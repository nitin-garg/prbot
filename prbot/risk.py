from dataclasses import dataclass
from typing import List, Tuple, Dict

RISKY_PATH_RULES: List[Tuple[str, str, int]] = [
    ("auth", "Touches auth/security-related code", 30),
    ("security", "Touches auth/security-related code", 30),
    ("payments", "Touches payments/billing-related code", 30),
    ("billing", "Touches payments/billing-related code", 30),
    ("migration", "Touches database migration-related code", 30),
    ("db", "Touches database-related code (schema/migration risk)", 25),
    ("api", "Touches API surface (possible contract change)", 20),
    ("config", "Touches configuration (blast radius risk)", 15),
]

COMMENT_KEYWORDS: List[Tuple[str, str, int]] = [
    ("feature flag", "PR discussion mentioned feature flag", 15),
    ("feature toggle", "PR discussion mentioned feature toggle", 15),
    ("toggle", "PR discussion mentioned toggle/flag", 10),
    ("rollback", "PR discussion mentioned rollback plan", 10),
    ("regression", "PR discussion mentioned regression risk", 10),
    ("incident", "PR discussion mentioned incident/prod risk", 10),
    ("prod", "PR discussion mentioned production risk", 5),
]

@dataclass
class RiskResult:
    score: int
    level: str
    toggle: str
    evidence: List[str]
    stats: Dict[str, int]

def compute_risk(
    changed_files,
    additions,
    deletions,
    text_blobs,
    jira_bonus=0,
    hist_score=0,
    *,
    config: dict,
):
    thr = config.get("threshold", {})
    yes_threshold = int(thr.get("foryes", 50))
    no_threshold  = int(thr.get("forno",  40))
   
    
    jira_cap = config["weights"]["jira_bonus_cap"]
    history_cap = config["weights"]["history_bonus_cap"]

    risky_paths = config["paths"]["risky"]
    safe_paths = config["paths"]["safe"]

    jira_bonus = min(jira_bonus, jira_cap)
    hist_score = min(hist_score, history_cap)

    evidence: List[str] = []
    score = 0

    total_lines = additions + deletions
    if len(changed_files) > 25:
        score += 10
        evidence.append(f"Large PR: {len(changed_files)} files changed (+10).")

    if total_lines > 800:
        score += 10
        evidence.append(f"Large diff: {total_lines} lines changed (+10).")
    elif total_lines > 300:
        score += 5
        evidence.append(f"Moderate diff: {total_lines} lines changed (+5).")

    lower_paths = " ".join(changed_files).lower()
    for token, reason, pts in RISKY_PATH_RULES:
        if token in lower_paths:
            score += pts
            evidence.append(f"{reason} (+{pts}).")

    joined_text = "\n".join(text_blobs).lower()
    for token, reason, pts in COMMENT_KEYWORDS:
        if token in joined_text:
            score += pts
            evidence.append(f"{reason} (+{pts}).")
    score = score + jira_bonus
    score = score + hist_score
    score = min(score, 100)
    if score >= yes_threshold:
        level, toggle = "HIGH","YES"
    elif score <= no_threshold:
        level, toggle = "LOW","NO"
    else:
        level, toggle = "MEDIUM","UNCLEAR"


    stats = {
        "files_changed": len(changed_files),
        "additions": additions,
        "deletions": deletions,
        "total_lines": total_lines,
    }
    return RiskResult(score=score, level=level, toggle=toggle, evidence=evidence, stats=stats)
