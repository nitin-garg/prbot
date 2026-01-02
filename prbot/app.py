from dotenv import load_dotenv
import os
from github import Github
from prbot.jira_client import JiraClient
import requests
load_dotenv()


from prbot.store import init_db
import pip_system_certs
print("pip-system-certs loaded from:", pip_system_certs.__file__)

init_db()

r = requests.get("https://api.openai.com/v1/models", timeout=10)
print("status:", r.status_code)
print("body:", r.text[:120])

print("DB ready")

base = os.getenv("JIRA_BASE_URL").rstrip("/")
token = os.getenv("JIRA_TOKEN")
key = "PS-659931"  # <-- replace

r = requests.get(
    base + f"/rest/api/2/issue/{key}",
    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    timeout=20
)
print("status:", r.status_code)
print("body:", r.text[:300])


def make_github(token: str) -> Github:
    base_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
    return Github(login_or_token=token, base_url=base_url)




jc = JiraClient()
me = jc.get_myself()
print("Jira user:", me.get("displayName") or me.get("name") or me.get("emailAddress"))

print(os.environ["GITHUB_TOKEN"])
g = make_github(os.environ["GITHUB_TOKEN"])
user = g.get_user()
print(user.login)

import socket
print(socket.gethostbyname("api.github.com"))

try:
    r = g.get_repo("UKGEPIC/timekeeping-service-timecard")
    print("Repo OK:", r.full_name, "private=", r.private)
except Exception as e:
    print("Repo ERROR:", type(e), e)
