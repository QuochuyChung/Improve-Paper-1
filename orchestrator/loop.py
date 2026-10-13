"""Ticket parsing and the polling orchestration loop."""

from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests

from .github_client import Issue

LOG = logging.getLogger(__name__)
TERMINAL_PHASES = {"Succeeded", "Failed", "Error"}


def parse_drift_payload(body: str) -> dict[str, Any]:
    """Find a JSON object in free-form Markdown and validate the drift contract."""
    decoder = json.JSONDecoder()
    for position, char in enumerate(body):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(body[position:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("type") == "drift":
            missing = {
                "model_version",
                "drifted_features",
                "detected_at",
            } - value.keys()
            if missing:
                raise ValueError(f"drift JSON is missing fields: {sorted(missing)}")
            if not isinstance(value["drifted_features"], list):
                raise ValueError("drifted_features must be a list")
            if "shift" in value:
                try:
                    value["shift"] = float(value["shift"])
                except (TypeError, ValueError) as exc:
                    raise ValueError("shift must be a finite number") from exc
                if not math.isfinite(value["shift"]):
                    raise ValueError("shift must be a finite number")
            return value
    raise ValueError("issue body does not contain a valid drift JSON object")


@dataclass(frozen=True)
class Settings:
    artifact_root: Path = Path("/data")
    namespace: str = "argo"
    serving_url: str = "http://skelty-serving:8000"
    poll_seconds: float = 30
    workflow_poll_seconds: float = 5
    default_shift: float = 0
    workflow_timeout_seconds: float = 900
    image: str = "skelty-poc:0.1"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            artifact_root=Path(os.environ.get("ARTIFACT_ROOT", "/data")),
            namespace=os.environ.get("ARGO_NAMESPACE", "argo"),
            serving_url=os.environ.get(
                "SERVING_URL", "http://skelty-serving:8000"
            ).rstrip("/"),
            poll_seconds=float(os.environ.get("POLL_SECONDS", "30")),
            workflow_poll_seconds=float(
                os.environ.get("WORKFLOW_POLL_SECONDS", "5")
            ),
            default_shift=float(os.environ.get("DEFAULT_SHIFT", "0")),
            workflow_timeout_seconds=float(
                os.environ.get("WORKFLOW_TIMEOUT_SECONDS", "900")
            ),
            image=os.environ.get("PIPELINE_IMAGE", "skelty-poc:0.1"),
        )


class Orchestrator:
    def __init__(
        self,
        github: Any,
        argo: Any,
        settings: Settings,
        *,
        http: Any = requests,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.github = github
        self.argo = argo
        self.settings = settings
        self.http = http
        self.sleep = sleep
        self.monotonic = monotonic

    def run_once(self) -> int:
        processed = 0
        for issue in self.github.list_retrain_issues():
            self.process_issue(issue)
            processed += 1
        return processed

    def process_issue(self, issue: Issue) -> None:
        # A crash after adding `done` but before closing the issue is recoverable.
        if "done" in issue.labels:
            self.github.remove_label(issue.number, "in-progress")
            self.github.close(issue.number)
            return

        try:
            payload = parse_drift_payload(issue.body)
        except ValueError as exc:
            self.github.comment(issue.number, f"Orchestrator bỏ qua issue: {exc}")
            LOG.warning("Issue #%s has invalid payload: %s", issue.number, exc)
            return

        run_id = f"issue-{issue.number}"
        workflow_name = self.argo.workflow_name(issue.number)
        shift = payload.get("shift", self.settings.default_shift)
        if "in-progress" not in issue.labels:
            self.github.add_labels(issue.number, "in-progress")

        try:
            _, created = self.argo.ensure_workflow(
                issue.number, run_id, shift, self.settings.image
            )
            LOG.info(
                "%s workflow %s for issue #%s",
                "Created" if created else "Resumed",
                workflow_name,
                issue.number,
            )
            phase, message = self._wait_for_workflow(workflow_name)
            if phase != "Succeeded":
                detail = message or "no status message"
                self.github.comment(
                    issue.number,
                    f"Workflow `{workflow_name}` {phase}: {detail}",
                )
                self.github.remove_label(issue.number, "in-progress")
                return

            metrics = self._read_metrics(run_id)
            reload_body = self._reload_serving()
            model_version = reload_body.get("model_version") or reload_body.get("run_id")
            if model_version != run_id:
                raise RuntimeError(
                    f"serving reloaded unexpected model {model_version!r}; expected {run_id!r}"
                )
            self.github.comment(
                issue.number,
                "\n".join(
                    [
                        f"Workflow `{workflow_name}` Succeeded.",
                        f"- run-id: `{run_id}`",
                        f"- accuracy: `{metrics.get('accuracy', 'không có')}`",
                        f"- f1: `{metrics.get('f1', 'không có')}`",
                        f"- model_version sau reload: `{model_version}`",
                    ]
                ),
            )
            self.github.add_labels(issue.number, "done")
            self.github.remove_label(issue.number, "in-progress")
            self.github.close(issue.number)
        except Exception as exc:
            LOG.exception("Issue #%s failed", issue.number)
            try:
                self.github.comment(
                    issue.number,
                    f"Orchestrator lỗi khi xử lý `{workflow_name}`: {type(exc).__name__}: {exc}",
                )
                self.github.remove_label(issue.number, "in-progress")
            except Exception:
                LOG.exception("Could not report failure for issue #%s", issue.number)

    def _wait_for_workflow(self, name: str) -> tuple[str, str]:
        deadline = self.monotonic() + self.settings.workflow_timeout_seconds
        while True:
            phase, message = self.argo.phase(name)
            if phase in TERMINAL_PHASES:
                return phase, message
            if self.monotonic() >= deadline:
                return "Timeout", (
                    f"exceeded {self.settings.workflow_timeout_seconds:g}s; last phase={phase}"
                )
            self.sleep(self.settings.workflow_poll_seconds)

    def _read_metrics(self, run_id: str) -> dict[str, Any]:
        path = self.settings.artifact_root / "models" / run_id / "metrics.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot read metrics from {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise RuntimeError(f"metrics in {path} must be a JSON object")
        return value

    def _reload_serving(self) -> dict[str, Any]:
        response = self.http.post(
            self.settings.serving_url + "/reload",
            timeout=30,
        )
        response.raise_for_status()
        value = response.json()
        if not isinstance(value, dict):
            raise RuntimeError("serving /reload did not return a JSON object")
        return value


def run_forever(orchestrator: Orchestrator) -> None:
    while True:
        try:
            orchestrator.run_once()
        except Exception:
            LOG.exception("Polling iteration failed")
        orchestrator.sleep(orchestrator.settings.poll_seconds)
