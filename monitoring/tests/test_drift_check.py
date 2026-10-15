import json

import pytest
import requests

import drift_check
from fakes import FEATURES, GITHUB, PUSHGATEWAY, FakeSession, make_stats

DRIFTED = {"f0": 1.6, "f1": 1.6, "f2": 1.6, "f3": 1.6, "f4": 1.6, "f5": 1.6}
NONE = {}


def check(env, session, *flags):
    args = drift_check.parse_args(list(flags), env)
    return drift_check.run(args, env, session)


def metric_value(session, name):
    text = session.puts[-1][1]
    return float(next(l.split()[1] for l in text.splitlines() if l.startswith(name + " ")))


def test_no_drift_creates_nothing(env, capsys):
    session = FakeSession(stats=make_stats(200, {f: 0.1 for f in FEATURES}))
    assert check(env, session) == 0
    assert session.posts == []
    assert GITHUB not in session.gets
    assert metric_value(session, "drift_detected") == 0
    assert metric_value(session, "drifted_feature_count") == 0
    assert "drift = không" in capsys.readouterr().out


def test_first_drift_creates_exactly_one_issue(env):
    session = FakeSession(stats=make_stats(200, DRIFTED))
    assert check(env, session) == 0
    assert len(session.posts) == 1
    issue = session.posts[0]
    assert issue["labels"] == ["retrain"]
    assert issue["title"].startswith("[drift]")
    assert metric_value(session, "drift_detected") == 1
    assert metric_value(session, "drifted_feature_count") == 6
    assert metric_value(session, "max_feature_zscore") == pytest.approx(1.6, abs=1e-4)


def test_issue_body_matches_orchestrator_contract(env):
    orchestrator = pytest.importorskip("orchestrator.loop", reason="cần thư viện kubernetes của orchestrator")
    session = FakeSession(stats=make_stats(200, DRIFTED))
    check(env, session)
    payload = orchestrator.parse_drift_payload(session.posts[0]["body"])
    assert payload["type"] == "drift"
    assert payload["model_version"] == "baseline-001"
    assert payload["drifted_features"] == FEATURES
    assert payload["detected_at"].endswith("Z")


def test_no_new_issue_when_retrain_issue_already_open(env, capsys):
    session = FakeSession(stats=make_stats(200, DRIFTED), open_issues=[{"number": 3}])
    assert check(env, session) == 0
    assert session.posts == []
    assert "#3" in capsys.readouterr().out
    # metric vẫn phản ánh drift dù không tạo issue mới
    assert metric_value(session, "drift_detected") == 1


def test_pull_requests_do_not_count_as_open_issue(env):
    session = FakeSession(stats=make_stats(200, DRIFTED), open_issues=[{"number": 9, "pull_request": {}}])
    assert check(env, session) == 0
    assert len(session.posts) == 1


def test_too_few_samples_is_not_drift(env):
    session = FakeSession(stats=make_stats(99, DRIFTED))
    assert check(env, session) == 0
    assert session.posts == []
    assert metric_value(session, "drift_detected") == 0


def test_exactly_min_samples_counts(env):
    session = FakeSession(stats=make_stats(100, DRIFTED))
    check(env, session)
    assert len(session.posts) == 1


def test_two_features_over_threshold_is_not_drift(env):
    session = FakeSession(stats=make_stats(200, {"f0": 1.6, "f1": 1.6}))
    assert check(env, session) == 0
    assert session.posts == []
    assert metric_value(session, "drifted_feature_count") == 2


def test_z_equal_threshold_is_not_over(env):
    session = FakeSession(stats=make_stats(200, {"f0": 1.0, "f1": 1.0, "f2": 1.0}))
    assert check(env, session) == 0
    assert session.posts == []


def test_serving_unreachable_exits_nonzero(env, capsys):
    session = FakeSession(stats=make_stats(200, DRIFTED))
    session.serving_error = requests.ConnectionError("mất kết nối")
    assert check(env, session) == 1
    assert session.posts == [] and session.puts == []
    assert "lỗi" in capsys.readouterr().err


def test_github_list_error_exits_nonzero(env):
    session = FakeSession(stats=make_stats(200, DRIFTED))
    session.list_status = 500
    assert check(env, session) == 1
    assert session.posts == []


def test_github_create_error_exits_nonzero(env):
    session = FakeSession(stats=make_stats(200, DRIFTED))
    session.create_status = 403
    assert check(env, session) == 1


def test_missing_reference_file_exits_nonzero(env):
    session = FakeSession(model={"run_id": "khong-ton-tai"}, stats=make_stats(200, DRIFTED))
    assert check(env, session) == 1


def test_run_id_path_traversal_is_rejected(env):
    session = FakeSession(model={"run_id": "../../etc"}, stats=make_stats(200, DRIFTED))
    assert check(env, session) == 1
    assert session.posts == []


def test_dry_run_creates_and_pushes_nothing(env, capsys):
    session = FakeSession(stats=make_stats(200, DRIFTED))
    assert check(env, session, "--dry-run") == 0
    assert session.posts == [] and session.puts == []
    assert "dry-run" in capsys.readouterr().out


def test_dry_run_without_github_credentials(env):
    for key in ("GITHUB_TOKEN", "GITHUB_REPO"):
        env.pop(key)
    session = FakeSession(stats=make_stats(200, DRIFTED))
    assert check(env, session, "--dry-run") == 0
    assert GITHUB not in session.gets


def test_missing_credentials_with_drift_exits_nonzero(env):
    env.pop("GITHUB_TOKEN")
    session = FakeSession(stats=make_stats(200, DRIFTED))
    assert check(env, session) == 1


def test_pushgateway_failure_does_not_fail_the_check(env):
    session = FakeSession(stats=make_stats(200, DRIFTED))
    session.push_status = 503
    assert check(env, session) == 0
    assert len(session.posts) == 1


def test_no_pushgateway_url_skips_push(env):
    env.pop("PUSHGATEWAY_URL")
    session = FakeSession(stats=make_stats(200, DRIFTED))
    assert check(env, session) == 0
    assert session.puts == []


def test_push_goes_to_expected_url(env):
    session = FakeSession(stats=make_stats(200, NONE))
    check(env, session)
    assert session.puts[-1][0] == f"{PUSHGATEWAY}/metrics/job/skelty_drift_check"


def test_empty_window_is_handled(env):
    session = FakeSession(stats={"n": 0, "features": {}})
    assert check(env, session) == 0
    assert session.posts == []
    assert metric_value(session, "max_feature_zscore") == 0


def test_feature_missing_from_stats_is_skipped_not_crash(env, capsys):
    stats = make_stats(200, DRIFTED)
    del stats["features"]["f5"]
    session = FakeSession(stats=stats)
    assert check(env, session) == 0
    assert "bỏ qua" in capsys.readouterr().out
    assert metric_value(session, "drifted_feature_count") == 5


def test_thresholds_are_parameters(env):
    session = FakeSession(stats=make_stats(200, {"f0": 0.6, "f1": 0.6}))
    check(env, session, "--z-threshold", "0.5", "--min-features", "2")
    assert len(session.posts) == 1


def test_thresholds_can_come_from_environment(env):
    env["DRIFT_MIN_SAMPLES"] = "300"
    session = FakeSession(stats=make_stats(200, DRIFTED))
    check(env, session)
    assert session.posts == []
