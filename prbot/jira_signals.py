from __future__ import annotations
from typing import Any, Dict, List, Tuple

KEYWORDS: List[Tuple[str, int]] = [
    ("blocking", 12),
    ("regression", 12),
    ("rollback", 12),
    ("revert", 12),
    ("hotfix", 12),
    ("production", 8),
    ("prod", 6),
    ("incident", 12),
    ("sev", 10),
    ("outage", 12),
    ("reopened", 10),
    ("customer impact", 12),
]

def _collect_text(issue: Dict[str, Any]) -> str:
    fields = issue.get("fields", {})
    parts: List[str] = []
    parts.append(fields.get("summary") or "")
    parts.append(fields.get("description") or "")

    comment_obj = fields.get("comment") or {}
    comments = comment_obj.get("comments") or []
    for c in comments[-20:]:
        parts.append(c.get("body") or "")

    return "\n".join(parts).lower()

def extract_signals(issue: Dict[str, Any]) -> Dict[str, Any]:
    fields = issue.get("fields", {})
    issuetype = (fields.get("issuetype") or {}).get("name") or ""
    priority = (fields.get("priority") or {}).get("name") or ""
    status = (fields.get("status") or {}).get("name") or ""
    updated = fields.get("updated") or ""
    score = 0
    reasons: List[str] = []

    # Type risk
    if issuetype in {"Defect", "Incident", "Problem", "Hotfix"}:
        score += 30
        reasons.append(f"Issue type is {issuetype} (+30).")
    
    # Priority risk (best-effort)
    p = priority.lower()
    if "p0" in p or "highest" in p:
        score += 15
        reasons.append(f"High priority {priority} (+15).")
    elif "p1" in p or "high" in p:
        score += 10
        reasons.append(f"Priority {priority} (+10).")

    # Keyword risk
    blob = _collect_text(issue)
    print(blob)
    for kw, pts in KEYWORDS:
        if kw in blob:
            score += pts
            reasons.append(f"Keyword '{kw}' found (+{pts}).")

    score = min(score, 100)

    return {
        "issuetype": issuetype,
        "priority": priority,
        "status": status,
        "updated": updated,
        "risk_score": score,
        "reasons": reasons[:10],
    }
