"""Bước 1: nhận dữ liệu.

Sinh dữ liệu dạng bảng (6 feature, nhãn nhị phân). `--shift` dịch mọi feature đi
shift * std so với phân phối gốc để giả lập data drift; ranh giới nhãn dịch theo,
nên model huấn luyện lại trên dữ liệu đã dịch khác model baseline.
"""

from __future__ import annotations

import argparse
import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import storage

FEATURE_NAMES = [f"f{i}" for i in range(6)]
BASE_MEANS = np.array([5.0, -2.0, 10.0, 0.0, 3.0, 1.0])
BASE_STDS = np.array([1.0, 0.5, 2.0, 1.0, 1.5, 0.3])
WEIGHTS = np.array([1.0, -1.0, 0.5, 0.8, -0.5, 0.3])
LABEL = "label"


def make_data(n: int, shift: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    centre = BASE_MEANS + shift * BASE_STDS
    X = rng.normal(centre, BASE_STDS, size=(n, len(FEATURE_NAMES)))
    z = ((X - centre) / BASE_STDS) @ WEIGHTS
    y = (z + rng.normal(0, 0.5, n) > 0).astype(int)
    frame = pd.DataFrame(X, columns=FEATURE_NAMES)
    frame[LABEL] = y
    return frame


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--shift", type=float, default=0.0)
    parser.add_argument("--n-samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    if not math.isfinite(args.shift):
        parser.error("--shift phải là số hữu hạn")
    if args.n_samples < 50:
        parser.error("--n-samples phải >= 50")

    out = storage.run_dir("raw", args.run_id)
    data = make_data(args.n_samples, args.shift, args.seed)
    data_path = out / "data.csv"
    data.to_csv(data_path, index=False)

    storage.write_json(
        out / "manifest.json",
        {
            "run_id": args.run_id,
            "shift": args.shift,
            "n_samples": args.n_samples,
            "seed": args.seed,
            "feature_names": FEATURE_NAMES,
            "sha256": storage.sha256_file(data_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    print(f"[acquire] run-id={args.run_id} shift={args.shift} n={args.n_samples} -> {data_path}")


if __name__ == "__main__":
    main()
