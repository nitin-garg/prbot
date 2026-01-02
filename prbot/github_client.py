import re
from typing import Dict, Any, List, Optional
from github import Github
import os
import datetime as dt

BOT_MARKER = "<!-- prbot-toggle-risk -->"

PR_URL_RE = re.compile(r"https://github\.com/(?P<org>[^/]+)/(?P<repo>[^/]+)/pull/(?P<num>\d+)")

def parse_pr_url(pr_url: str):
    m = PR_URL_RE.match(pr_url.strip())
    if not m:
        raise ValueError("PR URL must look like https://github.com/ORG/REPO/pull/123")
    org = m.group("org")
    repo = m.group("repo")
    num = int(m.group("num"))
    return f"{org}/{repo}", num

def fetch_pr_context(token: str, pr_url: str) -> Dict[str, Any]:
    repo_full, pr_number = parse_pr_url(pr_url)
    gh = make_github(token)

    try:
        repo = gh.get_repo(repo_full)
        pr = repo.get_pull(pr_number)
    except Exception as e:
        print("ERROR:", type(e), e)
    print("DEBUG repo_full:", repo_full, "pr_number:", pr_number)

    merged = bool(pr.merged)
    merged_at = pr.merged_at  # datetime or None
    merged_at_epoch = int(merged_at.timestamp()) if merged_at else 0

    files = [f.filename for f in pr.get_files()]
    issue_comments = [c.body or "" for c in pr.get_issue_comments()]
    review_comments = [c.body or "" for c in pr.get_review_comments()]
    commit_messages = [c.commit.message for c in pr.get_commits()]
    return {
        "repo_full": repo_full,
        "pr_number": pr_number,
        "merged": pr.merged,
        "merged_at_epoch":merged_at_epoch,
        "url": pr.html_url,
        "title": pr.title or "",
        "body": pr.body or "",
        "files": files,
        "additions": pr.additions or 0,
        "deletions": pr.deletions or 0,
        "issue_comments": issue_comments,
        "review_comments": review_comments,
        "commit_messages": commit_messages,
    }

def _format_comment(ctx: Dict[str, Any], result, jira_keys: List[str]) -> str:
    evidence_md = "\n".join([f"- {e}" for e in (result.evidence or ["No strong risk signals detected."])])
    jira_md = ", ".join([f"`{k}`" for k in jira_keys]) if jira_keys else "_None detected_"
    total = ctx["additions"] + ctx["deletions"]

    return f"""{BOT_MARKER}
## PR Risk + Toggle Advisor (local v0)

**Risk score:** **{result.score}/100** (**{result.level}**)  
**Feature toggle needed:** **{result.toggle}**

**Stats:** {len(ctx["files"])} files, +{ctx["additions"]} / -{ctx["deletions"]} (total {total})

**Jira keys found:** {jira_md}

### Evidence
{evidence_md}
"""
def make_github(token: str) -> Github:
    base_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
    return Github(login_or_token=token, base_url=base_url)

def upsert_bot_comment(token: str, ctx: Dict[str, Any], result, jira_keys: List[str]) -> None:
    gh = make_github(token)
    repo = gh.get_repo(ctx["repo_full"])
    pr = repo.get_pull(ctx["pr_number"])

    body = _format_comment(ctx, result, jira_keys)

    existing = None
    for c in pr.get_issue_comments():
        if c.body and BOT_MARKER in c.body:
            existing = c
            break

    if existing:
        existing.edit(body)
    else:
        pr.create_issue_comment(body)

def list_merged_prs(token: str, repo_full: str, limit: int = 20):
    gh = Github(token)
    repo = gh.get_repo(repo_full)

    prs = []
    # "state='closed'" includes merged and just-closed; filter merged=True
    for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        print(pr.title)
        if pr.merged:
            prs.append(pr)
        if len(prs) >= limit:
            break
    return prs
