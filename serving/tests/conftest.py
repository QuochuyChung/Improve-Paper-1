import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SERVING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVING_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fake_pipeline  # noqa: E402


@pytest.fixture
def artifact_root(tmp_path, monkeypatch):
    monkeypatch.setenv("ARTIFACT_ROOT", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(artifact_root):
    from app import create_app

    fake_pipeline.run(artifact_root, "baseline-001", shift=0.0, seed=1)
    with TestClient(create_app(artifact_root, window_size=50)) as c:
        yield c
