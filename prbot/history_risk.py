from __future__ import annotations
import time
from typing import Any, Dict, List, Tuple
from prbot.store import get_file_history, get_prefix_history, get_cached_jira
from collections import Counter

def top_prefix(file_path: str, depth: int = 2) -> str:
    parts = file_path.split("/")
    if len(parts) <= depth:
        return file_path
    return "/".join(parts[:depth])

def compute_history_risk(repo: str, changed_files: List[str], days: int = 180) -> Dict[str, Any]:
    now = int(time.time())
    since = now - days * 24 * 3600

    total_touches = 0
    hotfix_like = 0
    jira_keys = []

    for fp in changed_files:
        rows = get_file_history(repo, fp, since, limit=50)
        if not rows:
            prefix = top_prefix(fp, depth=2)
            rows = get_prefix_history(repo, prefix, since, limit=50)

        total_touches += len(rows)
        for r in rows:
            if any(m in {"revert", "rollback", "hotfix", "incident", "sev"} for m in r["markers"]):
                hotfix_like += 1
            jira_keys.extend(r["jira_keys"])

    jira_keys = list(dict.fromkeys(jira_keys))  # unique preserve order
    jira_risks = []
    for k in jira_keys[:50]:
        cached = get_cached_jira(k, max_age_seconds=30*24*3600)  # allow older cache for history
        if cached:
            jira_risks.append(cached["signals"].get("risk_score", 0))

    max_hist_jira_risk = max(jira_risks) if jira_risks else 0

    # Score (cap history influence)
    score = 0
    evidence = []

    if total_touches >= 20:
        score += 15
        evidence.append(f"High churn in area: {total_touches} historical touches in last {days}d (+15).")
    elif total_touches >= 8:
        score += 8
        evidence.append(f"Moderate churn in area: {total_touches} historical touches in last {days}d (+8).")

    if hotfix_like >= 3:
        score += 25
        evidence.append(f"Multiple hotfix/revert-like PRs in history: {hotfix_like} (+25).")
    elif hotfix_like >= 1:
        score += 12
        evidence.append(f"Hotfix/revert signal in history: {hotfix_like} (+12).")

    if max_hist_jira_risk >= 70:
        score += 15
        evidence.append(f"Historical Jira issues show high risk (max {max_hist_jira_risk}/100) (+15).")
    elif max_hist_jira_risk >= 40:
        score += 8
        evidence.append(f"Historical Jira issues show moderate risk (max {max_hist_jira_risk}/100) (+8).")

    if score > 40:
        score = 40  # cap history impact

    return {
        "score": score,
        "evidence": evidence,
        "total_touches": total_touches,
        "hotfix_like": hotfix_like,
        "max_hist_jira_risk": max_hist_jira_risk,
        "historical_jira_keys": jira_keys[:20],
    }
