# Chia việc PoC SkeltyMLOps cho 5 người, mỗi người một prompt


## Cách chia việc

Quochuy tạo repo GitHub và làm các bước cần quyền vào homelab (Phần 9). Mọi việc còn lại, kể cả viết code, giao cho 4 người còn lại, mỗi người tự prompt agent cho phần của mình. Các phần chỉ nối với nhau qua mục "Giao diện chung" bên dưới nên làm song song được. Mọi prompt giả định repo là bản `skelty-poc` đã gửi (3 script pipeline, `storage.py`, Dockerfile, PVC, WorkflowTemplate).

| Phần | Việc | Ai làm | Cần cluster |
| --- | --- | --- | --- |
| 1 | Chấm điểm 4 kiến trúc, viết phần Cải tiến 1 | Người A | Không |
| 2 | FastAPI phục vụ model, đóng gói image | Người B | Không khi viết |
| 3 | Monitoring, phát hiện drift, tự tạo ticket | Người D | Không khi viết |
| 4 | Orchestrator: đọc ticket, chạy Argo | Người C | Không khi viết |
| 5 | Script kịch bản end-to-end | Người B | Không khi viết, chạy cần cluster |
| 6 | Viết phần PoC trong báo cáo | Người A | Không |
| 7 | Review chéo code Phần 2 đến 5 | Người D | Không |
| 8 | Tích hợp vào báo cáo chính, biên dịch, điền kết quả | Người C | Không, nhưng cần log từ Quochuy ở cuối |
| 9 | Tạo repo GitHub, label, token, mời nhóm vào repo; mọi bước chạy trên homelab | Quochuy | Có (riêng việc tạo repo thì không) |

Tên Người A đến D là chỗ để nhóm ghi tên thật. Phần 4 (orchestrator) nặng nhất nên Người C chỉ nhận thêm Phần 8, là phần làm cuối cùng.

## Giao diện chung

Đưa bảng này cho cả 5 người. Quy ước do tôi đề xuất, nhóm nên chỉnh trước khi phát prompt.

| Thành phần | Quy ước |
| --- | --- |
| Artifact | `/data/models/<run-id>/model.joblib`, `metrics.json`, `manifest.json` (có `feature_names`). `/data/models/LATEST` chứa run-id mới nhất. `/data/features/<run-id>/reference_stats.json` chứa mean và std từng feature. |
| API (Phần 2) | Service `skelty-serving`, port 8000, namespace `argo`. Endpoint: `GET /health`, `GET /model`, `POST /predict` với `{"features": {tên: giá trị}}`, `POST /reload`, `GET /stats`, `GET /metrics`. `/stats` trả `{"n": số mẫu, "features": {tên: {"mean": .., "std": ..}}}`. |
| Ticket (Phần 3 tạo, Phần 4 đọc) | GitHub Issue có label `retrain`, tiêu đề bắt đầu bằng `[drift]`. Thân issue chứa một khối JSON `{"type": "drift", "model_version": "..", "drifted_features": [..], "detected_at": ".."}`. Người 4 đổi label sang `in-progress`, xong thì comment kết quả, gắn `done` và đóng issue. Người 3 không tạo issue mới khi còn issue `retrain` đang mở. |
| Argo (Phần 4 gọi) | WorkflowTemplate `skelty-training-pipeline`, namespace `argo`, tham số `run-id`, `shift`, `image`. Quy ước `run-id` = `issue-<số issue>`. |
| Quy tắc drift (Phần 3 cài, Phần 5 dùng dựng kịch bản) | Với mỗi feature, lấy chênh lệch tuyệt đối giữa mean hiện tại và mean tham chiếu, chia cho std tham chiếu. Có drift khi ít nhất 3 feature vượt 1,0 và cửa sổ có tối thiểu 100 mẫu. Dữ liệu `--shift=1.5` dịch mọi feature 1,5 std nên sẽ kích hoạt. |
| Cấu hình | `GITHUB_TOKEN` trong Secret `skelty-github`, `GITHUB_REPO` dạng `owner/repo`. |

**Bổ sung:** image đặt tên `skelty-poc:0.1` (pipeline), `skelty-serving:0.1`, `skelty-monitor:0.1`, `skelty-orchestrator:0.1`. Secret `skelty-github` trong namespace `argo` có hai khóa `GITHUB_TOKEN` và `GITHUB_REPO` (dạng `owner/repo`), mọi manifest đọc cả hai khóa này từ Secret qua `secretKeyRef`.

## Phần 1: chấm điểm 4 kiến trúc (Người A)

Đính kèm PDF paper. Prompt này độc lập, chạy được ngay. Nếu có thời gian, đính kèm thêm 3 paper gốc của Woźniak, Najafabadi và Kreuzberger để điểm của 3 kiến trúc kia dựa vào chính họ chứ không chỉ dựa vào lời nhận xét của SkeltyMLOps.

```
Bạn là trợ lý nghiên cứu. Tôi đính kèm paper "SkeltyMLOps: Orchestrating Collaborative MLOps Activities" (Daoud và cộng sự, 2025, CEUR-WS Vol-4109).

Nhiệm vụ: chấm điểm chính SkeltyMLOps cùng với 3 kiến trúc mà Section 7 của paper so sánh (Woźniak và cộng sự, Najafabadi và cộng sự, Kreuzberger và cộng sự). Lý do: paper chỉ chấm các phương pháp khác mà không chấm chính nó.

Bộ 6 tiêu chí (rút từ Section 7). Hãy đối chiếu lại với văn bản gốc và báo tôi nếu thấy lệch:
1. Có component quản lý dữ liệu.
2. Actor và trách nhiệm được định nghĩa rõ.
3. Orchestrator được vẽ và mô tả tường minh.
4. Versioning đầy đủ (dữ liệu thô, tập train/test, feature, model, code).
5. Monitoring bao phủ hiệu năng model, data drift, tài nguyên và hạ tầng.
6. Feedback loop kích hoạt retrain.

Quy tắc bắt buộc:
- Thang 3 mức: Có / Một phần / Không đủ bằng chứng.
- Mỗi ô phải trích section, bảng hoặc hình trong paper, kèm một câu trích ngắn đúng nguyên văn. Không đoán, không dùng kiến thức ngoài paper.
- Với 3 kiến trúc kia, chỉ dùng những gì Section 7 mô tả về chúng. Thiếu thì ghi "Không đủ bằng chứng".
- Với SkeltyMLOps, tách rõ "tự nhận" (paper nói có) và "đã kiểm chứng" (có thực nghiệm). Paper chưa có đánh giá thực nghiệm, nên mọi ô đều là "tự nhận".

Kết quả cần có:
1. Bảng 4 kiến trúc x 6 tiêu chí, mỗi ô có mức điểm và trích dẫn.
2. Đoạn phản biện tối đa 150 từ: tiêu chí do chính tác giả chọn nên thiên về điểm mạnh của họ, và những gì paper chưa kiểm chứng.
3. Mã LaTeX của bảng và đoạn phản biện để chèn vào báo cáo.
Viết bằng tiếng Việt, giữ nguyên thuật ngữ tiếng Anh.
```

Ghi chú: ghi trong báo cáo đây là đánh giá của nhóm, không phải của tác giả. Lưu mã LaTeX thành file scoring\_section.tex để Người C chèn vào báo cáo.

## Phần 2: FastAPI phục vụ model và deploy lên K8s (Người B)

Đính kèm repo `skelty-poc`. Dựng component API Development, đồng thời chuẩn bị đầu vào cho monitoring ở Phần 3 (thống kê dữ liệu đang đến).

```
Tôi đính kèm repo skelty-poc, PoC thu nhỏ của kiến trúc SkeltyMLOps (paper Daoud và cộng sự, 2025). Hiện repo có: pipeline/storage.py, acquire.py, process.py, train.py (chạy qua Argo WorkflowTemplate "skelty-training-pipeline" trong namespace argo, xem k8s/workflow-template.yaml), Dockerfile (python:3.12-slim, ARTIFACT_ROOT=/data, PYTHONPATH=/app/pipeline), k8s/pvc.yaml (PVC "skelty-artifacts", ReadWriteOnce, 2Gi).

Qui ước artifact: model ở /data/models/<run-id>/model.joblib, cùng metrics.json và manifest.json (manifest có trường feature_names). File /data/models/LATEST chứa run-id mới nhất. Thống kê tham chiếu (mean, std từng feature) nằm ở /data/features/<run-id>/reference_stats.json.

Nhiệm vụ: dựng component API Development.
1. Tạo serving/app.py dùng FastAPI:
   - GET /health.
   - GET /model: run-id đang dùng, metrics, feature_names.
   - POST /predict: nhận JSON {"features": {tên: giá trị}}, trả về dự đoán, xác suất và model_version. Thiếu hoặc sai feature thì trả lỗi 422 rõ ràng.
   - POST /reload: đọc lại /data/models/LATEST và nạp model mới mà không restart pod.
   - GET /stats: trả JSON {"n": số mẫu, "features": {tên: {"mean": .., "std": ..}}}, là thống kê của các feature trong cửa sổ trượt N request gần nhất (N mặc định 200, đổi qua biến môi trường). Đây là đầu vào cho bước phát hiện drift sau này.
   - GET /metrics theo định dạng Prometheus (prometheus-client): predictions_total, histogram độ trễ, gauge model_version_info.
2. Tạo serving/Dockerfile và requirements riêng (image skelty-serving:0.1). Không sửa pipeline/*.py nếu chưa nói rõ lý do.
3. Tạo k8s/serving.yaml: Deployment 1 replica + Service ClusterIP tên skelty-serving, port 8000, trong namespace argo, mount PVC skelty-artifacts chế độ read-only, có readiness probe ở /health và annotation prometheus.io/scrape. Lưu ý PVC là ReadWriteOnce nên pod serving và pod Argo phải cùng một node: hãy ghi chú điều này trong file và README. Thêm thêm file k8s/servicemonitor.yaml tùy chọn cho trường hợp cluster dùng Prometheus Operator.
4. Viết test (pytest, TestClient): chạy 3 script pipeline vào thư mục tạm, trỏ ARTIFACT_ROOT vào đó, rồi kiểm tra /predict, /reload, /stats, /metrics. Chạy test thật và dán kết quả.
5. Cập nhật README: cách build, apply, và thử bằng curl.

Quy tắc: chỉ báo đã làm những gì đã chạy thật. Phần chưa thử trên cluster (vì bạn không có cluster) phải nói rõ là chưa kiểm chứng. Trả lời ngắn: file đã tạo, lệnh chạy, kết quả test.
```

**Quyết định trước khi chạy:** Prometheus trong homelab thu metric bằng annotation hay bằng ServiceMonitor. Nếu là annotation thì bỏ file `servicemonitor.yaml`.

## Phần 3: monitoring, phát hiện drift, tự tạo ticket (Người D)

Đính kèm repo `skelty-poc`. Dựng phần Deployment & Monitoring còn thiếu. Không cần cluster khi viết, vì test dùng API giả và GitHub giả.

```
Tôi đính kèm repo skelty-poc, PoC thu nhỏ của kiến trúc SkeltyMLOps (paper Daoud và cộng sự, 2025). Nhóm 5 người làm song song; bạn làm phần Monitoring: phát hiện drift và tự tạo ticket. Các phần khác do người khác làm, bạn chỉ dùng chúng qua giao diện dưới đây, nên phải test bằng đối tượng giả.

Giao diện bạn dùng:
- API model (người khác làm): Service skelty-serving, port 8000, namespace argo. GET /stats trả {"n": số mẫu, "features": {tên: {"mean": .., "std": ..}}}. GET /model trả run-id (model_version) đang dùng.
- Thống kê tham chiếu: /data/features/<run-id>/reference_stats.json, dạng {tên feature: {"mean": .., "std": ..}}. run-id lấy từ GET /model.
- Ticket: GitHub Issue có label "retrain", tiêu đề bắt đầu bằng "[drift]". Thân issue chứa một khối JSON {"type": "drift", "model_version": "..", "drifted_features": [..], "detected_at": ".."}. Không được tạo issue mới nếu đang còn issue mở có label "retrain".
- Cấu hình qua biến môi trường: SERVING_URL, ARTIFACT_ROOT (mặc định /data), GITHUB_TOKEN, GITHUB_REPO (dạng owner/repo).

Quy tắc drift: với mỗi feature, lấy chênh lệch tuyệt đối giữa mean hiện tại (từ /stats) và mean tham chiếu, chia cho std tham chiếu. Có drift khi ít nhất 3 feature vượt 1,0 và n >= 100. Các ngưỡng là tham số.

Nhiệm vụ:
1. Tạo monitoring/drift_check.py. Mỗi lần chạy: đọc /stats, so với tham chiếu, in kết quả từng feature. Nếu có drift và chưa có issue retrain đang mở thì tạo issue đúng định dạng trên (GitHub REST API, thư viện requests). Thoát mã 0 trong mọi trường hợp bình thường, mã khác 0 khi lỗi mạng hoặc lỗi API. Có cờ --dry-run chỉ in, không tạo issue.
2. Xuất metric Prometheus cho kết quả: drift_detected (0 hoặc 1), drifted_feature_count, max_feature_zscore. Chọn cách đơn giản nhất phù hợp với job chạy ngắn (Pushgateway hoặc file textfile) và giải thích lý do.
3. Tạo monitoring/Dockerfile và k8s/drift-cronjob.yaml: CronJob chạy mỗi 5 phút, mount PVC skelty-artifacts chế độ read-only, dùng image skelty-monitor:0.1, lấy GITHUB_TOKEN và GITHUB_REPO từ Secret skelty-github.
4. Viết test pytest, dùng API giả và GitHub giả. Phủ các trường hợp: không drift, drift lần đầu, drift khi đã có issue mở (không tạo thêm), n < 100, lỗi API. Chạy test thật và dán kết quả.
5. Cập nhật README: cách chạy dry-run và cách tạo Secret.

Quy tắc: chỉ báo những gì đã chạy thật. Chưa thử trên cluster hoặc GitHub thật thì nói rõ. Trả lời ngắn: file đã tạo, lệnh chạy, kết quả test.
```

**Chuẩn bị trước:** repo GitHub dùng làm nơi chứa ticket, ba label `retrain`, `in-progress`, `done`, và một token có quyền đọc ghi Issues; cả ba do Quochuy tạo (Phần 9), lúc viết code chưa cần, dùng GitHub giả để test. Trong homelab cần biết Prometheus có Pushgateway hay thu bằng textfile.

## Phần 4: orchestrator nối GitHub Issues với Argo (Người C)

Đính kèm repo `skelty-poc`. Đây là component MLOps Process Orchestration, phần làm nên điểm riêng của paper. Không cần cluster khi viết, vì test dùng GitHub giả và Kubernetes giả.

```
Tôi đính kèm repo skelty-poc, PoC thu nhỏ của kiến trúc SkeltyMLOps (paper Daoud và cộng sự, 2025). Nhóm 5 người làm song song; bạn làm component MLOps Process Orchestration: đọc ticket và dịch thành lệnh chạy pipeline. Các phần khác do người khác làm, bạn chỉ dùng chúng qua giao diện dưới đây, nên phải test bằng đối tượng giả.

Giao diện bạn dùng:
- Ticket (người khác tạo): GitHub Issue có label "retrain", tiêu đề bắt đầu bằng "[drift]". Thân issue chứa một khối JSON {"type": "drift", "model_version": "..", "drifted_features": [..], "detected_at": ".."}, có thể có thêm trường "shift" (số).
- Argo: WorkflowTemplate "skelty-training-pipeline" trong namespace argo, tham số run-id, shift, image. Quy ước run-id = "issue-<số issue>". shift lấy từ thân issue nếu có, nếu không thì lấy biến môi trường DEFAULT_SHIFT (mặc định 0).
- Artifact: /data/models/<run-id>/metrics.json (accuracy, f1). Mount PVC skelty-artifacts chế độ read-only.
- API model: Service skelty-serving, port 8000. POST /reload để nạp model mới nhất.
- Cấu hình qua biến môi trường: GITHUB_TOKEN, GITHUB_REPO (owner/repo), ARGO_NAMESPACE, SERVING_URL, POLL_SECONDS (mặc định 30), DEFAULT_SHIFT, WORKFLOW_TIMEOUT_SECONDS.

Hành vi cần có:
- Polling GitHub mỗi POLL_SECONDS (homelab không có webhook), lấy issue mở có label "retrain" mà chưa có label "in-progress" hoặc "done".
- Nhận việc: thêm label "in-progress", tạo Workflow trên cluster (resource Workflow có workflowTemplateRef, tên retrain-issue-<số>) qua Kubernetes API với xác thực in-cluster.
- Idempotent: mỗi issue chỉ tạo tối đa một Workflow, kể cả khi orchestrator restart giữa chừng.
- Chờ Workflow xong (poll trạng thái, có timeout). Thành công: gọi POST /reload, comment vào issue (run-id, accuracy, f1 đọc từ metrics.json, model_version mới), gắn "done", bỏ "in-progress", đóng issue. Thất bại hoặc timeout: comment lý do, bỏ "in-progress", để issue mở.
- Issue không đọc được JSON hợp lệ: comment báo lỗi, bỏ qua, không crash.

Nhiệm vụ:
1. Tạo orchestrator/ gồm main.py và các module tách biết (github_client, argo_client, loop). Thư viện: requests và kubernetes.
2. Tạo orchestrator/Dockerfile và k8s/orchestrator.yaml: Deployment 1 replica, ServiceAccount, Role và RoleBinding chỉ đủ quyền create, get, list workflows trong namespace argo, mount PVC read-only, image skelty-orchestrator:0.1, GITHUB_TOKEN và GITHUB_REPO từ Secret skelty-github. Ghi chú PVC là ReadWriteOnce nên phải cùng node với các pod khác.
3. Viết test pytest với GitHub giả và Kubernetes giả. Phủ: không có issue, issue mới (tạo đúng một Workflow, chạy lại vẫn một), Workflow thành công, Workflow lỗi, timeout, issue hỏng JSON, restart giữa chừng. Chạy test thật và dán kết quả.
4. Cập nhật README: sơ đồ luồng ticket → orchestrator → Argo → reload, cách cấu hình, cách tạo Secret.

Quy tắc: chỉ báo những gì đã chạy thật. Chưa thử trên cluster hoặc GitHub thật thì nói rõ. Trả lời ngắn: file đã tạo, lệnh chạy, kết quả test.
```

**Chuẩn bị trước:** cùng repo GitHub, label và token như Phần 3, do Quochuy tạo. Khi chạy thật, đặt `DEFAULT_SHIFT=1.5` để lần retrain dùng dữ liệu đã dịch, nếu không model mới sẽ giống hệt model cũ.

## Phần 5: script kịch bản end-to-end (Người B)

Đính kèm repo `skelty-poc` sau khi Phần 2 đến 4 đã nằm trong repo. Viết được trước bằng dịch vụ giả; chạy thật cần cluster.

```
Tôi đính kèm repo skelty-poc, PoC thu nhỏ của kiến trúc SkeltyMLOps (paper Daoud và cộng sự, 2025). Repo đã có: API model (Service skelty-serving, port 8000), CronJob phát hiện drift tạo GitHub Issue, orchestrator đọc issue và chạy Argo. Bạn viết script kiểm chứng end-to-end.

Giao diện: GitHub Issue label "retrain" (tiêu đề "[drift]", thân có JSON); Argo WorkflowTemplate "skelty-training-pipeline" trong namespace argo, tham số run-id, shift, image; API có GET /model, POST /predict với {"features": {tên: giá trị}}, POST /reload, GET /stats. Quy tắc drift: ít nhất 3 feature lệch mean quá 1,0 std tham chiếu với tối thiểu 100 mẫu. Orchestrator chạy retrain với shift lấy từ biến DEFAULT_SHIFT (dùng 1.5 cho kịch bản).

Nhiệm vụ: tạo scenario/run_scenario.py, chạy từ máy có kubectl, truy cập được API và GitHub. Các bước:
1. Chạy workflow lần đầu với shift=0, run-id baseline-001, chờ xong, gọi /reload.
2. Gửi ít nhất 200 request /predict bằng dữ liệu gốc, kiểm tra /stats và xác nhận chưa drift.
3. Gửi ít nhất 200 request bằng dữ liệu dịch 1,5 std, chờ drift được phát hiện và issue được tạo.
4. Chờ orchestrator xử lý: workflow retrain chạy, issue đóng, /model chuyển sang run-id issue-<số>.
5. Gửi lại dữ liệu dịch, xác nhận với model mới không còn drift.
Mỗi bước ghi timestamp, kết quả và lưu log vào scenario/logs/<timestamp>.md, kèm bảng tóm tắt gồm bước, kỳ vọng, thực tế, đạt hay không. Có cờ --step để chạy từng bước và --dry-run để chỉ in kế hoạch. Nếu một bước không đạt thì ghi "không đạt", không được sửa số liệu hay bỏ qua bước. Phần không chạy được ngoài cluster thì test bằng dịch vụ giả và nói rõ đã test giả.

Quy tắc: chỉ báo những gì đã chạy thật. Trả lời ngắn: file đã tạo, lệnh chạy, kết quả test.
```

## Phần 6: viết phần PoC trong báo cáo (Người A)

Đính kèm file `.tex` báo cáo nhóm (bản `SkeltyMLOps_report.tex` trong Project, hoặc bản nhóm đang dùng) và bảng "Giao diện chung" của tài liệu này. Khung viết được ngay; con số kết quả chờ log chạy thật.

```
Tôi đính kèm file báo cáo .tex của nhóm (phân tích paper SkeltyMLOps, Daoud và cộng sự, 2025). Nhóm đang dựng một PoC thu nhỏ của kiến trúc này trên cluster K8s nhỏ. Code do người khác viết, bạn chỉ viết phần báo cáo.

PoC gồm: pipeline huấn luyện chạy bằng Argo Workflows (nhận dữ liệu, xử lý feature, huấn luyện model scikit-learn, lưu artifact có version kèm hash SHA-256); API FastAPI phục vụ model và xuất metric; CronJob phát hiện drift (một feature lệch mean quá 1,0 std tham chiếu, ít nhất 3 feature, tối thiểu 100 mẫu) và tự tạo GitHub Issue; orchestrator đọc issue, chạy lại pipeline rồi nạp model mới vào API. Kịch bản kiểm chứng gồm 5 bước: chạy baseline, gửi dữ liệu gốc và xác nhận chưa drift, gửi dữ liệu dịch 1,5 std và xác nhận phát hiện drift cùng issue được tạo, orchestrator retrain và đóng issue, gửi lại dữ liệu dịch và xác nhận hết drift.

Nhiệm vụ: viết mục PoC vào file poc_section.tex riêng để nhóm chèn bằng \input, không sửa các section người khác đang viết. Nội dung gồm:
- Mục tiêu và phạm vi PoC.
- Bảng ánh xạ component trong Figure 3 của paper sang cài đặt, cột mức độ (đầy đủ, rút gọn, giả lập).
- Sơ đồ kiến trúc PoC (TikZ).
- Kịch bản kiểm chứng.
- Kết quả: dùng placeholder "CHƯA CÓ KẾT QUẢ THẬT" cho mọi con số cho đến khi có log; tuyệt đối không bịa hay ước lượng số.
- Khác biệt so với thiết kế trong paper và hạn chế: quy mô nhỏ, dữ liệu tabular nhỏ, một model đơn giản, orchestrator không dùng BPMN, storage dạng file thay cho MLflow hay DVC, gộp các component lưu trữ, chạy trên một cluster nhỏ, chưa phải production.
- Kết luận thận trọng.
Giọng học thuật, tiếng Việt, giữ thuật ngữ tiếng Anh. Luôn gọi là PoC, không gọi là production. Cuối cùng liệt kê chỗ nào trong poc_section.tex còn phải điền khi có log.

Quy tắc: chỉ viết những gì có trong mô tả trên. Không tự thêm tính năng hay kết quả. Trả lời ngắn: file đã tạo và danh sách chỗ còn trống.
```

## Phần 7: review chéo code (Người D)

Việc duy nhất: review chéo code của Phần 2 đến 5 khi chúng xong (repo GitHub do Quochuy tạo, xem Phần 9). Review giúp bắt lỗi lệch giao diện giữa các phần do những người khác nhau viết riêng. Người D ưu tiên review phần mình không viết (Người D tự viết Phần 3).

**Review chéo (khi Phần 2 đến 5 đã có code)**

Đính kèm repo `skelty-poc` đã có `serving/`, `monitoring/`, `orchestrator/`, `scenario/` và bảng "Giao diện chung".

```
Tôi đính kèm repo skelty-poc, PoC thu nhỏ của kiến trúc SkeltyMLOps. Repo có 4 phần do agent viết: serving/ (API FastAPI), monitoring/ (phát hiện drift, tạo issue), orchestrator/ (đọc issue, chạy Argo), scenario/ (kịch bản end-to-end). Hãy review chéo. Chỉ báo cáo, không sửa code.

Giao diện các phần phải tuân thủ: Service skelty-serving, port 8000, namespace argo; endpoint GET /health, GET /model, POST /predict với {"features": {tên: giá trị}}, POST /reload, GET /stats trả {"n": số mẫu, "features": {tên: {"mean": .., "std": ..}}}, GET /metrics. Ticket là GitHub Issue label "retrain", tiêu đề bắt đầu bằng "[drift]", thân có JSON {"type": "drift", "model_version": "..", "drifted_features": [..], "detected_at": ".."}; orchestrator dùng label "in-progress" và "done". Argo WorkflowTemplate "skelty-training-pipeline" trong namespace argo, tham số run-id, shift, image; run-id = "issue-<số issue>". Drift khi ít nhất 3 feature có chênh lệch mean chia std tham chiếu lớn hơn 1,0 và n >= 100. Cấu hình qua GITHUB_TOKEN (Secret skelty-github), GITHUB_REPO, SERVING_URL, ARTIFACT_ROOT.

Kiểm tra:
1. Mỗi phần có tuân thủ giao diện không: tên Service và port, endpoint, định dạng JSON, label, run-id, tham số WorkflowTemplate, biến môi trường. Liệt kê chỗ lệch kèm file và dòng.
2. Chạy toàn bộ pytest của từng thư mục và báo kết quả thật (số pass, số fail). Nếu không chạy được thì nêu lý do.
3. Rà manifest K8s: namespace, cách mount PVC (ReadWriteOnce thì các pod phải cùng node), Secret, RBAC quyền tối thiểu, probe. Chỉ ra manifest sai cú pháp hoặc thiếu.
4. Rà bảo mật cơ bản: token không nằm trong code hay log; khả năng vòng lặp tạo issue vô hạn; orchestrator có idempotent khi restart không.
5. Rà README: các lệnh có khớp với code không.

Kết quả: bảng lỗi theo mức (chặn chạy, nên sửa, nhỏ), mỗi lỗi có file, dòng, mô tả và cách sửa ngắn. Điều gì chưa chạy thử thì ghi "chưa kiểm chứng", không khẳng định.
```

Gửi bảng lỗi cho Quochuy để sửa; sau khi sửa, chạy lại prompt này một lần nữa.

## Phần 8: tích hợp vào báo cáo chính (Người C)

Đính kèm file `.tex` báo cáo chính, `scoring_section.tex` và `poc_section.tex` (cả hai do Người A viết). Làm được ngay để ghép và biên dịch; điền kết quả chờ log thật từ Quochuy ở cuối.

```
Tôi đính kèm báo cáo nhóm dạng .tex (phân tích paper SkeltyMLOps, Daoud và cộng sự, 2025) cùng hai file mới: scoring_section.tex (chấm điểm 4 kiến trúc) và poc_section.tex (phần PoC).

Nhiệm vụ:
1. Chèn hai file vào báo cáo chính bằng \input ở vị trí hợp lý. Không sửa các section khác, chỉ được thêm vào chỗ chèn và danh sách tài liệu tham khảo.
2. Biên dịch bằng engine phù hợp với preamble hiện có. Sửa lỗi biên dịch sinh ra từ hai file mới. Nếu lỗi nằm ở phần cũ thì báo, không tự sửa.
3. Kiểm tra: \ref, \cite, hình, bảng, gói LaTeX còn thiếu, tiếng Việt hiển thị đúng, bảng không tràn lề.
4. Liệt kê mọi chỗ còn placeholder "CHƯA CÓ KẾT QUẢ THẬT" kèm số dòng.
5. Khi tôi đính kèm scenario/logs/*.md: điền bảng kết quả từ log. Mỗi con số phải truy được về một dòng log và ghi tên file log trong chú thích bảng. Tuyệt đối không điền số không có trong log; bước nào "không đạt" thì ghi "không đạt".

Kết quả: file .tex đã cập nhật, PDF biên dịch được, danh sách việc còn lại. Chỉ báo những gì đã biên dịch thật.
```

## Phần 9: việc trên cluster (Quochuy)

Quochuy làm các bước dưới đây, theo thứ tự: tạo repo GitHub trước, rồi tới homelab. Mỗi bước dùng file do người khác viết nên chỉ làm khi file đó đã xong. Nếu lỗi, gửi log cho người viết phần đó sửa, không tự sửa code.

- [ ] Tạo repo GitHub (làm đầu tiên, các phần khác cần tên repo) bằng các lệnh bên dưới, đẩy bản `skelty-poc` lên, rồi mời 4 người còn lại làm collaborator.
- [ ] Tạo fine-grained token chỉ cho repo này, quyền đọc và ghi Issues. Giữ riêng, không dán vào chat nhóm và không commit.
- [ ] Gửi tên repo (dạng `owner/repo`) cho cả nhóm để họ ghi vào cấu hình và README.
- [ ] Kiểm tra môi trường rồi báo cho Người B và Người D: Argo Workflows đã cài trong namespace `argo` chưa, storage class cho PVC, Prometheus thu metric bằng annotation hay ServiceMonitor, có Pushgateway không. Họ cần câu trả lời này trước khi chạy prompt Phần 2 và 3.
- [ ] Chạy pipeline huấn luyện có sẵn trong repo (lệnh bên dưới).
- [ ] Tạo Secret `skelty-github` bằng token ở bước trên.
- [ ] Deploy API (Phần 2): `kubectl apply -f k8s/serving.yaml`, thử `/health` và `/model` bằng curl hoặc port-forward.
- [ ] Deploy CronJob drift (Phần 3): apply `k8s/drift-cronjob.yaml`, chạy tay một lần để thử.
- [ ] Deploy orchestrator (Phần 4): apply `k8s/orchestrator.yaml`, đặt `DEFAULT_SHIFT=1.5`, xem log.
- [ ] Chạy script kịch bản (Phần 5) và giữ lại thư mục `scenario/logs/`.
- [ ] Chụp bằng chứng cho báo cáo: Argo UI, issue GitHub, Grafana hoặc `/metrics`.
- [ ] Gửi log và ảnh cho Người C (Phần 8).

```
gh repo create <tên-repo> --private
gh label create retrain --repo <owner>/<tên-repo>
gh label create in-progress --repo <owner>/<tên-repo>
gh label create done --repo <owner>/<tên-repo>
```

Sau đó đẩy code `skelty-poc` lên repo và mời collaborator (GitHub: Settings, Collaborators).

```
docker build -t skelty-poc:0.1 .
kubectl apply -f k8s/pvc.yaml -f k8s/workflow-template.yaml
argo submit -n argo --from workflowtemplate/skelty-training-pipeline -p run-id=baseline-001 --watch

kubectl -n argo create secret generic skelty-github --from-literal=GITHUB_TOKEN=<token> --from-literal=GITHUB_REPO=<owner>/<repo>
```

Đưa image vào cluster theo cách homelab đang dùng (registry riêng hoặc import vào node). Lệnh build image của Phần 2 đến 4 nằm trong README của từng phần. Token không dán vào chat hay commit. PVC là ReadWriteOnce nên các pod dùng chung phải nằm cùng một node; pod bị Pending vì volume thì kiểm tra điều này trước.

## Việc làm tay, không cần prompt

Những việc dưới đây cần người thật làm, vì cần tài khoản GitHub hoặc cần nhóm quyết định.

**Trước khi phát prompt**

- [ ] Cả nhóm chốt bảng "Giao diện chung" và phân người cho 8 phần.
- [ ] Nhắn nhóm và hỏi giảng viên: hai phần mới nằm ở section nào, hạn nộp thật, đề có yêu cầu thực nghiệm không.
- [ ] Quochuy tạo repo GitHub chứa ticket, ba label `retrain`, `in-progress`, `done`, và token có quyền đọc ghi Issues, rồi gửi tên repo cho nhóm.
- [ ] Giải nén repo `skelty-poc` đã gửi để cả nhóm dùng chung, mỗi phần code nằm ở thư mục riêng (`serving/`, `monitoring/`, `orchestrator/`, `scenario/`) và file `k8s/` của mình.

**Sau mỗi prompt**

- [ ] Tự chạy lại test của phần đó trên máy mình, không chỉ tin lời báo cáo của AI.
- [ ] Với Phần 1 (Người A trích, Người D đối chiếu): đối chiếu từng câu trích dẫn với paper gốc, vì AI có thể trích sai.
- [ ] Kiểm tra README có bị ghi đè không, vì mỗi prompt đều cập nhật README.
