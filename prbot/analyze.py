from __future__ import annotations
import time
from typing import Dict, Any, List, Optional

from prbot.github_client import fetch_pr_context
from prbot.extractors import extract_jira_keys
from prbot.risk import compute_risk
from prbot.jira_client import JiraClient
from prbot.jira_signals import extract_signals
from prbot.store import init_db, get_cached_jira, upsert_cached_jira
from prbot.history_risk import compute_history_risk
from prbot.config import load_config

config = load_config()

def analyze_pr(
    token: str,
    pr_url: str,
    *,
    with_ai: bool = False,
) -> Dict[str, Any]:
    """
    Analyze a PR and return all analysis artifacts.
    No printing, no DB writes, no side effects except Jira cache.
    """

    # 1. Fetch PR context
    ctx = fetch_pr_context(token, pr_url)

    # 2. Extract Jira keys
    jira_keys = extract_jira_keys(
        [ctx["title"], ctx["body"]]
        + ctx["issue_comments"]
        + ctx["review_comments"]
        + ctx["commit_messages"]
    )

    # 3. Jira enrichment
    init_db()
    jira_details: List[tuple[str, dict]] = []

    try:
        jc = JiraClient()
    except Exception:
        jc = None

    if jc and jira_keys:
        for key in jira_keys[:15]:
            if not key.startswith("PS-"):
                continue

            cached = get_cached_jira(key)
            if cached:
                signals = cached["signals"]
            else:
                issue = jc.get_issue(key)
                signals = extract_signals(issue)
                upsert_cached_jira(key, issue, signals)

            jira_details.append((key, signals))

    jira_risk_max = max((sig["risk_score"] for _, sig in jira_details), default=0)
    jira_bonus = min(20, int(jira_risk_max * 0.2))

    # 4. History enrichment
    hist = compute_history_risk(ctx["repo_full"], ctx["files"], days=180)

    # 5. Core risk computation
    result = compute_risk(
        changed_files=ctx["files"],
        additions=ctx["additions"],
        deletions=ctx["deletions"],
        text_blobs=[ctx["title"], ctx["body"]]
        + ctx["issue_comments"]
        + ctx["review_comments"],
        jira_bonus=jira_bonus,
        hist_score=hist["score"],
        config=config
    )

    # Attach evidence
    if hist["score"] > 0:
        result.evidence.extend(hist["evidence"])
    if jira_bonus:
        result.evidence.append(
            f"Jira signals raise risk (max Jira issue risk {jira_risk_max}/100) (+{jira_bonus})."
        )

    # 6. Optional AI reasoning
    ai = None
    if with_ai:
        try:
            from prbot.ai_explainer import ai_explain

            ai_payload = {
                "repo": ctx["repo_full"],
                "pr_number": ctx["pr_number"],
                "title": ctx["title"],
                "stats": {
                    "files_changed": len(ctx["files"]),
                    "additions": ctx["additions"],
                    "deletions": ctx["deletions"],
                },
                "rule_engine": {
                    "risk_score": result.score,
                    "risk_level": result.level,
                    "toggle_recommendation": result.toggle,
                    "evidence": result.evidence[:12],
                },
                "policy": {
                    "recommend_toggle_when": [
                        "high churn + regressions",
                        "touches risky modules (auth/payments/migrations)",
                        "large blast radius changes",
                    ],
                    "allowed_decisions": ["YES", "NO", "UNCLEAR"],
                },
                "jira": [
                    {"key": k, **sig} for (k, sig) in jira_details[:10]
                ],
                "history": hist,
            }

            ai = ai_explain(ai_payload)
        except Exception as e:
            ai = {"error": str(e)}

    # 7. Return full analysis bundle
    return {
        "ctx": ctx,
        "result": result,
        "jira_keys":jira_keys,
        "jira_details": jira_details,
        "jira_bonus": jira_bonus,
        "history": hist,
        "ai": ai,
        "analyzed_at": int(time.time()),
    }
