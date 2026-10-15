"""Phát hiện drift dữ liệu đầu vào và tự tạo GitHub Issue.

Mỗi lần chạy:
  1. GET {SERVING_URL}/model lấy run-id model đang dùng, GET /stats lấy thống kê dữ liệu đang đến.
  2. Đọc {ARTIFACT_ROOT}/features/<run-id>/reference_stats.json (mean, std lúc huấn luyện).
  3. Với mỗi feature: z = |mean hiện tại - mean tham chiếu| / std tham chiếu.
     Có drift khi ít nhất --min-features feature có z > --z-threshold và n >= --min-samples.
  4. Đẩy 3 metric lên Pushgateway nếu có PUSHGATEWAY_URL (lỗi đẩy metric chỉ cảnh báo).
  5. Nếu có drift và chưa có issue mở nào mang label `retrain` thì tạo issue `[drift] ...`.

Mã thoát: 0 mọi trường hợp bình thường (kể cả có drift và đã tạo issue), 1 khi lỗi mạng hoặc lỗi API.
Cờ --dry-run chỉ in kết quả, không tạo issue và không đẩy metric.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import requests

RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,62}$")
TITLE_PREFIX = "[drift]"
LABEL = "retrain"
GITHUB_API = "https://api.github.com"
PUSH_JOB = "skelty_drift_check"
TIMEOUT = 15
EXIT_OK, EXIT_ERROR = 0, 1


class CheckError(Exception):
    """Lỗi mạng, lỗi API hoặc dữ liệu không đúng định dạng."""


@dataclass
class FeatureResult:
    name: str
    mean_now: float
    mean_ref: float
    std_ref: float
    z: float


@dataclass
class Evaluation:
    n: int
    features: list[FeatureResult]
    skipped: list[str]
    drifted: list[str]
    max_z: float
    enough_samples: bool
    drift: bool


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def evaluate(
    stats: Mapping[str, Any],
    reference: Mapping[str, Mapping[str, Any]],
    z_threshold: float = 1.0,
    min_features: int = 3,
    min_samples: int = 100,
) -> Evaluation:
    n = int(_number(stats.get("n")) or 0)
    current = stats.get("features") or {}
    results: list[FeatureResult] = []
    skipped: list[str] = []
    for name, ref in reference.items():
        cur = current.get(name) or {}
        mean_now, mean_ref, std_ref = _number(cur.get("mean")), _number(ref.get("mean")), _number(ref.get("std"))
        if mean_now is None or mean_ref is None or std_ref is None or std_ref <= 0:
            skipped.append(name)
            continue
        results.append(FeatureResult(name, mean_now, mean_ref, std_ref, abs(mean_now - mean_ref) / std_ref))
    drifted = [r.name for r in results if r.z > z_threshold]
    enough = n >= min_samples
    return Evaluation(
        n=n,
        features=results,
        skipped=skipped,
        drifted=drifted,
        max_z=max((r.z for r in results), default=0.0),
        enough_samples=enough,
        drift=enough and len(drifted) >= min_features,
    )


def _get_json(session: Any, url: str) -> Any:
    try:
        response = session.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise CheckError(f"GET {url} lỗi: {exc}") from exc


def fetch_model_and_stats(session: Any, serving_url: str) -> tuple[str, dict[str, Any]]:
    base = serving_url.rstrip("/")
    model = _get_json(session, f"{base}/model")
    run_id = str(model.get("run_id") or model.get("model_version") or "")
    # run-id đến từ mạng và được dùng làm tên thư mục nên phải kiểm tra trước.
    if not RUN_ID_RE.fullmatch(run_id) or ".." in run_id:
        raise CheckError(f"/model trả run_id không hợp lệ: {run_id!r}")
    stats = _get_json(session, f"{base}/stats")
    if not isinstance(stats, dict):
        raise CheckError("/stats không trả về một JSON object")
    return run_id, stats


def load_reference(artifact_root: str | Path, run_id: str) -> dict[str, dict[str, Any]]:
    path = Path(artifact_root) / "features" / run_id / "reference_stats.json"
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CheckError(f"không đọc được {path}: {exc}") from exc
    if not isinstance(value, dict) or not all(isinstance(v, dict) for v in value.values()):
        raise CheckError(f"{path} không đúng định dạng {{feature: {{mean, std}}}}")
    return value


def metrics_text(ev: Evaluation) -> str:
    return (
        "# TYPE drift_detected gauge\n"
        f"drift_detected {int(ev.drift)}\n"
        "# TYPE drifted_feature_count gauge\n"
        f"drifted_feature_count {len(ev.drifted)}\n"
        "# TYPE max_feature_zscore gauge\n"
        f"max_feature_zscore {ev.max_z:.6f}\n"
    )


def push_metrics(session: Any, pushgateway_url: str, ev: Evaluation) -> None:
    url = f"{pushgateway_url.rstrip('/')}/metrics/job/{PUSH_JOB}"
    response = session.put(url, data=metrics_text(ev), timeout=TIMEOUT)
    response.raise_for_status()


class GitHub:
    def __init__(self, session: Any, repo: str, token: str) -> None:
        self.session, self.repo = session, repo
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _url(self) -> str:
        return f"{GITHUB_API}/repos/{self.repo}/issues"

    def open_retrain_issues(self) -> list[int]:
        try:
            response = self.session.get(
                self._url(),
                params={"state": "open", "labels": LABEL, "per_page": 100},
                headers=self.headers,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            items = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise CheckError(f"GitHub liệt kê issue lỗi: {exc}") from exc
        # API issues cũng trả pull request, bỏ qua chúng.
        return [int(i["number"]) for i in items if "pull_request" not in i]

    def create_issue(self, title: str, body: str) -> int:
        try:
            response = self.session.post(
                self._url(),
                json={"title": title, "body": body, "labels": [LABEL]},
                headers=self.headers,
                timeout=TIMEOUT,
            )
            response.raise_for_status()
            return int(response.json()["number"])
        except (requests.RequestException, ValueError, KeyError) as exc:
            raise CheckError(f"GitHub tạo issue lỗi: {exc}") from exc


def issue_text(run_id: str, ev: Evaluation, args: argparse.Namespace, detected_at: str) -> tuple[str, str]:
    title = f"{TITLE_PREFIX} {run_id}: {len(ev.drifted)} feature lệch so với tham chiếu"
    payload = {
        "type": "drift",
        "model_version": run_id,
        "drifted_features": ev.drifted,
        "detected_at": detected_at,
    }
    rows = "\n".join(
        f"| {r.name} | {r.mean_now:.4f} | {r.mean_ref:.4f} | {r.std_ref:.4f} | {r.z:.2f} | "
        f"{'có' if r.name in ev.drifted else 'không'} |"
        for r in ev.features
    )
    body = (
        "Drift dữ liệu đầu vào, phát hiện tự động bởi `skelty-drift-check`.\n\n"
        f"- Model đang dùng: `{run_id}`\n"
        f"- Số mẫu trong cửa sổ: {ev.n}\n"
        f"- Quy tắc: |mean hiện tại - mean tham chiếu| / std tham chiếu > {args.z_threshold} "
        f"trên ít nhất {args.min_features} feature, và n >= {args.min_samples}\n\n"
        "| Feature | mean hiện tại | mean tham chiếu | std tham chiếu | z | Drift |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        f"{rows}\n\n"
        "```json\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n"
        "```\n"
    )
    return title, body


def print_evaluation(run_id: str, ev: Evaluation, args: argparse.Namespace) -> None:
    print(f"model={run_id} n={ev.n} (cần n >= {args.min_samples}: {'đủ' if ev.enough_samples else 'CHƯA ĐỦ'})")
    for r in ev.features:
        flag = "  <-- lệch" if r.name in ev.drifted else ""
        print(
            f"  {r.name}: mean_now={r.mean_now:.4f} mean_ref={r.mean_ref:.4f} "
            f"std_ref={r.std_ref:.4f} z={r.z:.2f}{flag}"
        )
    if ev.skipped:
        print(f"  bỏ qua (thiếu số liệu hoặc std tham chiếu <= 0): {', '.join(ev.skipped)}")
    print(
        f"kết quả: {len(ev.drifted)} feature vượt z > {args.z_threshold}, max z = {ev.max_z:.2f}, "
        f"drift = {'CÓ' if ev.drift else 'không'}"
    )


def parse_args(argv: list[str] | None, env: Mapping[str, str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="chỉ in kết quả, không tạo issue, không đẩy metric")
    parser.add_argument("--z-threshold", type=float, default=float(env.get("DRIFT_Z_THRESHOLD", "1.0")))
    parser.add_argument("--min-features", type=int, default=int(env.get("DRIFT_MIN_FEATURES", "3")))
    parser.add_argument("--min-samples", type=int, default=int(env.get("DRIFT_MIN_SAMPLES", "100")))
    return parser.parse_args(argv)


def run(args: argparse.Namespace, env: Mapping[str, str], session: Any) -> int:
    serving_url = env.get("SERVING_URL", "http://skelty-serving:8000")
    artifact_root = env.get("ARTIFACT_ROOT", "/data")
    pushgateway = env.get("PUSHGATEWAY_URL", "")
    token, repo = env.get("GITHUB_TOKEN", ""), env.get("GITHUB_REPO", "")

    try:
        run_id, stats = fetch_model_and_stats(session, serving_url)
        reference = load_reference(artifact_root, run_id)
        ev = evaluate(stats, reference, args.z_threshold, args.min_features, args.min_samples)
        print_evaluation(run_id, ev, args)

        if pushgateway and not args.dry_run:
            try:
                push_metrics(session, pushgateway, ev)
                print("đã đẩy metric lên Pushgateway")
            except requests.RequestException as exc:
                print(f"cảnh báo: không đẩy được metric lên Pushgateway: {exc}", file=sys.stderr)

        if not ev.drift:
            return EXIT_OK

        if not (token and repo):
            if args.dry_run:
                print("dry-run: thiếu GITHUB_TOKEN/GITHUB_REPO nên không kiểm tra được issue đang mở")
                return EXIT_OK
            raise CheckError("có drift nhưng thiếu GITHUB_TOKEN hoặc GITHUB_REPO")

        github = GitHub(session, repo, token)
        open_issues = github.open_retrain_issues()
        if open_issues:
            print(f"đã có issue retrain đang mở ({', '.join(f'#{n}' for n in open_issues)}), không tạo thêm")
            return EXIT_OK

        detected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        title, body = issue_text(run_id, ev, args, detected_at)
        if args.dry_run:
            print(f"dry-run: sẽ tạo issue \"{title}\" với label {LABEL}")
            return EXIT_OK
        number = github.create_issue(title, body)
        print(f"đã tạo issue #{number}: {title}")
        return EXIT_OK
    except CheckError as exc:
        print(f"lỗi: {exc}", file=sys.stderr)
        return EXIT_ERROR


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv, os.environ)
    return run(args, os.environ, requests.Session())


if __name__ == "__main__":
    sys.exit(main())
