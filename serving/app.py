"""SkeltyMLOps PoC: component API Development.

FastAPI phục vụ model do pipeline Argo sinh ra, theo quy ước artifact chung:

    <ARTIFACT_ROOT>/models/LATEST                 run-id mới nhất
    <ARTIFACT_ROOT>/models/<run-id>/model.joblib
    <ARTIFACT_ROOT>/models/<run-id>/metrics.json
    <ARTIFACT_ROOT>/models/<run-id>/manifest.json (có feature_names)

Biến môi trường:
    ARTIFACT_ROOT  thư mục gốc artifact (mặc định /data)
    STATS_WINDOW   số request gần nhất dùng cho /stats (mặc định 200)
"""

from __future__ import annotations

import json
import math
import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ModelNotAvailable(RuntimeError):
    pass


class PredictRequest(BaseModel):
    features: dict[str, float]


@dataclass
class LoadedModel:
    run_id: str
    model: Any
    metrics: dict
    manifest: dict
    feature_names: list[str]
    loaded_at: str


def load_model(artifact_root: Path) -> LoadedModel:
    """Đọc models/LATEST và nạp model tương ứng."""
    latest = artifact_root / "models" / "LATEST"
    if not latest.is_file():
        raise ModelNotAvailable(f"không thấy {latest}")
    run_id = latest.read_text().strip()
    if not RUN_ID_RE.match(run_id):
        raise ModelNotAvailable(f"run-id không hợp lệ trong LATEST: {run_id!r}")
    run_dir = artifact_root / "models" / run_id
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text())
        metrics = json.loads((run_dir / "metrics.json").read_text())
        model = joblib.load(run_dir / "model.joblib")
    except (OSError, ValueError) as exc:
        raise ModelNotAvailable(f"không nạp được artifact của {run_id}: {exc}") from exc
    feature_names = manifest.get("feature_names")
    if not feature_names or not isinstance(feature_names, list):
        raise ModelNotAvailable(f"manifest của {run_id} thiếu feature_names")
    return LoadedModel(
        run_id=run_id,
        model=model,
        metrics=metrics,
        manifest=manifest,
        feature_names=[str(f) for f in feature_names],
        loaded_at=datetime.now(timezone.utc).isoformat(),
    )


@dataclass
class ServingState:
    artifact_root: Path
    window_size: int
    current: LoadedModel | None = None
    window: deque = field(default_factory=deque)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        self.window = deque(maxlen=self.window_size)


def _window_stats(rows: list[list[float]], names: list[str]) -> dict:
    n = len(rows)
    features: dict[str, dict[str, float]] = {}
    if n:
        arr = np.asarray(rows, dtype=float)
        means = arr.mean(axis=0)
        stds = arr.std(axis=0, ddof=1) if n > 1 else np.zeros(len(names))
        for i, name in enumerate(names):
            features[name] = {"mean": float(means[i]), "std": float(stds[i])}
    return {"n": n, "features": features}


def create_app(artifact_root: str | Path | None = None, window_size: int | None = None) -> FastAPI:
    root = Path(artifact_root or os.environ.get("ARTIFACT_ROOT", "/data"))
    size = window_size or int(os.environ.get("STATS_WINDOW", "200"))
    if size < 1:
        raise ValueError("STATS_WINDOW phải >= 1")
    state = ServingState(artifact_root=root, window_size=size)

    registry = CollectorRegistry()
    predictions_total = Counter(
        "predictions_total", "Số dự đoán đã trả về", ["model_version"], registry=registry
    )
    latency = Histogram(
        "prediction_latency_seconds", "Độ trễ xử lý /predict", registry=registry
    )
    version_info = Gauge(
        "model_version_info", "Model đang phục vụ (giá trị 1)", ["model_version"], registry=registry
    )

    def install(new: LoadedModel) -> str | None:
        """Thay model đang dùng. Gọi khi đang giữ lock."""
        previous = state.current.run_id if state.current else None
        if previous != new.run_id or state.current.feature_names != new.feature_names:
            # /stats mô tả lưu lượng mà model hiện tại nhận, nên đổi model thì xoá cửa sổ.
            state.window.clear()
        if previous is not None:
            version_info.remove(previous)
        version_info.labels(model_version=new.run_id).set(1)
        state.current = new
        return previous

    def ensure_model() -> LoadedModel:
        with state.lock:
            if state.current is None:
                install(load_model(state.artifact_root))
            return state.current

    app = FastAPI(title="skelty-serving", version="0.1")
    app.state.serving = state
    app.state.registry = registry

    try:
        ensure_model()
    except ModelNotAvailable:
        # Pod vẫn khởi động; /health báo chưa sẵn sàng cho tới khi pipeline tạo model.
        pass

    @app.get("/health")
    def health():
        try:
            current = ensure_model()
        except ModelNotAvailable as exc:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "model_loaded": False, "detail": str(exc)},
            )
        return {"status": "ok", "model_loaded": True, "model_version": current.run_id}

    @app.get("/model")
    def model_info():
        try:
            current = ensure_model()
        except ModelNotAvailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        return {
            "model_version": current.run_id,
            "run_id": current.run_id,
            "metrics": current.metrics,
            "feature_names": current.feature_names,
            "loaded_at": current.loaded_at,
        }

    @app.post("/predict")
    def predict(req: PredictRequest):
        start = time.perf_counter()
        try:
            current = ensure_model()
        except ModelNotAvailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))

        expected = current.feature_names
        missing = [f for f in expected if f not in req.features]
        unexpected = sorted(set(req.features) - set(expected))
        not_finite = [f for f, v in req.features.items() if not math.isfinite(v)]
        if missing or unexpected or not_finite:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "features không khớp với model",
                    "missing": missing,
                    "unexpected": unexpected,
                    "not_finite": not_finite,
                    "expected": expected,
                },
            )

        row = [float(req.features[f]) for f in expected]
        X: Any = np.asarray([row], dtype=float)
        if hasattr(current.model, "feature_names_in_"):
            import pandas as pd

            X = pd.DataFrame(X, columns=expected)
        pred = current.model.predict(X)[0]
        probabilities = None
        if hasattr(current.model, "predict_proba"):
            proba = current.model.predict_proba(X)[0]
            probabilities = {str(c): float(p) for c, p in zip(current.model.classes_, proba)}

        with state.lock:
            # Chỉ ghi vào cửa sổ nếu model chưa bị thay trong lúc dự đoán.
            if state.current is current:
                state.window.append(row)
        predictions_total.labels(model_version=current.run_id).inc()
        latency.observe(time.perf_counter() - start)
        return {
            "prediction": pred.item() if hasattr(pred, "item") else pred,
            "probabilities": probabilities,
            "model_version": current.run_id,
        }

    @app.post("/reload")
    def reload():
        try:
            new = load_model(state.artifact_root)
        except ModelNotAvailable as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        with state.lock:
            previous = install(new)
        return {
            "previous_version": previous,
            "model_version": new.run_id,
            "changed": previous != new.run_id,
        }

    @app.get("/stats")
    def stats():
        with state.lock:
            rows = list(state.window)
            current = state.current
        names = current.feature_names if current else []
        body = _window_stats(rows, names)
        body["model_version"] = current.run_id if current else None
        body["window_size"] = state.window_size
        return body

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
