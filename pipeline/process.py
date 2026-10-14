"""Bước 2: xử lý feature.

Chia train/test, ghi hai tập vào features/<run-id>/ cùng reference_stats.json
(mean và std từng feature của tập train). Bước phát hiện drift so với file này.
"""

from __future__ import annotations

import argparse

import pandas as pd
from sklearn.model_selection import train_test_split

import storage
from acquire import LABEL


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--shift", type=float, default=0.0, help="chỉ ghi nhận, bước acquire mới dùng")
    args = parser.parse_args(argv)

    raw_dir = storage.run_dir("raw", args.run_id, create=False)
    raw_manifest = storage.read_json(raw_dir / "manifest.json")
    data = pd.read_csv(raw_dir / "data.csv")
    feature_names = [c for c in data.columns if c != LABEL]

    train, test = train_test_split(
        data, test_size=0.2, random_state=raw_manifest["seed"], stratify=data[LABEL]
    )

    out = storage.run_dir("features", args.run_id)
    train_path, test_path = out / "train.csv", out / "test.csv"
    train.to_csv(train_path, index=False)
    test.to_csv(test_path, index=False)

    stats = {}
    for name in feature_names:
        std = float(train[name].std())
        if not std > 0:
            raise SystemExit(f"feature {name} có std = 0, không dùng được làm tham chiếu")
        stats[name] = {"mean": float(train[name].mean()), "std": std}
    storage.write_json(out / "reference_stats.json", stats)

    storage.write_json(
        out / "manifest.json",
        {
            "run_id": args.run_id,
            "feature_names": feature_names,
            "raw_sha256": raw_manifest["sha256"],
            "train_sha256": storage.sha256_file(train_path),
            "test_sha256": storage.sha256_file(test_path),
            "n_train": len(train),
            "n_test": len(test),
        },
    )
    print(f"[process] run-id={args.run_id} train={len(train)} test={len(test)} -> {out}")


if __name__ == "__main__":
    main()
