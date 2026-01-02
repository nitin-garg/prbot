from __future__ import annotations
import os
import time
import requests
from typing import Any, Dict, Optional

class JiraClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
        

       
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

        # Auth option A: Bearer/PAT
        token = os.getenv("JIRA_TOKEN")
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

        # Auth option B: Basic
        user = os.getenv("JIRA_USER")
        api_token = os.getenv("JIRA_API_TOKEN")
        if user and api_token and not token:
            self.session.auth = (user, api_token)

        # Timeouts
        self.timeout = 20

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def get_myself(self) -> Dict[str, Any]:
        # Works on many Jira DC/Cloud instances
        r = self.session.get(self._url("/rest/api/2/myself"), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_issue(self, key: str, expand: str = "changelog") -> Dict[str, Any]:
        r = self.session.get(
            self._url(f"/rest/api/2/issue/{key}"),
            params={"expand": expand},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def search(self, jql: str, fields: Optional[list[str]] = None, max_results: int = 50) -> Dict[str, Any]:
        payload = {
            "jql": jql,
            "maxResults": max_results,
        }
        if fields:
            payload["fields"] = fields

        r = self.session.post(
            self._url("/rest/api/2/search"),
            json=payload,
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()
