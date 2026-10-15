#!/usr/bin/env python3
"""Kịch bản kiểm chứng end-to-end cho PoC SkeltyMLOps (5 bước).

Chạy từ máy có kubectl, truy cập được API (SERVING_URL, ví dụ qua
`kubectl -n argo port-forward svc/skelty-serving 8000:8000`) và GitHub.

Biến môi trường:
  SERVING_URL     mặc định http://localhost:8000
  GITHUB_TOKEN    token đọc Issues (bước 3, 4)
  GITHUB_REPO     owner/repo
  ARGO_NAMESPACE  mặc định argo
  PIPELINE_IMAGE  mặc định skelty-poc:0.1
  SHIFT           độ dịch dữ liệu, mặc định 1.5
  N_REQUESTS      số request mỗi lượt, mặc định 200
  WAIT_SECONDS    timeout chờ drift / orchestrator, mặc định 900

Kết quả: scenario/logs/<timestamp>.md. Bước không đạt được ghi "không đạt",
không sửa số liệu và không bỏ qua bước.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests

DRIFT_Z = 1.0
DRIFT_MIN_FEATURES = 3
DRIFT_MIN_N = 100
BASELINE_RUN_ID = "baseline-001"

PLAN = [
    (1, "Chạy workflow baseline (shift=0, run-id baseline-001), chờ xong, gọi /reload",
     "workflow Succeeded; /model.run_id = baseline-001"),
    (2, "Gửi >= N request /predict bằng dữ liệu gốc, kiểm tra /stats",
     "n >= 100 và chưa drift theo quy tắc (>= 3 feature vượt 1,0 std)"),
    (3, "Gửi >= N request bằng dữ liệu dịch SHIFT std, chờ drift và issue",
     "/stats cho thấy drift; xuất hiện issue [drift] label retrain"),
    (4, "Chờ orchestrator retrain, đóng issue, /model chuyển sang issue-<số>",
     "issue đóng với label done; /model.run_id = issue-<số issue>"),
    (5, "Gửi lại dữ liệu dịch, kiểm tra với model mới",
     "n >= 100 và không còn drift theo tham chiếu của model mới"),
]


def drift_report(stats: dict, ref: dict) -> dict:
    """Quy tắc chung: |mean_now - mean_ref| / std_ref > 1,0 trên >= 3 feature, n >= 100."""
    zs = {}
    for name, r in ref.items():
        cur = stats.get("features", {}).get(name)
        if cur is None or not r.get("std"):
            continue
        zs[name] = abs(cur["mean"] - r["mean"]) / r["std"]
    drifted = sorted(n for n, z in zs.items() if z > DRIFT_Z)
    n = stats.get("n", 0)
    return {
        "n": n,
        "z": zs,
        "drifted": drifted,
        "drift": n >= DRIFT_MIN_N and len(drifted) >= DRIFT_MIN_FEATURES,
    }


def sample(ref: dict, feature_names: list[str], n: int, shift: float, rng) -> list[dict]:
    """Dữ liệu từ phân phối tham chiếu, dịch mọi feature `shift` std."""
    mean = np.array([ref[f]["mean"] for f in feature_names])
    std = np.array([ref[f]["std"] for f in feature_names])
    X = rng.normal(mean + shift * std, std, size=(n, len(feature_names)))
    return [dict(zip(feature_names, map(float, row))) for row in X]


class Env:
    """Giao diện tới thế giới bên ngoài; bản thật dưới đây, bản giả nằm trong test."""

    def __init__(self):
        self.base = os.environ.get("SERVING_URL", "http://localhost:8000").rstrip("/")
        self.ns = os.environ.get("ARGO_NAMESPACE", "argo")
        self.image = os.environ.get("PIPELINE_IMAGE", "skelty-poc:0.1")
        self.repo = os.environ.get("GITHUB_REPO", "")
        self.token = os.environ.get("GITHUB_TOKEN", "")

    def serving(self, method: str, path: str, body=None) -> dict:
        r = requests.request(method, self.base + path, json=body, timeout=30)
        r.raise_for_status()
        return r.json()

    def run_workflow(self, run_id: str, shift: float, timeout: int) -> str:
        cmd = ["argo", "submit", "-n", self.ns, "--from", "workflowtemplate/skelty-training-pipeline",
               "-p", f"run-id={run_id}", "-p", f"shift={shift}", "-p", f"image={self.image}",
               "--wait", "-o", "name"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if p.returncode != 0:
            return f"Failed: {p.stderr.strip() or p.stdout.strip()}"
        return "Succeeded"

    def reference_stats(self, run_id: str) -> dict:
        path = f"/data/features/{run_id}/reference_stats.json"
        out = subprocess.run(
            ["kubectl", "-n", self.ns, "exec", "deploy/skelty-serving", "--", "cat", path],
            capture_output=True, text=True, check=True, timeout=60)
        return json.loads(out.stdout)

    def issues(self) -> list[dict]:
        r = requests.get(
            f"https://api.github.com/repos/{self.repo}/issues",
            params={"labels": "retrain", "state": "all", "per_page": 50, "sort": "created", "direction": "desc"},
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"},
            timeout=30)
        r.raise_for_status()
        return [
            {"number": i["number"], "title": i["title"], "state": i["state"],
             "labels": [l["name"] for l in i["labels"]], "created_at": i["created_at"]}
            for i in r.json() if "pull_request" not in i
        ]

    def sleep(self, s: float) -> None:
        time.sleep(s)


@dataclass
class Result:
    step: int
    expected: str
    actual: str = ""
    ok: bool = False
    started: str = ""
    lines: list[str] = field(default_factory=list)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Scenario:
    def __init__(self, env, n=200, shift=1.5, wait=900, poll=10, seed=0):
        self.env, self.n, self.shift, self.wait, self.poll = env, n, shift, wait, poll
        self.rng = np.random.default_rng(seed)
        self.issue_number: int | None = None
        self.t0 = now()

    def _log(self, r: Result, msg: str):
        line = f"{now()} {msg}"
        r.lines.append(line)
        print(f"[bước {r.step}] {line}", flush=True)

    def _send(self, r: Result, shift) -> None:
        # Dữ liệu luôn sinh từ phân phối của baseline, kể cả sau retrain: "dịch 1,5 std"
        # nghĩa là lệch khỏi dữ liệu gốc, còn drift được đo so với tham chiếu của model đang chạy.
        base = self.env.reference_stats(BASELINE_RUN_ID)
        names = self.env.serving("GET", "/model")["feature_names"]
        for row in sample(base, names, self.n, shift, self.rng):
            self.env.serving("POST", "/predict", {"features": row})
        self._log(r, f"đã gửi {self.n} request /predict (shift={shift})")

    def _wait_for(self, fn, r: Result, what: str):
        deadline = time.monotonic() + self.wait
        while True:
            v = fn()
            if v:
                return v
            if time.monotonic() > deadline:
                self._log(r, f"hết {self.wait}s chờ {what}")
                return None
            self.env.sleep(self.poll)

    def step1(self, r):
        status = self.env.run_workflow(BASELINE_RUN_ID, 0.0, self.wait)
        self._log(r, f"workflow {BASELINE_RUN_ID}: {status}")
        if status != "Succeeded":
            r.actual = f"workflow: {status}"
            return False
        rel = self.env.serving("POST", "/reload")
        run_id = self.env.serving("GET", "/model")["run_id"]
        self._log(r, f"/reload -> {rel}; /model.run_id={run_id}")
        r.actual = f"workflow Succeeded; /model.run_id={run_id}"
        return run_id == BASELINE_RUN_ID

    def step2(self, r):
        ref = self.env.reference_stats(self.env.serving("GET", "/model")["run_id"])
        self._send(r, 0.0)
        rep = drift_report(self.env.serving("GET", "/stats"), ref)
        self._log(r, f"n={rep['n']} z={ {k: round(v, 2) for k, v in rep['z'].items()} } drifted={rep['drifted']}")
        r.actual = f"n={rep['n']}, drift={rep['drift']}, feature vượt ngưỡng={len(rep['drifted'])}"
        return rep["n"] >= DRIFT_MIN_N and not rep["drift"]

    def step3(self, r):
        run_id = self.env.serving("GET", "/model")["run_id"]
        ref = self.env.reference_stats(run_id)
        known = {i["number"] for i in self.env.issues()}
        self._send(r, self.shift)
        rep = drift_report(self.env.serving("GET", "/stats"), ref)
        self._log(r, f"n={rep['n']} drifted={rep['drifted']} drift={rep['drift']}")
        if not rep["drift"]:
            r.actual = f"/stats không cho thấy drift (n={rep['n']}, vượt ngưỡng={len(rep['drifted'])})"
            return False

        def new_issue():
            for i in self.env.issues():
                if i["number"] not in known and i["title"].startswith("[drift]"):
                    return i
        issue = self._wait_for(new_issue, r, "issue [drift]")
        if not issue:
            r.actual = "drift có trong /stats nhưng không thấy issue mới"
            return False
        self.issue_number = issue["number"]
        self._log(r, f"issue #{issue['number']}: {issue['title']}")
        r.actual = f"drift={rep['drift']}; issue #{issue['number']} được tạo"
        return True

    def step4(self, r):
        if self.issue_number is None:
            r.actual = "không có issue từ bước 3"
            return False
        n = self.issue_number

        def closed():
            for i in self.env.issues():
                if i["number"] == n and i["state"] == "closed":
                    return i
        issue = self._wait_for(closed, r, f"issue #{n} đóng")
        if not issue:
            r.actual = f"issue #{n} chưa đóng sau {self.wait}s"
            return False
        run_id = self.env.serving("GET", "/model")["run_id"]
        self._log(r, f"issue #{n} đóng, labels={issue['labels']}; /model.run_id={run_id}")
        r.actual = f"issue #{n} đóng (labels={issue['labels']}); /model.run_id={run_id}"
        return "done" in issue["labels"] and run_id == f"issue-{n}"

    def step5(self, r):
        run_id = self.env.serving("GET", "/model")["run_id"]
        ref = self.env.reference_stats(run_id)
        self._send(r, self.shift)
        rep = drift_report(self.env.serving("GET", "/stats"), ref)
        self._log(r, f"model={run_id} n={rep['n']} z={ {k: round(v, 2) for k, v in rep['z'].items()} } drifted={rep['drifted']}")
        r.actual = f"model={run_id}, n={rep['n']}, drift={rep['drift']}, feature vượt ngưỡng={len(rep['drifted'])}"
        return rep["n"] >= DRIFT_MIN_N and not rep["drift"]

    def run(self, steps: list[int]) -> list[Result]:
        results = []
        for num, _, expected in PLAN:
            if num not in steps:
                continue
            r = Result(step=num, expected=expected, started=now())
            try:
                r.ok = bool(getattr(self, f"step{num}")(r))
            except Exception as exc:  # lỗi hạ tầng cũng là "không đạt", không che giấu
                r.ok = False
                r.actual = f"lỗi: {type(exc).__name__}: {exc}"
                self._log(r, r.actual)
            self._log(r, "ĐẠT" if r.ok else "KHÔNG ĐẠT")
            results.append(r)
        return results


def render(results: list[Result], meta: dict) -> str:
    out = ["# Log kịch bản end-to-end SkeltyMLOps PoC", ""]
    out += [f"- {k}: {v}" for k, v in meta.items()]
    out += ["", "## Tóm tắt", "", "| Bước | Kỳ vọng | Thực tế | Kết quả |", "| --- | --- | --- | --- |"]
    for r in results:
        out.append(f"| {r.step} | {r.expected} | {r.actual or '-'} | {'đạt' if r.ok else 'không đạt'} |")
    out += ["", "## Chi tiết", ""]
    for r in results:
        out += [f"### Bước {r.step} (bắt đầu {r.started})", "", "```"] + r.lines + ["```", ""]
    return "\n".join(out)


def main(argv=None, env=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--step", type=int, choices=range(1, 6), action="append",
                    help="chỉ chạy bước này (có thể lặp lại); mặc định chạy cả 5 bước")
    ap.add_argument("--dry-run", action="store_true", help="chỉ in kế hoạch")
    ap.add_argument("--log-dir", default=str(Path(__file__).parent / "logs"))
    args = ap.parse_args(argv)
    steps = args.step or [1, 2, 3, 4, 5]
    n = int(os.environ.get("N_REQUESTS", "200"))
    shift = float(os.environ.get("SHIFT", "1.5"))

    if args.dry_run:
        for num, desc, expected in PLAN:
            if num in steps:
                print(f"Bước {num}: {desc}\n  kỳ vọng: {expected}")
        print(f"(N_REQUESTS={n}, SHIFT={shift}; không gọi cluster, API hay GitHub)")
        return 0

    env = env or Env()
    sc = Scenario(env, n=n, shift=shift, wait=int(os.environ.get("WAIT_SECONDS", "900")))
    results = sc.run(steps)
    meta = {"bắt đầu": sc.t0, "kết thúc": now(), "N_REQUESTS": n, "SHIFT": shift,
            "các bước đã chạy": steps, "môi trường": type(env).__name__}
    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.md"
    path.write_text(render(results, meta), encoding="utf-8")
    print(f"\nĐã ghi log: {path}")
    return 0 if all(r.ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
