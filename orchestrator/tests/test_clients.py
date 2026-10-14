from kubernetes.client.exceptions import ApiException

from orchestrator.argo_client import ArgoClient
from orchestrator.github_client import GitHubClient


class Response:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        return self.response


def test_github_fake_lists_only_open_retrain_drift_issues():
    raw = [
        {
            "number": 1,
            "title": "[drift] v1",
            "body": "{}",
            "state": "open",
            "labels": [{"name": "retrain"}, {"name": "in-progress"}],
        },
        {
            "number": 2,
            "title": "not drift",
            "body": "{}",
            "state": "open",
            "labels": [{"name": "retrain"}],
        },
        {
            "number": 3,
            "title": "[drift] pull request",
            "body": "{}",
            "state": "open",
            "labels": [{"name": "retrain"}],
            "pull_request": {},
        },
    ]
    session = Session(Response(raw))
    client = GitHubClient("secret", "owner/repo", session=session)
    issues = client.list_retrain_issues()
    assert [item.number for item in issues] == [1]
    method, url, kwargs = session.calls[0]
    assert method == "GET" and url.endswith("/repos/owner/repo/issues")
    assert kwargs["params"]["labels"] == "retrain"
    assert kwargs["headers"]["Authorization"] == "Bearer secret"


class KubernetesApi:
    def __init__(self):
        self.objects = {}
        self.created = []

    def get_namespaced_custom_object(self, group, version, namespace, plural, name):
        if name not in self.objects:
            raise ApiException(status=404)
        return self.objects[name]

    def create_namespaced_custom_object(self, group, version, namespace, plural, body):
        self.created.append((group, version, namespace, plural, body))
        self.objects[body["metadata"]["name"]] = body
        return body


def test_kubernetes_fake_creates_expected_workflow_and_reuses_it():
    api = KubernetesApi()
    argo = ArgoClient("argo", api=api)
    first, created = argo.ensure_workflow(9, "issue-9", 1.5, "skelty-poc:0.1")
    second, created_again = argo.ensure_workflow(9, "issue-9", 1.5, "skelty-poc:0.1")
    assert created and not created_again and first == second
    assert len(api.created) == 1
    body = api.created[0][-1]
    assert body["metadata"]["name"] == "retrain-issue-9"
    assert body["spec"]["workflowTemplateRef"]["name"] == "skelty-training-pipeline"
    assert body["spec"]["arguments"]["parameters"] == [
        {"name": "run-id", "value": "issue-9"},
        {"name": "shift", "value": "1.5"},
        {"name": "image", "value": "skelty-poc:0.1"},
    ]
