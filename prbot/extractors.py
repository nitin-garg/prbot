import re
from typing import List

JIRA_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")

def extract_jira_keys(texts: List[str]) -> List[str]:
    keys = set()
    for t in texts:
        if not t:
            continue
        for m in JIRA_KEY_RE.findall(t):
            keys.add(m)
    return sorted(keys)
