# Tiến độ PoC SkeltyMLOps

Cập nhật lần cuối: 2026-10-15 (Quochuy). Chi tiết phân việc xem [task.md](task.md).

Repo: `QuochuyChung/Improve-Paper-1`. Nhiều khả năng đã private (clone từ `.24` bị đòi mật khẩu; Quochuy xác nhận lại trên GitHub Settings). Mọi người đã được mời làm collaborator.

Ký hiệu: ✅ xong và đã kiểm chứng · 🟡 đã chuẩn bị nhưng chưa chạy hoặc làm dở · ⏳ đang chờ · ⬜ chưa làm

## Tóm tắt (2026-10-15)

**Toàn bộ vòng phản hồi đã chạy thông trên cụm thật, không có bước tạo tay**: dữ liệu lệch gửi vào `/predict` → `/stats` → CronJob phát hiện drift và tự tạo Issue → orchestrator bắt Issue → Argo chạy pipeline → model mới ghi lên NFS → `/reload` → đóng Issue → hết drift với model mới. Kịch bản end-to-end của B chạy đủ 5 bước, cả 5 đạt (log: `scenario/logs/20261015T121211Z.md`).

| Khâu | Trạng thái |
| --- | --- |
| 1. Pipeline huấn luyện (Argo) | ✅ chạy thật |
| 2. API serving | ✅ deploy, đã dùng đủ `/health`, `/model`, `/predict`, `/stats`, `/reload` |
| 3. Drift monitor | ✅ viết bởi Quochuy thay Người D (Jira `SWD391-14`), deploy CronJob, đã tự tạo Issue `#5`, `#7` |
| 4. Orchestrator | ✅ deploy, đã xử lý Issue `#3` đến `#7` |
| Kịch bản end-to-end (B) | ✅ chạy 1 lần, 5/5 bước đạt |
| Báo cáo (A, C) | ⬜ chưa có `scoring_section.tex`, `poc_section.tex`, source LaTeX |

Test (chạy trên máy Windows của Quochuy, Python 3.12.8, mỗi thư mục chạy riêng, 2026-10-15): `pipeline/tests` 16, `monitoring/tests` 24, `serving/tests` 10, `orchestrator/tests` 12, `scenario/tests` 6, **tổng 68 đạt**.

## Trạng thái tổng thể (ghi nhận 2026-10-15)

**Phần PoC kỹ thuật đã xong và chạy thật** (Phần 2, 3, 4, 5, 9). **Dự án chưa xong**, vì báo cáo, là sản phẩm nộp, chưa có phần nào viết từ kết quả này.

| Còn thiếu | Ai | Ghi chú |
| --- | --- | --- |
| `scoring_section.tex` (Phần 1) | Người A | Chưa có file |
| `poc_section.tex` (Phần 6) | Người A | Chưa có file. Dùng log `scenario/logs/20261015T121211Z.md` và ảnh `evidence/` để điền kết quả |
| Review chéo code (Phần 7) | Người D | Chưa bắt đầu. Code Phần 2 đến 5 đã có và đã chạy thật |
| Tích hợp vào báo cáo chính (Phần 8) | Người C | Bị chặn: thiếu source LaTeX báo cáo và hai file `.tex` ở trên |

Việc còn lại của Quochuy, theo thứ tự:

1. **Commit và push** `monitoring/`, `k8s/drift-cronjob.yaml`, `grafana/`, `scenario/` (log và hai sửa bảng mã), `evidence/` (đổi tên, thêm `14` đến `17`), `PROGRESS.md`. Tại thời điểm ghi, các file này mới nằm trên máy Quochuy, chưa xác nhận đã lên GitHub.
2. Xác nhận repo đã private trên GitHub Settings.
3. Cập nhật Jira `SWD391-14` và nhắn nhóm (Người D review monitor; Người C điền báo cáo từ log; Người B giữ hai sửa nhỏ trong `scenario/`; Người A hai file `.tex`).
4. Tùy chọn: tắt `port-forward` chạy nền trên `kubernetes1`, tạm dừng CronJob `skelty-drift-check` nếu không còn demo (`kubectl -n argo patch cronjob skelty-drift-check -p '{"spec":{"suspend":true}}'`).

Chưa kiểm chứng hoặc là hạn chế đã biết khi nộp: nguyên nhân gốc sự cố API server hết RAM (mục 6d, không thấy lại trong lần chạy cuối nhưng chưa ghi RSS lúc chạy); test của B và C mới chạy bằng đồ giả trên máy Windows (kịch bản đã chứng minh trên cụm thật); dữ liệu tổng hợp và accuracy không đổi giữa các lần retrain, nên báo cáo dùng "hết drift" làm bằng chứng. Các hạn chế khác xem mục "Ghi chú cho báo cáo".

## Tổng quan theo phần

| Phần | Việc | Người | Trạng thái | Ghi chú |
| --- | --- | --- | --- | --- |
| 1 | Chấm điểm 4 kiến trúc | Người A | ⬜ | Chưa có `scoring_section.tex` trong repo |
| 2 | FastAPI serving | Người B | ✅ | Code B, Quochuy build image và deploy. 10 pytest đạt. `k8s/servicemonitor.yaml` của B thiếu label `release: huydevops`, đã sửa |
| 3 | Monitoring, drift, tạo ticket | Người D | ✅ | **Do Quochuy làm thay** (Jira `SWD391-14` đang gán cho `lt2727714`): `monitoring/`, `k8s/drift-cronjob.yaml`. 24 pytest đạt, đã deploy và chạy thật. Người D cần review và cập nhật Jira |
| 4 | Orchestrator | Người C | ✅ | Code C, Quochuy build image và deploy. 12 pytest đạt. Còn nên sửa nhỏ (xem "Việc cho từng người") |
| 5 | Script kịch bản end-to-end | Người B | ✅ | Chạy thật 1 lần trên `kubernetes1`, 5/5 đạt. 6 pytest đạt sau khi sửa bảng mã (xem "Việc cho từng người") |
| 6 | Viết phần PoC trong báo cáo | Người A | ⬜ | Chưa thấy `poc_section.tex` |
| 7 | Review chéo | Người D | ⬜ | Code Phần 2 đến 5 đã có và đã chạy thật, có thể bắt đầu |
| 8 | Tích hợp báo cáo | Người C | 🟡 | Bị chặn, xem `report/INTEGRATION_STATUS.md`: thiếu source LaTeX, hai file section. Đã có log kịch bản để điền bảng kết quả |
| 9 | Việc trên cluster | Quochuy | 🟡 | Xem bảng chi tiết dưới |

## Phần 9 (Quochuy) chi tiết

| # | Việc | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| 1 | Tạo repo GitHub | ✅ | `QuochuyChung/Improve-Paper-1` |
| 2 | Mời 4 người làm collaborator | ✅ | Quochuy xác nhận đã mời |
| 3 | Tạo 3 label `retrain`, `in-progress`, `done` | ✅ | Cả 3 label được dùng trên Issue `#3` đến `#7` |
| 4 | Fine-grained token (chỉ repo này, Issues read/write) | ✅ | `curl` trả `200`; orchestrator và monitor ghi được Issue (tạo, gắn label, comment, đóng). KHÔNG dán token vào chat, KHÔNG commit |
| 5 | Gửi tên repo cho nhóm | ✅ | `QuochuyChung/Improve-Paper-1` |
| 6 | Kiểm tra môi trường homelab | ✅ | Kết quả ở mục "Kết quả kiểm tra môi trường" |
| 6a | Cài Argo Workflows (namespace `argo`) bằng helm | ✅ | Release `argo-workflows` (chart 2.0.12, app v4.1.5). Argo UI mở được qua `port-forward` + đường hầm SSH |
| 6b | PV NFS cho PVC `skelty-artifacts` | ✅ | `skelty-artifacts-pv`, 2Gi, RWO, `Retain`, `nfs-storage`, NFS `192.168.58.24:/data/skelty-artifacts`. Manifest: `k8s/pv-skelty-artifacts.yaml` |
| 6c | Cài Pushgateway | ✅ | Release `prometheus-pushgateway` trong `monitoring-namespace`, Service `prometheus-pushgateway:9091`, ServiceMonitor có label `release=huydevops`. **Đã kiểm chứng**: Pushgateway nhận metric của CronJob (`drift_detected`, `drifted_feature_count`, `max_feature_zscore`, nhãn `job="skelty_drift_check"`) và Prometheus kéo được chúng (truy vấn `drift_detected` qua API Prometheus trả dữ liệu) |
| 6i | Prometheus và Grafana | ✅ | ServiceMonitor `skelty-serving` (namespace `argo`) và `prometheus-pushgateway` đều có `release=huydevops`. Truy vấn API Prometheus thấy `predictions_total` (job `skelty-serving`) và `drift_detected` (job `skelty_drift_check`). Dashboard `grafana/skelty-dashboard.json` đã nhập vào Grafana của cụm, 8 ô, hiển thị đúng: model `issue-7`, 801 dự đoán, hai đợt drift (z lớn nhất khoảng 2,1 và 1,6, 6 feature lệch) rồi hạ về gần 0. Ảnh: `evidence/16`, `17` |
| 6d | Điều tra API server chậm trên `kubernetes1` | 🟡 | Chưa tìm ra nguyên nhân gốc, xem mục "Sự cố API server" |
| 6e | Đổi repo sang private | 🟡 | Suy ra đã private, chưa xác nhận trên Settings |
| 6f | Cài CLI `argo` v4.1.5 trên `kubernetes1` | ✅ | `argo version` khớp server |
| 6g | ServiceAccount `argo-workflow` trong `argo` | ✅ | Workflow chạy bằng SA này (lấy từ WorkflowTemplate) |
| 6h | RoleBinding `default-workflowtaskresults` | ✅ | Phòng khi Workflow không đặt SA |
| 7 | Viết lại bản `skelty-poc` gốc | ✅ | `pipeline/`, `Dockerfile`, `k8s/pvc.yaml`, `k8s/workflow-template.yaml`. 16 pytest đạt |
| 8 | Build image `skelty-poc:0.1`, chạy `baseline-001` | ✅ | Build trên `deploy-server`, import 3 node. Workflow `Succeeded` 3/3. `models/baseline-001` có trên NFS, accuracy 0,915, f1 0,9163 |
| 9 | Tạo Secret `skelty-github` | ✅ | Có đủ hai khóa `GITHUB_TOKEN`, `GITHUB_REPO` |
| 10 | Deploy API (`k8s/serving.yaml`) | ✅ | Image `skelty-serving:0.1`. Đã dùng `/health`, `/model`, `/predict`, `/stats`, `/reload`. `/metrics` đã được Prometheus thu (mục 6i) |
| 11 | Deploy CronJob drift (`k8s/drift-cronjob.yaml`) | ✅ | Image `skelty-monitor:0.1`, chạy mỗi 5 phút. Lần chạy tay đầu (`n=0`) báo không drift và đẩy metric. Sau khi gửi dữ liệu lệch, tự tạo Issue `#5` và `#7` |
| 12 | Deploy orchestrator, `DEFAULT_SHIFT=1.5` | ✅ | Image `skelty-orchestrator:0.1`. Lần đầu `ImagePullBackOff` vì `kubernetes3` chưa import image, đã sửa |
| 13 | Chạy script kịch bản, giữ `scenario/logs/` | ✅ | `scenario/logs/20261015T121211Z.md`, 5/5 đạt (xem mục "Kết quả kịch bản") |
| 14 | Chụp bằng chứng | ✅ | `evidence/` có 17 ảnh `01` đến `17`: Argo UI (danh sách, sơ đồ, log từng bước), trang Issue `#4`, `#7`, danh sách Issue đã đóng, log pod CronJob tạo Issue `#7`, dashboard Grafana (khung 6 giờ và khung 5 phút). Không có ảnh riêng cho `curl /model` báo `issue-7` (trạng thái này có trong log kịch bản và dashboard) |
| 15 | Gửi log + ảnh cho Người C | ⬜ | Chưa gửi. Cần commit và push `scenario/logs/`, `evidence/` |

## Kết quả kịch bản end-to-end (`scenario/logs/20261015T121211Z.md`)

Chạy trên `kubernetes1`, `N_REQUESTS=200`, `SHIFT=1.5`, bắt đầu 12:06:20Z, kết thúc 12:12:11Z (khoảng 5 phút 51 giây).

| Bước | Kết quả | Số liệu trong log |
| --- | --- | --- |
| 1 | đạt | Workflow `baseline-001` `Succeeded`; `/reload` đổi `issue-6` → `baseline-001` (`changed: True`) |
| 2 | đạt | Gửi 200 request dữ liệu gốc; `n=200`, `z` lớn nhất 0,18 (`f3`), không feature nào lệch |
| 3 | đạt | Gửi 200 request dịch 1,5 std lúc 12:07:53Z; cả 6 feature lệch; Issue `#7` tạo lúc 12:10:34Z (sau 2 phút 41 giây) |
| 4 | đạt | Issue `#7` đóng với label `retrain`, `done` lúc 12:12:01Z (sau 1 phút 27 giây kể từ khi tạo Issue); `/model.run_id=issue-7` |
| 5 | đạt | Gửi lại 200 request dịch 1,5 std; `model=issue-7`, `n=200`, `z` lớn nhất 0,13, không còn drift |

Bằng chứng ảnh: `evidence/08` đến `13`, `15`.

## Các Issue đã tạo (tất cả đã đóng, `Open 0`)

| Issue | Tiêu đề | Do ai tạo | Workflow |
| --- | --- | --- | --- |
| `#3` | `[drift] thử orchestrator` | Quochuy, tay | `retrain-issue-3` |
| `#4` | `[drift] thử Argo UI` (thân có `"shift": 2.0`) | Quochuy, tay | `retrain-issue-4` |
| `#5` | `[drift] issue-4: 6 feature lệch so với tham chiếu` | **Monitor, tự động** (chạy tay `drift-manual2` sau khi gửi dữ liệu lệch) | `retrain-issue-5` |
| `#6` | `[drift] retrain 6` | Quochuy, tay | `retrain-issue-6` |
| `#7` | `[drift] baseline-001: 6 feature lệch so với tham chiếu` | **Monitor, tự động** (CronJob, trong kịch bản) | `retrain-issue-7` |

GitHub hiển thị người tạo và mọi thao tác là `QuochuyChung` cho cả Issue do monitor và orchestrator tạo, vì cả hai gọi API bằng token của Quochuy. Phân biệt tay hay tự động dựa vào tiêu đề và thân Issue (mẫu "phát hiện tự động bởi `skelty-drift-check`", bảng z từng feature) và log pod CronJob (`evidence/12`).

Chi tiết đã quan sát: `retrain-issue-3` `Succeeded` 1 phút 1 giây; `retrain-issue-4` 1 phút 21 giây, log `acquire` ghi `shift=2.0`; `retrain-issue-7` 1 phút 10 giây, log `acquire` ghi `shift=1.5`, `train` ghi `accuracy=0.9150 f1=0.9163`.

Log orchestrator có 4 lần `Polling iteration failed` (10:32, 10:37, 10:40, 10:47 UTC) do gọi GitHub bị ngắt kết nối (`RemoteDisconnected`); vòng lặp tự hồi phục, không ảnh hưởng kết quả. Nguyên nhân chưa xác định.

## Thông tin môi trường đã biết

- Cụm K8s v1.30.14, containerd: `kubernetes1` control plane (chạy `kubectl` ở đây), `kubernetes2` và `kubernetes3` worker. Node `kubernetes1` chỉ có 3,8 GiB RAM, 3 nhân CPU, không swap.
- Có hai hệ NFS (cụm không có provisioner động, mọi PV tạo tay, reclaim `Retain`):
  - `nfs-storage` -> `deploy-server` `192.168.58.24`, export `/data` (`rw,sync,no_subtree_check,no_root_squash`, thư mục `/data` mode 777). Dùng cho uptime-kuma, Prometheus, maria, blog, và `skelty-artifacts`.
  - `nfs-storage-data-cluster` -> VIP `192.168.58.110` (cụm data, keepalived trên `data1`). Dùng cho mysql, postgres, mssql, vault, keycloak. Chưa kiểm tra cấu hình Ganesha.
- Phải bật `deploy-server` (`.24`) và cụm `data1/2/3` thì pod mới mount được volume.
- Không dùng registry. Cách đưa image vào cụm: build trên `deploy-server` (`.24`, có Docker), `docker save` ra `.tar`, `scp` sang từng node rồi `sudo ctr -n k8s.io images import`. Image phải có trên **cả 3 node** vì pod có thể rơi vào node nào cũng được (thiếu thì `ImagePullBackOff`). Harbor có trong homelab nhưng chưa dùng.
- Prometheus: kube-prometheus-stack, release `huydevops`, namespace `monitoring-namespace`. ServiceMonitor phải có label `release: huydevops` (quét mọi namespace).
- Cụm có sẵn Argo CD (khác Argo Workflows) và Rancher (UI báo cluster `huydevops` "agent is not connected").
- PVC `skelty-artifacts` là ReadWriteOnce, backend NFS. Pod pipeline, serving, orchestrator và CronJob đã chạy trên các node khác nhau (CronJob ở `kubernetes2`, orchestrator ở `kubernetes3`) mà không lỗi mount.
- Argo UI không đòi đăng nhập (`server.authModes={server}`), chỉ mở qua `port-forward`, không đưa ra ngoài mạng.
- Kịch bản chạy trên `kubernetes1`: cài `python3-numpy` (1.17.4) và `python3-requests` qua `apt`, Python 3.8 của Ubuntu 20.04.

## Kết quả kiểm tra môi trường

| Câu hỏi | Trả lời | Người cần biết |
| --- | --- | --- |
| Argo Workflows đã cài chưa? | **Đã cài**, namespace `argo`. CLI `argo` v4.1.5 trên `kubernetes1` | B, C, D |
| StorageClass cho PVC? | `nfs-storage` (trỏ vào `.24`). PV `skelty-artifacts-pv`, PVC đã Bound | B |
| Prometheus thu bằng annotation hay ServiceMonitor? | **ServiceMonitor** (Prometheus Operator) với label `release: huydevops` | B |
| Có Pushgateway không? | **Có.** `http://prometheus-pushgateway.monitoring-namespace:9091`; đã nhận metric từ CronJob | D |
| ServiceAccount cho workflow? | `argo-workflow` (namespace `argo`) | B, C |
| Cách đưa image vào cluster? | Build trên `.24`, `ctr images import` vào cả 3 node | B, C, D |

## Sự cố API server trên `kubernetes1` (mục 6d)

- Hiện tượng (2026-10-13): `kubectl` và `helm` báo `TLS handshake timeout`, `/readyz` chập chờn 9 đến 22 giây, etcd lúc ok lúc fail, API server restart 47 lần, etcd 34 lần.
- Nguyên nhân gần nhất đã xác định: `kube-apiserver` chiếm 2,3 đến 2,47 GB RAM trên node 3,8 GB, load average 63, node thrashing. Không phải pod của project khác. Số object trong etcd nhỏ (cao nhất 116 object/resource, cả cụm chừng 1.000). Có 107 CRD.
- Đợt vọt RAM sau reboot ngày 2026-10-13 trùng với lúc cài Argo Workflows và Pushgateway. Reboot lần sau, không cài thêm gì, RSS chỉ 1,56 GB, available 1,1 GB. Nghi CRD lớn của Argo góp phần (chưa kiểm chứng).
- Chưa xác định: hai tiến trình `agent` (khoảng 120 đến 130 MB) trên `kubernetes1`. Nghi `cattle-cluster-agent` của Rancher, giả thuyết yếu đi nhưng chưa loại.
- Từ 2026-10-14 đến 15 chạy pipeline, serving, orchestrator, CronJob và kịch bản mà không thấy lại lỗi timeout, nhưng chưa ghi lại RSS trong lúc chạy.
- Theo dõi: `watch -n5 'ps -o rss=,comm= -C kube-apiserver; free -m | sed -n 2p'`

## Việc đang chặn hoặc còn mở

1. **Báo cáo:** `scoring_section.tex`, `poc_section.tex`, source LaTeX báo cáo chính chưa có (Người A, C). Log kịch bản và ảnh đã có để điền kết quả.
2. **Commit và push** các thứ đang chỉ nằm trên máy Quochuy: `monitoring/`, `k8s/drift-cronjob.yaml`, `grafana/`, `scenario/logs/`, `evidence/` (đổi tên, thêm `14` đến `17`), hai sửa nhỏ trong `scenario/`, `PROGRESS.md`.
3. **Jira:** cập nhật `SWD391-14` (Phần 3) và báo Người D.
4. Chưa xác nhận repo đã private.

## Việc cho từng người

- **Người B:** hai sửa nhỏ do Quochuy thực hiện, đừng ghi đè: (a) `k8s/servicemonitor.yaml` thêm label `release: huydevops`; (b) `scenario/run_scenario.py` dòng 302 và `scenario/tests/test_scenario.py` dòng 97 thêm `encoding="utf-8"` (không có thì test lỗi trên Windows vì không ghi được tiếng Việt vào log, trên Linux không lỗi). Header file log ghi `môi trường: Env` (in tên lớp thay vì mô tả môi trường), nên sửa. `serving/tests` có thể dùng pipeline thật thay `fake_pipeline.py`.
- **Người C:** thêm `"serviceAccountName": "argo-workflow"` vào spec Workflow trong `orchestrator/argo_client.py` (hiện dựa vào WorkflowTemplate và RoleBinding cho `default`). Cân nhắc thử lại khi gọi GitHub bị ngắt kết nối (4 lần `RemoteDisconnected` trong khoảng 30 phút, ưu tiên thấp). Điền bảng kết quả báo cáo từ `scenario/logs/20261015T121211Z.md`.
- **Người D:** review `monitoring/drift_check.py`, `k8s/drift-cronjob.yaml` và 24 test (Quochuy viết thay, task `SWD391-14`), rồi bắt đầu Phần 7 (review chéo). Cập nhật Jira.
- **Người A:** hai file `.tex` còn trống.

## Ghi chú cho báo cáo

- `accuracy` và `f1` của `baseline-001`, `issue-3`, `issue-4`, `issue-7` **giống hệt nhau** (0,915 và 0,9163) dù `shift` khác. Do cách sinh dữ liệu (cùng seed 42, dịch cả khối nên bài toán tịnh tiến, chỉ ranh giới quyết định và `reference_stats.json` đổi). Đừng dùng "accuracy thay đổi" để chứng minh retrain; bằng chứng đúng là `run-id` mới, `shift` ghi trong log `acquire`, và việc hết drift sau `/reload` (bước 5 của kịch bản).
- Thời gian (từ log kịch bản): từ lúc dữ liệu lệch được gửi đến lúc Issue được tạo 2 phút 41 giây (chủ yếu chờ chu kỳ CronJob 5 phút); từ lúc có Issue đến lúc model mới được nạp 1 phút 27 giây. Tổng khoảng 4 phút 8 giây.
- Cửa sổ `/stats` là cửa sổ trượt 200 request, nên drift không báo ngay khi dữ liệu bắt đầu lệch: đo cục bộ (máy Windows, không phải trên cụm), 60 request dịch 1,5 std lẫn 140 request cũ cho `z` chỉ 0,3 đến 0,6, không vượt 1,0. Với dịch 1,5 std cần khoảng trên 134 trong 200 request đã dịch mới vượt ngưỡng.
- Hạn chế nên ghi: PoC chỉ phát hiện drift của dữ liệu đầu vào (không có nhãn thật để đo accuracy khi chạy); `/stats` giữ 200 request gần nhất trong RAM của pod, mất khi pod khởi động lại; mọi thao tác trên GitHub (monitor, orchestrator) chạy bằng token của một tài khoản cá nhân nên không phân biệt được người và máy; orchestrator tự viết bằng Python (không dùng BPMN như paper); dữ liệu tổng hợp, model đơn giản; storage là file trên NFS thay vì MLflow hay DVC; giả lập drift bằng cách dịch phân phối vì không có luồng dữ liệu thật.

## Quy ước cập nhật file này

- Mỗi người tự sửa dòng của phần mình khi có thay đổi, ghi ngày vào "Cập nhật lần cuối".
- Chỉ ghi ✅ khi đã chạy thật. Chưa thử trên cluster hoặc GitHub thật thì ghi 🟡 và nói rõ.
- Token, mật khẩu không được ghi vào file này.
