"""Minimal GitHub Issues client used by the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    labels: frozenset[str]
    state: str = "open"


class GitHubClient:
    def __init__(
        self,
        token: str,
        repo: str,
        *,
        session: requests.Session | None = None,
        api_url: str = "https://api.github.com",
        timeout: float = 30,
    ) -> None:
        if not token:
            raise ValueError("GITHUB_TOKEN is required")
        if "/" not in repo:
            raise ValueError("GITHUB_REPO must have the form owner/repo")
        self.base = f"{api_url.rstrip('/')}/repos/{repo}"
        self.session = session or requests.Session()
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        response = self.session.request(
            method,
            self.base + path,
            headers=self.headers,
            timeout=self.timeout,
            **kwargs,
        )
        response.raise_for_status()
        return response

    @staticmethod
    def _issue(raw: dict[str, Any]) -> Issue:
        return Issue(
            number=int(raw["number"]),
            title=str(raw.get("title") or ""),
            body=str(raw.get("body") or ""),
            labels=frozenset(label["name"] for label in raw.get("labels", [])),
            state=str(raw.get("state") or "open"),
        )

    def list_retrain_issues(self) -> list[Issue]:
        """Return open drift issues, including claimed/done ones for crash recovery."""
        response = self._request(
            "GET",
            "/issues",
            params={"state": "open", "labels": "retrain", "per_page": 100},
        )
        return [
            self._issue(raw)
            for raw in response.json()
            if "pull_request" not in raw
            and str(raw.get("title") or "").startswith("[drift]")
        ]

    def add_labels(self, issue_number: int, *labels: str) -> None:
        self._request(
            "POST", f"/issues/{issue_number}/labels", json={"labels": list(labels)}
        )

    def remove_label(self, issue_number: int, label: str) -> None:
        response = self.session.request(
            "DELETE",
            self.base + f"/issues/{issue_number}/labels/{label}",
            headers=self.headers,
            timeout=self.timeout,
        )
        # Removing a missing label is already the desired idempotent state.
        if response.status_code != 404:
            response.raise_for_status()

    def comment(self, issue_number: int, body: str) -> None:
        self._request("POST", f"/issues/{issue_number}/comments", json={"body": body})

    def close(self, issue_number: int) -> None:
        self._request("PATCH", f"/issues/{issue_number}", json={"state": "closed"})
