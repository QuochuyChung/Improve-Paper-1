import fake_pipeline
import numpy as np
from app import create_app
from fastapi.testclient import TestClient

FEATURES = {"f0": 5.0, "f1": -2.0, "f2": 10.0, "f3": 0.0, "f4": 3.0, "f5": 1.0}


def test_health_and_model(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["model_version"] == "baseline-001"
    body = client.get("/model").json()
    assert body["run_id"] == "baseline-001"
    assert body["feature_names"] == fake_pipeline.FEATURE_NAMES
    assert set(body["metrics"]) == {"accuracy", "f1"}


def test_predict_ok(client):
    r = client.post("/predict", json={"features": FEATURES})
    assert r.status_code == 200
    body = r.json()
    assert body["prediction"] in (0, 1)
    assert set(body["probabilities"]) == {"0", "1"}
    assert abs(sum(body["probabilities"].values()) - 1) < 1e-9
    assert body["model_version"] == "baseline-001"


def test_predict_missing_and_extra_feature_is_422(client):
    bad = dict(FEATURES)
    del bad["f3"]
    bad["oops"] = 1.0
    r = client.post("/predict", json={"features": bad})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["missing"] == ["f3"]
    assert detail["unexpected"] == ["oops"]


def test_predict_non_numeric_is_422(client):
    r = client.post("/predict", json={"features": {**FEATURES, "f0": "abc"}})
    assert r.status_code == 422
    r = client.post("/predict", json={"wrong": {}})
    assert r.status_code == 422


def test_stats_sliding_window(client):
    assert client.get("/stats").json()["n"] == 0
    rng = np.random.default_rng(0)
    sent = []
    for _ in range(80):
        row = {k: float(v) for k, v in zip(FEATURES, rng.normal(0, 1, 6))}
        sent.append([row[k] for k in fake_pipeline.FEATURE_NAMES])
        assert client.post("/predict", json={"features": row}).status_code == 200
    body = client.get("/stats").json()
    assert body["n"] == 50  # window_size của fixture
    last = np.array(sent[-50:])
    for i, name in enumerate(fake_pipeline.FEATURE_NAMES):
        assert abs(body["features"][name]["mean"] - last[:, i].mean()) < 1e-9
        assert abs(body["features"][name]["std"] - last[:, i].std(ddof=1)) < 1e-9


def test_rejected_requests_do_not_enter_stats(client):
    client.post("/predict", json={"features": {"f0": 1.0}})
    assert client.get("/stats").json()["n"] == 0


def test_reload_switches_model_without_restart(client, artifact_root):
    client.post("/predict", json={"features": FEATURES})
    fake_pipeline.run(artifact_root, "issue-7", shift=1.5, seed=2)
    r = client.post("/reload")
    assert r.status_code == 200
    assert r.json() == {"previous_version": "baseline-001", "model_version": "issue-7", "changed": True}
    assert client.get("/model").json()["run_id"] == "issue-7"
    assert client.post("/predict", json={"features": FEATURES}).json()["model_version"] == "issue-7"
    # Cửa sổ thống kê được làm mới khi đổi model.
    assert client.get("/stats").json()["n"] == 1


def test_reload_with_broken_latest_keeps_old_model(client, artifact_root):
    (artifact_root / "models" / "LATEST").write_text("does-not-exist\n")
    assert client.post("/reload").status_code == 503
    assert client.get("/model").json()["run_id"] == "baseline-001"


def test_metrics(client, artifact_root):
    for _ in range(3):
        client.post("/predict", json={"features": FEATURES})
    text = client.get("/metrics").text
    assert 'predictions_total{model_version="baseline-001"} 3.0' in text
    assert "prediction_latency_seconds_count 3.0" in text
    assert 'model_version_info{model_version="baseline-001"} 1.0' in text
    fake_pipeline.run(artifact_root, "issue-8", shift=0.0, seed=3)
    client.post("/reload")
    text = client.get("/metrics").text
    assert 'model_version_info{model_version="issue-8"} 1.0' in text
    assert 'model_version_info{model_version="baseline-001"}' not in text


def test_starts_without_model_then_becomes_ready(artifact_root):
    with TestClient(create_app(artifact_root)) as c:
        assert c.get("/health").status_code == 503
        assert c.post("/predict", json={"features": FEATURES}).status_code == 503
        fake_pipeline.run(artifact_root, "baseline-001")
        assert c.get("/health").status_code == 200
        assert c.get("/model").json()["run_id"] == "baseline-001"
