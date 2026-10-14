"""Bước 3: huấn luyện model scikit-learn và lưu artifact có version.

Ghi model.joblib, metrics.json, manifest.json (kèm SHA-256 của model và các tập
dữ liệu) vào models/<run-id>/, rồi mới cập nhật models/LATEST.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

import joblib
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

import storage
from acquire import LABEL


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--shift", type=float, default=0.0, help="chỉ ghi nhận, bước acquire mới dùng")
    args = parser.parse_args(argv)

    feat_dir = storage.run_dir("features", args.run_id, create=False)
    feat_manifest = storage.read_json(feat_dir / "manifest.json")
    feature_names = feat_manifest["feature_names"]
    train = pd.read_csv(feat_dir / "train.csv")
    test = pd.read_csv(feat_dir / "test.csv")

    model = LogisticRegression(max_iter=1000)
    model.fit(train[feature_names], train[LABEL])
    pred = model.predict(test[feature_names])
    metrics = {
        "accuracy": float(accuracy_score(test[LABEL], pred)),
        "f1": float(f1_score(test[LABEL], pred)),
        "n_train": len(train),
        "n_test": len(test),
    }

    out = storage.run_dir("models", args.run_id)
    model_path = out / "model.joblib"
    joblib.dump(model, model_path)
    storage.write_json(out / "metrics.json", metrics)
    storage.write_json(
        out / "manifest.json",
        {
            "run_id": args.run_id,
            "shift": args.shift,
            "feature_names": feature_names,
            "model_sha256": storage.sha256_file(model_path),
            "raw_sha256": feat_manifest["raw_sha256"],
            "train_sha256": feat_manifest["train_sha256"],
            "test_sha256": feat_manifest["test_sha256"],
            "sklearn_version": sklearn.__version__,
            "code_version": os.environ.get("CODE_VERSION", "unknown"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    storage.set_latest(args.run_id)
    print(
        f"[train] run-id={args.run_id} accuracy={metrics['accuracy']:.4f} "
        f"f1={metrics['f1']:.4f} -> {out}"
    )


if __name__ == "__main__":
    main()
