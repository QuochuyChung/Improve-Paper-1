"""Pipeline thay thế, chỉ dùng cho test.

Repo chưa có pipeline/acquire.py, process.py, train.py của skelty-poc, nên test
dùng file này để sinh artifact đúng quy ước chung (models/<run-id>/...,
models/LATEST, features/<run-id>/reference_stats.json). Khi pipeline thật được
đẩy lên, có thể thay hàm run() bằng lời gọi 3 script đó.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

FEATURE_NAMES = ["f0", "f1", "f2", "f3", "f4", "f5"]
BASE_MEANS = np.array([5.0, -2.0, 10.0, 0.0, 3.0, 1.0])
BASE_STDS = np.array([1.0, 0.5, 2.0, 1.0, 1.5, 0.3])


def make_data(n: int, shift: float, seed: int) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = rng.normal(BASE_MEANS + shift * BASE_STDS, BASE_STDS, size=(n, len(FEATURE_NAMES)))
    z = ((X - BASE_MEANS) / BASE_STDS) @ np.array([1.0, -1.0, 0.5, 0.8, -0.5, 0.3])
    y = (z + rng.normal(0, 0.5, n) > shift * 1.1).astype(int)
    return pd.DataFrame(X, columns=FEATURE_NAMES), y


def run(root: Path, run_id: str, shift: float = 0.0, seed: int = 0) -> None:
    X, y = make_data(1000, shift, seed)
    feat_dir = root / "features" / run_id
    feat_dir.mkdir(parents=True, exist_ok=True)
    stats = {c: {"mean": float(X[c].mean()), "std": float(X[c].std())} for c in FEATURE_NAMES}
    (feat_dir / "reference_stats.json").write_text(json.dumps(stats))

    model = LogisticRegression(max_iter=500).fit(X[:800], y[:800])
    pred = model.predict(X[800:])
    model_dir = root / "models" / run_id
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "model.joblib")
    metrics = {"accuracy": accuracy_score(y[800:], pred), "f1": f1_score(y[800:], pred)}
    (model_dir / "metrics.json").write_text(json.dumps(metrics))
    sha = hashlib.sha256((model_dir / "model.joblib").read_bytes()).hexdigest()
    manifest = {"run_id": run_id, "shift": shift, "feature_names": FEATURE_NAMES, "model_sha256": sha}
    (model_dir / "manifest.json").write_text(json.dumps(manifest))
    (root / "models" / "LATEST").write_text(run_id + "\n")
