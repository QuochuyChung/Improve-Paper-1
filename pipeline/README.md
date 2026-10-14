# Pipeline huấn luyện (`skelty-poc:0.1`)

Ba bước chạy tuần tự bằng Argo Workflows, ghi artifact vào `$ARTIFACT_ROOT` (mặc định `/data`):

| Bước | Script | Ghi ra |
| --- | --- | --- |
| 1 | `acquire.py` | `raw/<run-id>/data.csv`, `manifest.json` (SHA-256) |
| 2 | `process.py` | `features/<run-id>/train.csv`, `test.csv`, `reference_stats.json`, `manifest.json` |
| 3 | `train.py` | `models/<run-id>/model.joblib`, `metrics.json`, `manifest.json`, rồi `models/LATEST` |

Mỗi script nhận `--run-id` (bắt buộc) và `--shift` (mặc định 0). Chỉ `acquire.py` dùng `--shift`:
nó dịch mọi feature đi `shift` x std so với phân phối gốc, và ranh giới nhãn dịch theo.
Dữ liệu tổng hợp, cố định seed 42 nên chạy lại cùng tham số cho cùng kết quả. Vì vậy `baseline-001`
(shift 0) và `issue-<số>` (shift 1.5) có accuracy và f1 như nhau; khác nhau ở tham số model
(ranh giới quyết định dịch theo dữ liệu) và ở `reference_stats.json`.

`LATEST` chỉ được ghi sau khi model, metrics và manifest đã xong, nên lần chạy lỗi không làm đổi model đang dùng.
`run-id` chỉ nhận ký tự `A-Za-z0-9._-` (tối đa 63), chặn đường dẫn kiểu `../x`.

## Test

```bash
pip install -r pipeline/requirements-dev.txt
python -m pytest pipeline/tests
```

## Build và chạy trên cụm

```bash
docker build -t skelty-poc:0.1 .
kubectl apply -f k8s/pv-skelty-artifacts.yaml -f k8s/pvc.yaml -f k8s/workflow-template.yaml
argo submit -n argo --from workflowtemplate/skelty-training-pipeline -p run-id=baseline-001 --watch
```

Image phải có trên node chạy pod (import vào từng node hoặc đẩy lên registry mà node kéo được).
Workflow chạy bằng ServiceAccount `argo-workflow`. PV trỏ NFS `192.168.58.24:/data/skelty-artifacts`,
thư mục này phải tạo sẵn trên NFS server.

Phiên bản `scikit-learn` trong `pipeline/requirements.txt` phải khớp `serving/requirements.txt`.

## Chưa kiểm chứng

Test pytest đã chạy thật (xem commit). Chưa build image Docker, chưa apply manifest lên cụm,
chưa chạy Workflow thật trên Argo.
