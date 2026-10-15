import json
import sys
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).resolve().parent
MONITORING_DIR = TESTS_DIR.parent
sys.path.insert(0, str(MONITORING_DIR))
sys.path.insert(1, str(TESTS_DIR))
# gốc repo, để test hợp đồng với orchestrator/ import được (bỏ qua nếu thiếu thư viện kubernetes)
sys.path.insert(2, str(MONITORING_DIR.parent))

from fakes import PUSHGATEWAY, REF, SERVING  # noqa: E402


@pytest.fixture
def env(tmp_path):
    ref_dir = tmp_path / "features" / "baseline-001"
    ref_dir.mkdir(parents=True)
    (ref_dir / "reference_stats.json").write_text(json.dumps(REF))
    return {
        "SERVING_URL": SERVING,
        "ARTIFACT_ROOT": str(tmp_path),
        "PUSHGATEWAY_URL": PUSHGATEWAY,
        "GITHUB_TOKEN": "token-gia",
        "GITHUB_REPO": "owner/repo",
    }
