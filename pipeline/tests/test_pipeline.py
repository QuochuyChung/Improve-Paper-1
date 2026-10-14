import hashlib
import json

import joblib
import pytest

import acquire
import process
import storage
import train


def run_pipeline(run_id, shift=0.0):
    args = ["--run-id", run_id, "--shift", str(shift)]
    acquire.main(args)
    process.main(args)
    train.main(args)


def load(path):
    return json.loads(path.read_text())


def test_artifacts_follow_shared_convention(root):
    run_pipeline("baseline-001")

    model_dir = root / "models" / "baseline-001"
    for name in ("model.joblib", "metrics.json", "manifest.json"):
        assert (model_dir / name).is_file()
    assert (root / "models" / "LATEST").read_text().strip() == "baseline-001"

    manifest = load(model_dir / "manifest.json")
    assert manifest["feature_names"] == acquire.FEATURE_NAMES
    assert manifest["run_id"] == "baseline-001"

    metrics = load(model_dir / "metrics.json")
    assert metrics["accuracy"] > 0.8
    assert 0.0 <= metrics["f1"] <= 1.0


def test_reference_stats_format(root):
    run_pipeline("baseline-001")
    stats = load(root / "features" / "baseline-001" / "reference_stats.json")
    assert list(stats) == acquire.FEATURE_NAMES
    for entry in stats.values():
        assert set(entry) == {"mean", "std"}
        assert entry["std"] > 0


def test_model_hash_matches_file(root):
    run_pipeline("baseline-001")
    model_dir = root / "models" / "baseline-001"
    manifest = load(model_dir / "manifest.json")
    actual = hashlib.sha256((model_dir / "model.joblib").read_bytes()).hexdigest()
    assert manifest["model_sha256"] == actual


def test_model_is_loadable_and_predicts(root):
    run_pipeline("baseline-001")
    model = joblib.load(root / "models" / "baseline-001" / "model.joblib")
    row = [[m for m in acquire.BASE_MEANS]]
    assert model.predict(row).shape == (1,)


def test_shift_moves_reference_mean_by_shift_std(root):
    run_pipeline("baseline-001", shift=0.0)
    run_pipeline("issue-1", shift=1.5)
    base = load(root / "features" / "baseline-001" / "reference_stats.json")
    shifted = load(root / "features" / "issue-1" / "reference_stats.json")
    for name, std in zip(acquire.FEATURE_NAMES, acquire.BASE_STDS):
        moved = (shifted[name]["mean"] - base[name]["mean"]) / std
        assert moved == pytest.approx(1.5, abs=0.25), name


def test_retrain_keeps_old_run_and_updates_latest(root):
    run_pipeline("baseline-001")
    run_pipeline("issue-7", shift=1.5)
    assert (root / "models" / "baseline-001" / "model.joblib").is_file()
    assert (root / "models" / "issue-7" / "model.joblib").is_file()
    assert (root / "models" / "LATEST").read_text().strip() == "issue-7"


def test_same_seed_is_reproducible(root):
    run_pipeline("a")
    run_pipeline("b")
    sha_a = load(root / "raw" / "a" / "manifest.json")["sha256"]
    sha_b = load(root / "raw" / "b" / "manifest.json")["sha256"]
    assert sha_a == sha_b


@pytest.mark.parametrize("bad", ["../escape", "a/b", "", ".hidden", "x" * 80, "a b"])
def test_bad_run_id_rejected(root, bad):
    with pytest.raises(ValueError):
        storage.validate_run_id(bad)


def test_acquire_rejects_traversal_run_id(root):
    with pytest.raises(ValueError):
        acquire.main(["--run-id", "../escape"])
    assert not (root.parent / "escape").exists()


def test_acquire_rejects_non_finite_shift(root):
    with pytest.raises(SystemExit):
        acquire.main(["--run-id", "x", "--shift", "nan"])


def test_latest_not_updated_when_train_fails(root):
    run_pipeline("baseline-001")
    acquire.main(["--run-id", "broken"])
    # bỏ qua bước process nên train phải lỗi và không được đổi LATEST
    with pytest.raises(FileNotFoundError):
        train.main(["--run-id", "broken"])
    assert (root / "models" / "LATEST").read_text().strip() == "baseline-001"
