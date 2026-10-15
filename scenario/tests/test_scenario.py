"""Test kịch bản bằng dịch vụ GIẢ: serving là app FastAPI thật (TestClient),
còn Argo, CronJob drift, orchestrator và GitHub đều là mô phỏng trong FakeEnv.
Đây không phải kiểm chứng trên cluster."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "serving"), str(ROOT / "serving" / "tests"), str(ROOT / "scenario")]

import fake_pipeline  # noqa: E402
import run_scenario as rs  # noqa: E402
from app import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class FakeEnv:
    def __init__(self, root, orchestrator_works=True, workflow_ok=True):
        self.root = root
        self.client = TestClient(create_app(root, window_size=200))
        self.orchestrator_works, self.workflow_ok = orchestrator_works, workflow_ok
        self._issues: list[dict] = []

    def serving(self, method, path, body=None):
        r = self.client.request(method, path, json=body)
        r.raise_for_status()
        return r.json()

    def run_workflow(self, run_id, shift, timeout):
        if not self.workflow_ok:
            return "Failed: giả lập"
        fake_pipeline.run(self.root, run_id, shift=shift, seed=hash(run_id) % 1000)
        return "Succeeded"

    def reference_stats(self, run_id):
        import json
        return json.loads((self.root / "features" / run_id / "reference_stats.json").read_text())

    def issues(self):
        # mô phỏng CronJob drift + orchestrator mỗi lần được hỏi
        stats = self.serving("GET", "/stats")
        run_id = self.serving("GET", "/model")["run_id"]
        rep = rs.drift_report(stats, self.reference_stats(run_id))
        open_issue = [i for i in self._issues if i["state"] == "open"]
        if rep["drift"] and not open_issue and not self._issues:
            self._issues.append({"number": 42, "title": "[drift] model " + run_id, "state": "open",
                                 "labels": ["retrain"], "created_at": "x"})
        elif open_issue and self.orchestrator_works:
            i = open_issue[0]
            fake_pipeline.run(self.root, f"issue-{i['number']}", shift=1.5, seed=7)
            self.serving("POST", "/reload")
            i.update(state="closed", labels=["retrain", "done"])
        return [dict(i) for i in self._issues]

    def sleep(self, s):
        pass


def run(tmp_path, steps=None, **kw):
    env = FakeEnv(tmp_path, **kw)
    sc = rs.Scenario(env, n=200, shift=1.5, wait=5, poll=0)
    # sleep=0 nên giới hạn số vòng chờ bằng wait thực: dùng wait nhỏ
    return sc.run(steps or [1, 2, 3, 4, 5])


def test_full_scenario_passes(tmp_path):
    results = run(tmp_path)
    assert [r.ok for r in results] == [True] * 5, [(r.step, r.actual) for r in results]
    assert "issue-42" in results[3].actual


def test_orchestrator_down_fails_step4_and_is_reported(tmp_path):
    results = run(tmp_path, orchestrator_works=False)
    assert [r.ok for r in results] == [True, True, True, False, False]
    assert "chưa đóng" in results[3].actual


def test_workflow_failure_fails_step1(tmp_path):
    results = run(tmp_path, steps=[1], workflow_ok=False)
    assert not results[0].ok and "Failed" in results[0].actual


def test_dry_run_prints_plan_and_touches_nothing(tmp_path, capsys):
    assert rs.main(["--dry-run", "--log-dir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "Bước 5" in out and not list(tmp_path.iterdir())


def test_main_writes_log_with_summary_table(tmp_path, monkeypatch):
    monkeypatch.setenv("WAIT_SECONDS", "2")
    env = FakeEnv(tmp_path / "art", orchestrator_works=False)
    (tmp_path / "art").mkdir()
    code = rs.main(["--log-dir", str(tmp_path / "logs")], env=env)
    assert code == 1
    log = next((tmp_path / "logs").glob("*.md")).read_text(encoding="utf-8")
    assert "| Bước | Kỳ vọng | Thực tế | Kết quả |" in log
    assert "| 4 |" in log and "không đạt" in log


def test_drift_rule_boundaries():
    ref = {f"f{i}": {"mean": 0.0, "std": 1.0} for i in range(4)}
    mk = lambda n, m: {"n": n, "features": {f: {"mean": m[i], "std": 1} for i, f in enumerate(ref)}}
    assert rs.drift_report(mk(100, [1.1, 1.1, 1.1, 0]), ref)["drift"]
    assert not rs.drift_report(mk(99, [1.1, 1.1, 1.1, 0]), ref)["drift"]
    assert not rs.drift_report(mk(200, [1.1, 1.1, 1.0, 0]), ref)["drift"]  # đúng 1,0 chưa vượt
