"""Đọc/ghi artifact theo quy ước chung dưới ARTIFACT_ROOT (mặc định /data).

Bố cục:
  raw/<run-id>/            dữ liệu thô
  features/<run-id>/       tập train/test và reference_stats.json
  models/<run-id>/         model.joblib, metrics.json, manifest.json
  models/LATEST            run-id mới nhất
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")


def root() -> Path:
    return Path(os.environ.get("ARTIFACT_ROOT", "/data"))


def validate_run_id(run_id: str) -> str:
    """Chặn run-id có thể thoát khỏi thư mục artifact (ví dụ '../x')."""
    if not RUN_ID_RE.fullmatch(run_id) or ".." in run_id:
        raise ValueError(f"run-id không hợp lệ: {run_id!r}")
    return run_id


def run_dir(kind: str, run_id: str, create: bool = True) -> Path:
    """kind là một trong raw, features, models."""
    directory = root() / kind / validate_run_id(run_id)
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    return directory


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_json(path: Path, obj: Any) -> None:
    _atomic_write(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def set_latest(run_id: str) -> None:
    """Chỉ gọi sau khi model, metrics và manifest đã ghi xong."""
    models = root() / "models"
    models.mkdir(parents=True, exist_ok=True)
    _atomic_write(models / "LATEST", validate_run_id(run_id) + "\n")
