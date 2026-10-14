# Improve-Paper-1: PoC SkeltyMLOps

Chia việc xem `task.md`. Repo hiện có **Phần 2 (serving API)**, **Phần 4
(orchestrator)** và **Phần 5 (kịch bản end-to-end)**.

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

## Phần 4: orchestrator (`skelty-orchestrator:0.1`)

Luồng xử lý:

```text
GitHub Issue [drift] + retrain
  -> thêm in-progress
  -> tạo/đọc Workflow retrain-issue-<số> từ WorkflowTemplate
  -> chờ Argo kết thúc
  -> đọc metrics.json -> POST /reload
  -> comment kết quả -> done -> đóng issue
```

Workflow có tên xác định theo issue nên việc gọi lại hoặc restart không tạo bản sao.
Issue đã có label `in-progress` vẫn được đọc lại để tiếp tục workflow đang tồn tại.
Issue lỗi JSON được comment và bỏ qua; workflow lỗi/timeout được comment, bỏ
`in-progress` và giữ issue mở.

Build, test và deploy:

```bash
docker build -f orchestrator/Dockerfile -t skelty-orchestrator:0.1 .
pip install -r orchestrator/requirements-dev.txt
python -m pytest orchestrator/tests
kubectl apply -f k8s/orchestrator.yaml
kubectl -n argo logs -f deploy/skelty-orchestrator
```

Manifest đọc `GITHUB_TOKEN` và `GITHUB_REPO` từ Secret `skelty-github`. Tạo
Secret mà không ghi token vào file hay lịch sử Git:

```bash
kubectl -n argo create secret generic skelty-github \
  --from-literal=GITHUB_TOKEN='<token>' \
  --from-literal=GITHUB_REPO='<owner>/<repo>'
```

Biến cấu hình: `ARGO_NAMESPACE` (mặc định `argo`), `SERVING_URL`,
`ARTIFACT_ROOT`, `POLL_SECONDS`, `WORKFLOW_POLL_SECONDS`,
`WORKFLOW_TIMEOUT_SECONDS`, `DEFAULT_SHIFT` và `PIPELINE_IMAGE`. Với kịch bản
E2E dùng `DEFAULT_SHIFT=1.5`.

ServiceAccount chỉ có quyền `create`, `get`, `list` resource `workflows` trong
namespace `argo`. PVC `skelty-artifacts` là ReadWriteOnce, vì vậy orchestrator,
serving, monitoring và các pod Argo phải cùng node.

## Chưa kiểm chứng

Chưa chạy trên cluster, chưa build Docker image, chưa thử `k8s/*.yaml` bằng
`kubectl apply`, chưa gọi GitHub thật và chưa chạy kịch bản với Argo, CronJob và
orchestrator thật. Trạng thái tích hợp báo cáo SWD391-19 nằm tại
`report/INTEGRATION_STATUS.md`; repo còn thiếu source LaTeX và hai section đầu vào.
