# Phần 3: drift monitor (`skelty-monitor:0.1`)

`monitoring/drift_check.py` là một script chạy ngắn (CronJob mỗi 5 phút). Mỗi lần chạy:

1. `GET $SERVING_URL/model` lấy run-id model đang dùng, `GET /stats` lấy thống kê dữ liệu đang đến.
2. Đọc `$ARTIFACT_ROOT/features/<run-id>/reference_stats.json` (mean, std lúc huấn luyện).
3. Mỗi feature: `z = |mean hiện tại - mean tham chiếu| / std tham chiếu`.
   **Có drift** khi ít nhất 3 feature có `z > 1,0` và `n >= 100`. Ba ngưỡng là tham số (xem dưới).
4. Đẩy 3 metric lên Pushgateway (nếu có `PUSHGATEWAY_URL`).
5. Có drift và **chưa có issue mở nào mang label `retrain`** thì tạo issue `[drift] ...` kèm khối JSON
   `{"type": "drift", "model_version", "drifted_features", "detected_at"}` (đúng định dạng orchestrator đọc).

Mã thoát: `0` mọi trường hợp bình thường (kể cả có drift và đã tạo issue), `1` khi lỗi mạng hoặc lỗi API
(API serving, GitHub, thiếu file tham chiếu, thiếu token khi cần tạo issue). Lỗi đẩy metric lên Pushgateway
chỉ cảnh báo, không đổi mã thoát.

Không tạo issue mới khi còn issue `retrain` mở. Orchestrator đóng issue sau khi retrain xong và `/reload` xóa
cửa sổ `/stats`, nên không có vòng lặp vô hạn: sau retrain phải gom lại tối thiểu 100 mẫu mới mới có thể báo drift.

## Chạy thử (dry-run)

`--dry-run` chỉ in kết quả: không tạo issue, không đẩy metric. Nếu có `GITHUB_TOKEN` và `GITHUB_REPO` thì nó vẫn
đọc (chỉ đọc) danh sách issue để nói "sẽ tạo" hay "đã có issue mở".

```bash
kubectl -n argo port-forward svc/skelty-serving 8000:8000 &
export SERVING_URL=http://localhost:8000 ARTIFACT_ROOT=/data/skelty-artifacts   # đường dẫn tới thư mục artifact
pip install -r monitoring/requirements.txt
python monitoring/drift_check.py --dry-run
```

Biến môi trường: `SERVING_URL` (mặc định `http://skelty-serving:8000`), `ARTIFACT_ROOT` (mặc định `/data`),
`GITHUB_TOKEN`, `GITHUB_REPO` (`owner/repo`), `PUSHGATEWAY_URL`.
Tham số (cờ hoặc biến môi trường): `--z-threshold` / `DRIFT_Z_THRESHOLD` (1.0), `--min-features` /
`DRIFT_MIN_FEATURES` (3), `--min-samples` / `DRIFT_MIN_SAMPLES` (100).

## Metric và vì sao dùng Pushgateway

`drift_detected` (0 hoặc 1), `drifted_feature_count`, `max_feature_zscore`, đẩy bằng `PUT
$PUSHGATEWAY_URL/metrics/job/skelty_drift_check`.

Job chỉ sống vài giây nên Prometheus không kịp kéo (scrape) trực tiếp. Chọn Pushgateway vì cụm đã cài sẵn
(`prometheus-pushgateway` trong `monitoring-namespace`, có ServiceMonitor). Cách textfile cần node-exporter đọc file
trên host, không hợp với pod CronJob. Nhược điểm của Pushgateway: giá trị cuối cùng được giữ lại cho tới lần đẩy sau,
nên nếu CronJob ngừng chạy thì metric đứng yên chứ không biến mất.

## Secret, build và deploy

Secret `skelty-github` (namespace `argo`) có hai khóa, dùng chung với orchestrator. Tạo mà không ghi token vào
file hay lịch sử shell:

```bash
read -r -s -p "GITHUB_TOKEN: " T; echo
kubectl -n argo create secret generic skelty-github \
  --from-literal=GITHUB_TOKEN="$T" --from-literal=GITHUB_REPO='<owner>/<repo>'
unset T
```

Token fine-grained chỉ cho repo này, quyền Issues đọc/ghi.

```bash
docker build -f monitoring/Dockerfile -t skelty-monitor:0.1 .
# cụm không có registry: docker save, scp sang từng node, rồi trên MỖI node:
#   sudo ctr -n k8s.io images import skelty-monitor.tar
kubectl apply -f k8s/drift-cronjob.yaml
kubectl -n argo create job drift-manual --from=cronjob/skelty-drift-check   # chạy tay một lần
kubectl -n argo logs job/drift-manual
```

CronJob mount PVC `skelty-artifacts` chế độ chỉ đọc, chạy bằng user không phải root (đọc được vì file do pipeline
ghi quyền `644`/`755`), `concurrencyPolicy: Forbid`, lưu 3 job thành công và 3 job lỗi gần nhất.

## Test

```bash
pip install -r monitoring/requirements-dev.txt
python -m pytest monitoring/tests
```

24 test dùng API giả và GitHub giả, phủ: không drift, drift lần đầu, drift khi đã có issue mở, `n < 100`,
ngưỡng biên (`z` bằng đúng 1,0; đúng 2 feature; đúng `n = 100`), lỗi API serving, lỗi GitHub, thiếu file tham chiếu,
run-id độc hại (`../`), dry-run, Pushgateway lỗi, và một test kiểm tra thân issue qua đúng bộ phân tích của
`orchestrator.loop.parse_drift_payload` (cần cài `kubernetes`, nếu thiếu thì test này bị bỏ qua).

## Chưa kiểm chứng

Chưa build image Docker, chưa apply CronJob lên cụm, chưa tạo issue trên GitHub thật, chưa đẩy metric lên
Pushgateway thật và chưa xem Prometheus kéo được metric đó. Đã chạy thật ở máy cục bộ: script qua HTTP với API
serving thật và artifact do pipeline thật sinh ra (chỉ ở chế độ `--dry-run`).
