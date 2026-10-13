# Improve-Paper-1: PoC SkeltyMLOps

Chia việc xem `task.md`. Tài liệu này mô tả phần của Người B: **Phần 2 (serving API)** và **Phần 5 (kịch bản end-to-end)**.

> Repo hiện chưa có `pipeline/`, `Dockerfile` gốc và `k8s/pvc.yaml`, `k8s/workflow-template.yaml` của `skelty-poc`; các phần này do nhóm đẩy lên sau. Test dùng `serving/tests/fake_pipeline.py` để sinh artifact đúng quy ước chung.

## Phần 2: serving (`skelty-serving:0.1`)

Endpoint (port 8000): `GET /health`, `GET /model`, `POST /predict`, `POST /reload`, `GET /stats`, `GET /metrics`.
Model và `manifest.json` đọc từ `$ARTIFACT_ROOT/models/LATEST` (mặc định `/data`). `/stats` là thống kê (mean, std mẫu) của `STATS_WINDOW` request hợp lệ gần nhất (mặc định 200); cửa sổ được xoá khi `/reload` đổi sang model khác.

Build (từ thư mục gốc repo) và deploy:

```bash
docker build -f serving/Dockerfile -t skelty-serving:0.1 .
kubectl apply -f k8s/serving.yaml
# tùy chọn, chỉ khi dùng Prometheus Operator:
kubectl apply -f k8s/servicemonitor.yaml
```

`scikit-learn` trong `serving/requirements.txt` phải cùng phiên bản với image pipeline đã sinh `model.joblib`.

**Lưu ý PVC:** `skelty-artifacts` là ReadWriteOnce, nên pod serving phải nằm cùng node với các pod Argo/orchestrator/CronJob. Pod `Pending` vì volume thì kiểm tra điều này trước.

Thử bằng curl:

```bash
kubectl -n argo port-forward svc/skelty-serving 8000:8000 &
curl localhost:8000/health
curl localhost:8000/model
curl -XPOST localhost:8000/predict -H 'content-type: application/json' \
  -d '{"features": {"<tên feature trong /model>": 0.0}}'
curl localhost:8000/stats
curl -XPOST localhost:8000/reload
curl localhost:8000/metrics
```

Test: `pip install -r serving/requirements-dev.txt && python -m pytest serving/tests`

## Phần 5: kịch bản end-to-end (`scenario/run_scenario.py`)

```bash
kubectl -n argo port-forward svc/skelty-serving 8000:8000 &
export GITHUB_TOKEN=... GITHUB_REPO=owner/repo   # token chỉ cần đọc Issues
python scenario/run_scenario.py --dry-run         # chỉ in kế hoạch
python scenario/run_scenario.py                   # chạy cả 5 bước
python scenario/run_scenario.py --step 2          # chạy riêng từng bước
```

Cần `argo` và `kubectl` trong PATH, orchestrator chạy với `DEFAULT_SHIFT=1.5`. Log nằm ở `scenario/logs/<timestamp>.md` kèm bảng tóm tắt đạt/không đạt; bước lỗi được ghi "không đạt". Tham số: `N_REQUESTS`, `SHIFT`, `WAIT_SECONDS`, `PIPELINE_IMAGE`, `SERVING_URL`, `ARGO_NAMESPACE`.

Test: `python -m pytest scenario/tests` (dịch vụ giả, xem docstring trong file).

## Chưa kiểm chứng

Chưa chạy trên cluster, chưa build Docker image, chưa thử `k8s/*.yaml` bằng `kubectl apply` (chỉ kiểm tra cú pháp YAML), chưa chạy kịch bản với GitHub, Argo, CronJob và orchestrator thật.
