import json
from collections import deque
from pathlib import Path

import pytest

from orchestrator.github_client import Issue
from orchestrator.loop import Orchestrator, Settings, parse_drift_payload


def body(**extra):
    payload = {
        "type": "drift",
        "model_version": "baseline-001",
        "drifted_features": ["f0", "f1", "f2"],
        "detected_at": "2026-10-14T00:00:00Z",
        **extra,
    }
    return "Drift detected\n```json\n" + json.dumps(payload) + "\n```"


class FakeGitHub:
    def __init__(self, issues=()):
        self.issues = list(issues)
        self.comments = []
        self.added = []
        self.removed = []
        self.closed = []

    def list_retrain_issues(self):
        return list(self.issues)

    def add_labels(self, number, *labels):
        self.added.append((number, *labels))

    def remove_label(self, number, label):
        self.removed.append((number, label))

    def comment(self, number, text):
        self.comments.append((number, text))

    def close(self, number):
        self.closed.append(number)


class FakeArgo:
    def __init__(self, phases=()):
        self.phases = deque(phases or [("Running", "")])
        self.workflows = {}
        self.create_count = 0

    @staticmethod
    def workflow_name(number):
        return f"retrain-issue-{number}"

    def ensure_workflow(self, number, run_id, shift, image):
        name = self.workflow_name(number)
        created = name not in self.workflows
        if created:
            self.create_count += 1
            self.workflows[name] = {"run_id": run_id, "shift": shift, "image": image}
        return self.workflows[name], created

    def phase(self, name):
        if len(self.phases) > 1:
            return self.phases.popleft()
        return self.phases[0]


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeHTTP:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def post(self, url, timeout):
        self.calls.append((url, timeout))
        return FakeResponse(self.payload)


class Clock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


def make(tmp_path: Path, github, argo, http=None, timeout=3):
    clock = Clock()
    settings = Settings(
        artifact_root=tmp_path,
        workflow_timeout_seconds=timeout,
        workflow_poll_seconds=1,
        default_shift=1.5,
    )
    return Orchestrator(
        github,
        argo,
        settings,
        http=http or FakeHTTP({"model_version": "issue-7"}),
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )


def issue(labels=frozenset({"retrain"}), text=None):
    return Issue(7, "[drift] baseline-001", text or body(), labels)


def write_metrics(root: Path):
    path = root / "models" / "issue-7"
    path.mkdir(parents=True)
    (path / "metrics.json").write_text('{"accuracy": 0.91, "f1": 0.90}', encoding="utf-8")


def test_no_issue(tmp_path):
    github, argo = FakeGitHub(), FakeArgo()
    assert make(tmp_path, github, argo).run_once() == 0
    assert argo.create_count == 0


def test_new_issue_creates_exactly_one_workflow_on_rerun(tmp_path):
    github, argo = FakeGitHub([issue()]), FakeArgo([("Failed", "training error")])
    runner = make(tmp_path, github, argo)
    runner.run_once()
    runner.run_once()
    assert argo.create_count == 1
    assert argo.workflows["retrain-issue-7"] == {
        "run_id": "issue-7",
        "shift": 1.5,
        "image": "skelty-poc:0.1",
    }


def test_success_reloads_comments_labels_and_closes(tmp_path):
    write_metrics(tmp_path)
    github = FakeGitHub([issue()])
    argo = FakeArgo([("Running", ""), ("Succeeded", "")])
    http = FakeHTTP({"model_version": "issue-7"})
    make(tmp_path, github, argo, http).run_once()
    assert http.calls == [("http://skelty-serving:8000/reload", 30)]
    assert github.closed == [7]
    assert (7, "done") in github.added
    assert (7, "in-progress") in github.removed
    assert "accuracy: `0.91`" in github.comments[-1][1]


@pytest.mark.parametrize("phase", ["Failed", "Error"])
def test_failed_workflow_comments_unlocks_and_keeps_issue_open(tmp_path, phase):
    github = FakeGitHub([issue()])
    make(tmp_path, github, FakeArgo([(phase, "pod failed")])).run_once()
    assert github.closed == []
    assert (7, "in-progress") in github.removed
    assert phase in github.comments[-1][1]


def test_timeout_comments_unlocks_and_keeps_issue_open(tmp_path):
    github = FakeGitHub([issue()])
    make(tmp_path, github, FakeArgo([("Running", "")]), timeout=2).run_once()
    assert github.closed == []
    assert "Timeout" in github.comments[-1][1]
    assert (7, "in-progress") in github.removed


def test_invalid_json_is_commented_and_does_not_create_workflow(tmp_path):
    github, argo = FakeGitHub([issue(text="not JSON")]), FakeArgo()
    make(tmp_path, github, argo).run_once()
    assert argo.create_count == 0
    assert "bỏ qua" in github.comments[-1][1]


def test_restart_resumes_in_progress_workflow_without_duplicate(tmp_path):
    write_metrics(tmp_path)
    argo = FakeArgo([("Succeeded", "")])
    argo.workflows["retrain-issue-7"] = {
        "run_id": "issue-7",
        "shift": 1.5,
        "image": "skelty-poc:0.1",
    }
    github = FakeGitHub([issue(frozenset({"retrain", "in-progress"}))])
    make(tmp_path, github, argo).run_once()
    assert argo.create_count == 0
    assert github.closed == [7]
    assert (7, "in-progress") not in github.added


def test_restart_after_done_label_only_closes_issue(tmp_path):
    github = FakeGitHub([issue(frozenset({"retrain", "in-progress", "done"}))])
    argo = FakeArgo()
    make(tmp_path, github, argo).run_once()
    assert github.closed == [7]
    assert (7, "in-progress") in github.removed
    assert argo.create_count == 0


def test_payload_shift_and_validation():
    assert parse_drift_payload(body(shift="1.25"))["shift"] == 1.25
    with pytest.raises(ValueError):
        parse_drift_payload('{"type":"drift"}')

