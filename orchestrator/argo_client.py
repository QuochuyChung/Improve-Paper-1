"""Small adapter around the Kubernetes Custom Objects API for Argo Workflows."""

from __future__ import annotations

from typing import Any

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

GROUP = "argoproj.io"
VERSION = "v1alpha1"
PLURAL = "workflows"


class ArgoClient:
    def __init__(self, namespace: str = "argo", api: Any | None = None) -> None:
        self.namespace = namespace
        if api is None:
            config.load_incluster_config()
            api = client.CustomObjectsApi()
        self.api = api

    @staticmethod
    def workflow_name(issue_number: int) -> str:
        return f"retrain-issue-{issue_number}"

    def get_workflow(self, name: str) -> dict[str, Any] | None:
        try:
            return self.api.get_namespaced_custom_object(
                GROUP, VERSION, self.namespace, PLURAL, name
            )
        except ApiException as exc:
            if exc.status == 404:
                return None
            raise

    def ensure_workflow(
        self, issue_number: int, run_id: str, shift: float, image: str
    ) -> tuple[dict[str, Any], bool]:
        """Get or create the deterministic workflow; 409 is treated as success."""
        name = self.workflow_name(issue_number)
        existing = self.get_workflow(name)
        if existing is not None:
            return existing, False

        body = {
            "apiVersion": f"{GROUP}/{VERSION}",
            "kind": "Workflow",
            "metadata": {
                "name": name,
                "namespace": self.namespace,
                "labels": {
                    "app.kubernetes.io/name": "skelty-orchestrator",
                    "skelty.io/issue": str(issue_number),
                },
            },
            "spec": {
                "workflowTemplateRef": {"name": "skelty-training-pipeline"},
                "arguments": {
                    "parameters": [
                        {"name": "run-id", "value": run_id},
                        {"name": "shift", "value": str(shift)},
                        {"name": "image", "value": image},
                    ]
                },
            },
        }
        try:
            created = self.api.create_namespaced_custom_object(
                GROUP, VERSION, self.namespace, PLURAL, body
            )
            return created, True
        except ApiException as exc:
            if exc.status != 409:
                raise
            existing = self.get_workflow(name)
            if existing is None:
                raise RuntimeError(f"Workflow {name} returned 409 but cannot be read") from exc
            return existing, False

    def phase(self, name: str) -> tuple[str, str]:
        workflow = self.get_workflow(name)
        if workflow is None:
            return "Missing", "workflow not found"
        status = workflow.get("status") or {}
        return str(status.get("phase") or "Pending"), str(status.get("message") or "")
