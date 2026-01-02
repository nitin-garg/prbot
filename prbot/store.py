from __future__ import annotations
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple

DB_PATH = os.getenv("PRBOT_DB_PATH", "prbot.sqlite3")

@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    try:
        yield c
        c.commit()
    finally:
        c.close()

def init_db():
    with conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS pr_outcomes (
            repo TEXT NOT NULL,
            pr_number INTEGER NOT NULL,
            pr_url TEXT NOT NULL,

            analyzed_at INTEGER,

            risk_score INTEGER,
            risk_level TEXT,
            toggle_recommendation TEXT,   -- YES/NO/UNCLEAR

            ai_decision TEXT,
            ai_confidence REAL,
            ai_summary TEXT,

            toggle_added INTEGER,         -- 1/0/NULL
            regression INTEGER,           -- 1/0/NULL
            regression_jira TEXT,
            notes TEXT,

            PRIMARY KEY (repo, pr_number)
            );
            """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS jira_cache (
            jira_key TEXT PRIMARY KEY,
            fetched_at INTEGER NOT NULL,
            payload_json TEXT NOT NULL,
            signals_json TEXT NOT NULL
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS file_changes (
            repo TEXT NOT NULL,
            file_path TEXT NOT NULL,
            pr_number INTEGER NOT NULL,
            merged_at INTEGER NOT NULL,
            jira_keys_json TEXT NOT NULL,
            markers_json TEXT NOT NULL,
            pr_url TEXT NOT NULL,
            PRIMARY KEY (repo, file_path, pr_number)
        )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_fc_repo_path_time ON file_changes(repo, file_path, merged_at)")

        c.execute("""
        CREATE TABLE IF NOT EXISTS pr_index_state (
            repo TEXT PRIMARY KEY,
            last_pr_number INTEGER NOT NULL
        )
        """)

def get_cached_jira(jira_key: str, max_age_seconds: int = 6 * 3600) -> Optional[Dict[str, Any]]:
    now = int(time.time())
    with conn() as c:
        row = c.execute(
            "SELECT fetched_at, payload_json, signals_json FROM jira_cache WHERE jira_key=?",
            (jira_key,),
        ).fetchone()
    if not row:
        return None
    fetched_at, payload_json, signals_json = row
    if now - fetched_at > max_age_seconds:
        return None
    return {"payload": json.loads(payload_json), "signals": json.loads(signals_json)}

def upsert_cached_jira(jira_key: str, payload: Dict[str, Any], signals: Dict[str, Any]) -> None:
    now = int(time.time())
    with conn() as c:
        c.execute(
            """
            INSERT INTO jira_cache(jira_key, fetched_at, payload_json, signals_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(jira_key) DO UPDATE SET
                fetched_at=excluded.fetched_at,
                payload_json=excluded.payload_json,
                signals_json=excluded.signals_json
            """,
            (jira_key, now, json.dumps(payload), json.dumps(signals)),
        )

def upsert_file_change(repo: str, file_path: str, pr_number: int, merged_at: int,
                       jira_keys: List[str], markers: List[str], pr_url: str) -> None:
    with conn() as c:
        c.execute(
            """
            INSERT INTO file_changes(repo, file_path, pr_number, merged_at, jira_keys_json, markers_json, pr_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo, file_path, pr_number) DO UPDATE SET
                merged_at=excluded.merged_at,
                jira_keys_json=excluded.jira_keys_json,
                markers_json=excluded.markers_json,
                pr_url=excluded.pr_url
            """,
            (repo, file_path, pr_number, merged_at, json.dumps(jira_keys), json.dumps(markers), pr_url),
        )

def get_file_history(repo: str, file_path: str, since_epoch: int, limit: int = 50) -> List[Dict[str, Any]]:
    with conn() as c:
        rows = c.execute(
            """
            SELECT file_path, pr_number, merged_at, jira_keys_json, markers_json, pr_url
            FROM file_changes
            WHERE repo=? AND file_path=? AND merged_at>=?
            ORDER BY merged_at DESC
            LIMIT ?
            """,
            (repo, file_path, since_epoch, limit),
        ).fetchall()

    out = []
    for fp, prn, ma, jk, mk, url in rows:
        out.append({
            "file_path": fp,
            "pr_number": prn,
            "merged_at": ma,
            "jira_keys": json.loads(jk),
            "markers": json.loads(mk),
            "pr_url": url,
        })
    return out

def get_prefix_history(repo: str, prefix: str, since_epoch: int, limit: int = 50) -> List[Dict[str, Any]]:
    # prefix like "src/payments/"
    like = prefix.rstrip("/") + "/%"
    with conn() as c:
        rows = c.execute(
            """
            SELECT file_path, pr_number, merged_at, jira_keys_json, markers_json, pr_url
            FROM file_changes
            WHERE repo=? AND file_path LIKE ? AND merged_at>=?
            ORDER BY merged_at DESC
            LIMIT ?
            """,
            (repo, like, since_epoch, limit),
        ).fetchall()

    out = []
    for fp, prn, ma, jk, mk, url in rows:
        out.append({
            "file_path": fp,
            "pr_number": prn,
            "merged_at": ma,
            "jira_keys": json.loads(jk),
            "markers": json.loads(mk),
            "pr_url": url,
        })
    return out

def list_outcomes(repo: str | None = None):
    with conn() as c:
        if repo:
            return c.execute("SELECT * FROM pr_outcomes WHERE repo=?", (repo,)).fetchall()
        return c.execute("SELECT * FROM pr_outcomes").fetchall()


def list_labeled_outcomes(repo: str | None = None):
    with conn() as c:
        if repo:
            rows = c.execute(
                """
                SELECT * FROM pr_outcomes
                WHERE repo = ? AND regression IS NOT NULL AND risk_score IS NOT NULL
                """,
                (repo,),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT * FROM pr_outcomes
                WHERE regression IS NOT NULL AND risk_score IS NOT NULL
                """
            ).fetchall()

    # if you use sqlite3.Row row_factory, these behave like dicts already.
    return [dict(r) for r in rows]


def upsert_pr_outcome(row: Dict[str, Any]) -> None:
    cols = ",".join(row.keys())
    qs = ",".join(["?"] * len(row))
    updates = ",".join([f"{k}=excluded.{k}" for k in row.keys() if k not in ("repo","pr_number")])
    
    with conn() as c:
        c.execute(
            f"""
            INSERT INTO pr_outcomes ({cols})
            VALUES ({qs})
            ON CONFLICT(repo, pr_number) DO UPDATE SET {updates}
            """,
            tuple(row.values()),
        )

def get_pr_outcome(repo: str, pr_number: int):
    with conn() as c:
        return c.execute(
            "SELECT * FROM pr_outcomes WHERE repo=? AND pr_number=?",
            (repo, pr_number),
        ).fetchone()