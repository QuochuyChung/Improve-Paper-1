"""Entrypoint for the in-cluster SkeltyMLOps orchestrator."""

from __future__ import annotations

import logging
import os

from .argo_client import ArgoClient
from .github_client import GitHubClient
from .loop import Orchestrator, Settings, run_forever


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = Settings.from_env()
    github = GitHubClient(
        token=os.environ.get("GITHUB_TOKEN", ""),
        repo=os.environ.get("GITHUB_REPO", ""),
    )
    argo = ArgoClient(settings.namespace)
    run_forever(Orchestrator(github, argo, settings))


if __name__ == "__main__":
    main()
