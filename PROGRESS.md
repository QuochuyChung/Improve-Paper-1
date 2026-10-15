# Tiến độ PoC SkeltyMLOps

Cập nhật lần cuối: 2026-10-15 (Quochuy, Phần 9). Chi tiết phân việc xem [task.md](task.md).

Repo: `QuochuyChung/Improve-Paper-1`. Nhiều khả năng đã private (clone từ `.24` bị đòi mật khẩu; Quochuy xác nhận lại trên GitHub Settings). Mọi người đã được mời làm collaborator.

Ký hiệu: ✅ xong và đã kiểm chứng · 🟡 đã chuẩn bị nhưng chưa chạy hoặc làm dở · ⏳ đang chờ · ⬜ chưa làm

## Tóm tắt (2026-10-15)

Vòng retrain **nửa sau đã chạy thật trên cụm**: Issue (tạo tay) → orchestrator → Argo Workflow → pipeline ghi model lên NFS → `/reload` API → comment, gắn `done`, đóng Issue. Đã chạy 2 lần (Issue `#3`, `#4`), cả hai `Succeeded`. **Nửa trước chưa có**: không có drift monitor (Người D) nên Issue vẫn do người tạo tay. Kịch bản 5 bước của B chưa chạy.

| Khâu | Trạng thái |
| --- | --- |
| 1. Pipeline huấn luyện (Argo) | ✅ chạy thật 3 lần |
| 2. API serving | ✅ deploy, đã thử `/health`, `/model`, `/predict`, `/stats`, `/reload` (qua orchestrator) |
| 3. Drift monitor (Người D) | ❌ chưa có code trên `main` |
| 4. Orchestrator | ✅ deploy, đã xử lý thật 2 Issue |
| Kịch bản end-to-end (B) | ⏳ chưa chạy, bước 3 và 4 cần drift monitor |

## Tổng quan theo phần

| Phần | Việc | Người | Trạng thái | Ghi chú |
| --- | --- | --- | --- | --- |
| 1 | Chấm điểm 4 kiến trúc | Người A | ⬜ | Chưa có `scoring_section.tex` trong repo |
| 2 | FastAPI serving | Người B | ✅ | Code B, Quochuy đã build image và deploy. Test pytest của B chưa chạy. ServiceMonitor của B thiếu label `release: huydevops`, đã sửa trong repo (báo B) |
| 3 | Monitoring, drift, tạo ticket | Người D | ⬜ | Chưa thấy `monitoring/` hay `k8s/drift-cronjob.yaml`. Pushgateway đã sẵn sàng trên cụm (mục 6c) |
| 4 | Orchestrator | Người C | ✅ | Code C, Quochuy đã build image và deploy, đã xử lý Issue `#3`, `#4`. Test pytest của C chưa chạy. Còn nên sửa nhỏ: thêm `serviceAccountName`, thử lại khi mất kết nối GitHub (xem "Việc cho từng người") |
| 5 | Script kịch bản end-to-end | Người B | 🟡 | Có `scenario/run_scenario.py`, chưa chạy thật |
| 6 | Viết phần PoC trong báo cáo | Người A | ⬜ | Chưa thấy `poc_section.tex` |
| 7 | Review chéo | Người D | ⬜ | Làm sau khi Phần 2 đến 5 có code (còn thiếu Phần 3) |
| 8 | Tích hợp báo cáo | Người C | 🟡 | Bị chặn, xem `report/INTEGRATION_STATUS.md`: thiếu source LaTeX báo cáo, `scoring_section.tex`, `poc_section.tex` |
| 9 | Việc trên cluster | Quochuy | 🟡 | Xem bảng chi tiết dưới |

## Phần 9 (Quochuy) chi tiết

| # | Việc | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| 1 | Tạo repo GitHub | ✅ | `QuochuyChung/Improve-Paper-1` |
| 2 | Mời 4 người làm collaborator | ✅ | Quochuy xác nhận đã mời |
| 3 | Tạo 3 label `retrain`, `in-progress`, `done` | ✅ | Đã thấy cả 3 label được orchestrator dùng trên Issue `#3` |
| 4 | Fine-grained token (chỉ repo này, Issues read/write) | ✅ | `curl` tới `api.github.com/repos/QuochuyChung/Improve-Paper-1/issues` trả `200`; orchestrator ghi được label, comment và đóng Issue. KHÔNG dán token vào chat, KHÔNG commit |
| 5 | Gửi tên repo cho nhóm | ✅ | `QuochuyChung/Improve-Paper-1` |
| 6 | Kiểm tra môi trường homelab | ✅ | Kết quả ở mục "Kết quả kiểm tra môi trường" |
| 6a | Cài Argo Workflows (namespace `argo`) bằng helm | ✅ | Release `argo-workflows` (chart 2.0.12, app v4.1.5), 2 pod `Running`. Argo UI mở được qua `port-forward` + đường hầm SSH |
| 6b | PV NFS cho PVC `skelty-artifacts` | ✅ | `skelty-artifacts-pv`, 2Gi, RWO, `Retain`, `nfs-storage`, NFS `192.168.58.24:/data/skelty-artifacts`. Đã Bound với PVC. Manifest: `k8s/pv-skelty-artifacts.yaml` |
| 6c | Cài Pushgateway | ✅ | Release `prometheus-pushgateway` trong `monitoring-namespace`, pod `Running`, Service `prometheus-pushgateway:9091`, ServiceMonitor có label `release=huydevops`. Chưa gọi thử, chưa kiểm tra Prometheus kéo được target |
| 6d | Điều tra API server chậm trên `kubernetes1` | 🟡 | Chưa tìm ra nguyên nhân gốc, xem mục "Sự cố API server". Chưa ghi RSS trong lúc chạy pipeline |
| 6e | Đổi repo sang private | 🟡 | Suy ra đã private, chưa xác nhận trên Settings |
| 6f | Cài CLI `argo` v4.1.5 trên `kubernetes1` | ✅ | `argo version` khớp server |
| 6g | ServiceAccount `argo-workflow` trong `argo` | ✅ | Đã tạo. WorkflowTemplate dùng SA này (đã thấy `ServiceAccount: argo-workflow` trong Workflow) |
| 6h | RoleBinding `default-workflowtaskresults` | ✅ | Gán quyền `workflowtaskresults` cho SA `default` phòng khi Workflow không đặt SA |
| 7 | Viết lại bản `skelty-poc` gốc (không ai có bản gốc, B dùng pipeline giả) | ✅ | `pipeline/`, `Dockerfile`, `k8s/pvc.yaml`, `k8s/workflow-template.yaml`, đã commit. 16/16 pytest đạt (Python 3.12, scikit-learn 1.9.1) |
| 8 | Build image `skelty-poc:0.1`, apply PVC + WorkflowTemplate, chạy `baseline-001` | ✅ | Build trên `deploy-server` (46 phút, `pip install` chậm), image 447 MB import cả 3 node. Workflow `Succeeded` 3/3 trong 1 phút 52 giây. NFS có `models/baseline-001`, `LATEST` = `baseline-001`, accuracy 0,915, f1 0,9163 |
| 9 | Tạo Secret `skelty-github` | ✅ | Có đủ hai khóa `GITHUB_TOKEN`, `GITHUB_REPO` |
| 10 | Deploy API (`k8s/serving.yaml`) | ✅ | Image `skelty-serving:0.1` (488 MB, build 77 giây) import 3 node. Đã kiểm chứng: `/health` ok, `/model` đúng `baseline-001`, `/predict` trả dự đoán, `/stats` trả `n:1` sau 1 request. Sau retrain: `/model` báo `issue-3`, `/stats` trả `n:0` (cửa sổ xóa khi reload). Chưa kiểm chứng `/metrics` và việc Prometheus thu |
| 11 | Deploy CronJob drift | ⏳ | Chờ Người D (Phần 3) |
| 12 | Deploy orchestrator, `DEFAULT_SHIFT=1.5` | ✅ | Image `skelty-orchestrator:0.1`. Lần đầu `ImagePullBackOff` vì `kubernetes3` chưa import image, đã sửa. Pod `Running 1/1` trên `kubernetes3`. Xem mục "Kết quả chạy thử orchestrator" |
| 13 | Chạy script kịch bản, giữ `scenario/logs/` | ⏳ | Chờ drift monitor (bước 3 và 4 của kịch bản) |
| 14 | Chụp bằng chứng (Argo UI, issue, Grafana hoặc `/metrics`) | 🟡 | Đã có `evidence/` (5 ảnh Argo UI). Còn thiếu trang Issue `#4` sau khi đóng, `curl /model` sau retrain, Grafana hoặc `/metrics` |
| 15 | Gửi log + ảnh cho Người C | ⬜ | |

## Kết quả chạy thử orchestrator (Issue tạo tay, 2026-10-15)

| Issue | Thân Issue | Workflow | Kết quả đã quan sát |
| --- | --- | --- | --- |
| `#3` | `shift` không ghi (dùng `DEFAULT_SHIFT=1.5`) | `retrain-issue-3` | `Succeeded` 1 phút 1 giây. Orchestrator gắn `in-progress`, chạy, gọi `/reload` (comment ghi `model_version sau reload: issue-3`), comment accuracy 0,915 f1 0,9163, gắn `done`, đóng Issue. API sau đó báo `issue-3` |
| `#4` | `"shift": 2.0` | `retrain-issue-4` | `Succeeded` 1 phút 21 giây. Log `acquire` ghi `shift=2.0`, tức orchestrator đọc đúng trường `shift` từ Issue. `train` ghi `accuracy=0.9150 f1=0.9163` |

Chưa quan sát cho `#4`: trang Issue sau khi đóng và `/model` báo `issue-4`.

Log orchestrator có 4 lần `Polling iteration failed` (10:32, 10:37, 10:40, 10:47 UTC): gọi GitHub bị ngắt kết nối (`RemoteDisconnected`), vòng lặp tự hồi phục, không ảnh hưởng kết quả. Nguyên nhân chưa xác định.

Bằng chứng: thư mục `evidence/` (Argo UI: danh sách workflow, sơ đồ `retrain-issue-4`, log từng bước).

## Thông tin môi trường đã biết

- Cụm K8s v1.30.14, containerd: `kubernetes1` control plane (chạy `kubectl` ở đây), `kubernetes2` và `kubernetes3` worker. Node `kubernetes1` chỉ có 3,8 GiB RAM, 3 nhân CPU, không swap.
- Có hai hệ NFS (cụm không có provisioner động, mọi PV tạo tay, reclaim `Retain`):
  - `nfs-storage` -> `deploy-server` `192.168.58.24`, export `/data` (`rw,sync,no_subtree_check,no_root_squash`, thư mục `/data` mode 777). Dùng cho uptime-kuma, Prometheus, maria, blog, và `skelty-artifacts`.
  - `nfs-storage-data-cluster` -> VIP `192.168.58.110` (cụm data, keepalived trên `data1`). Dùng cho mysql, postgres, mssql, vault, keycloak. Chưa kiểm tra cấu hình Ganesha.
- Phải bật `deploy-server` (`.24`) và cụm `data1/2/3` thì pod mới mount được volume.
- Không dùng registry. Cách đưa image vào cụm: build trên `deploy-server` (`.24`, có Docker), `docker save` ra `.tar`, `scp` sang từng node rồi `sudo ctr -n k8s.io images import`. Image phải có trên **cả 3 node** vì pod có thể rơi vào node nào cũng được (thiếu thì `ImagePullBackOff`). Harbor có trong homelab nhưng chưa dùng.
- Prometheus: kube-prometheus-stack, release `huydevops`, namespace `monitoring-namespace`. ServiceMonitor phải có label `release: huydevops` (quét mọi namespace).
- Cụm có sẵn Argo CD (khác Argo Workflows) và Rancher (UI báo cluster `huydevops` "agent is not connected").
- PVC `skelty-artifacts` là ReadWriteOnce, backend NFS. Pipeline, serving và orchestrator đã chạy trên các node khác nhau mà không lỗi mount (orchestrator ở `kubernetes3`; node của pod serving và pod pipeline chưa ghi lại).
- Argo UI không đòi đăng nhập (`server.authModes={server}`), chỉ mở qua `port-forward`, không đưa ra ngoài mạng.

## Kết quả kiểm tra môi trường

| Câu hỏi | Trả lời | Người cần biết |
| --- | --- | --- |
| Argo Workflows đã cài chưa? | **Đã cài**, namespace `argo`. CLI `argo` v4.1.5 trên `kubernetes1` | B, C, D |
| StorageClass cho PVC? | `nfs-storage` (trỏ vào `.24`). PV `skelty-artifacts-pv` đã tạo, PVC đã Bound | B |
| Prometheus thu bằng annotation hay ServiceMonitor? | **ServiceMonitor** (Prometheus Operator) với label `release: huydevops` | B |
| Có Pushgateway không? | **Có.** URL trong cụm: `http://prometheus-pushgateway.monitoring-namespace:9091` (suy từ tên Service, chưa gọi thử) | D |
| ServiceAccount cho workflow? | `argo-workflow` (namespace `argo`) | B, C |
| Cách đưa image vào cluster? | Build trên `.24`, `ctr images import` vào cả 3 node (xem trên) | B, C, D |

## Sự cố API server trên `kubernetes1` (mục 6d)

- Hiện tượng (2026-10-13): `kubectl` và `helm` báo `TLS handshake timeout`, `/readyz` chập chờn 9 đến 22 giây, etcd lúc ok lúc fail, API server restart 47 lần, etcd 34 lần.
- Nguyên nhân gần nhất đã xác định: `kube-apiserver` chiếm 2,3 đến 2,47 GB RAM trên node 3,8 GB, load average 63, node thrashing. Không phải pod của project khác. Số object trong etcd nhỏ (cao nhất 116 object/resource, cả cụm chừng 1.000). Có 107 CRD.
- Đợt vọt RAM sau reboot ngày 2026-10-13 trùng với lúc cài Argo Workflows và Pushgateway. Reboot lần sau, không cài thêm gì, RSS chỉ 1,56 GB, available 1,1 GB. Nghi CRD lớn của Argo góp phần (chưa kiểm chứng).
- Chưa xác định: hai tiến trình `agent` (khoảng 120 đến 130 MB) trên `kubernetes1`. Nghi `cattle-cluster-agent` của Rancher, giả thuyết yếu đi nhưng chưa loại.
- Từ 2026-10-14 đến 15 chạy pipeline, serving và orchestrator mà không thấy lại lỗi timeout, nhưng chưa ghi lại RSS trong lúc chạy.
- Theo dõi: `watch -n5 'ps -o rss=,comm= -C kube-apiserver; free -m | sed -n 2p'`

## Việc đang chặn

1. **Người D chưa có code monitoring** (`monitoring/`, `k8s/drift-cronjob.yaml`, image `skelty-monitor:0.1`). Không có nó thì không tự tạo được Issue `[drift]`, nên vòng drift → retrain không tự chạy và kịch bản 5 bước không chạy hết.
2. **Source LaTeX báo cáo chính, `scoring_section.tex`, `poc_section.tex` chưa có** (Người A, C).
3. Chưa kiểm chứng Prometheus thu được `/metrics` của API (cần apply `k8s/servicemonitor.yaml` đã có label, rồi xem Targets). Cần cho ảnh Grafana.
4. Chưa xác nhận repo đã private.

## Việc cho từng người

- **Người B:** `k8s/servicemonitor.yaml` thiếu label `release: huydevops` (đã sửa trong repo, đừng ghi đè). `serving/tests` có thể dùng pipeline thật (`pipeline/`) thay `fake_pipeline.py`. Chạy kịch bản khi D xong.
- **Người C:** thêm `"serviceAccountName": "argo-workflow"` vào spec Workflow trong `orchestrator/argo_client.py` (hiện dựa vào WorkflowTemplate và RoleBinding cho `default`). Cân nhắc thử lại khi gọi GitHub bị ngắt kết nối (4 lần `RemoteDisconnected` trong khoảng 30 phút, ưu tiên thấp).
- **Người D:** dùng Pushgateway ở URL trên; image `skelty-monitor:0.1`; Secret `skelty-github` đã có; PVC `skelty-artifacts` để đọc `reference_stats.json`.
- **Người A:** hai file `.tex` còn trống.

## Ghi chú cho báo cáo

- `accuracy` và `f1` của `baseline-001`, `issue-3`, `issue-4` **giống hệt nhau** (0,915 và 0,9163) dù `shift` khác. Do cách sinh dữ liệu (cùng seed 42, dịch cả khối nên bài toán tịnh tiến, chỉ ranh giới quyết định và `reference_stats.json` đổi). Đừng dùng "accuracy thay đổi" để chứng minh retrain; bằng chứng đúng là `run-id` mới, `shift` ghi trong log `acquire`, và việc hết drift sau `/reload`.
- Đã kiểm chứng cục bộ (máy Windows): dữ liệu gốc 0 feature vượt 1,0 std; dữ liệu dịch 1,5 std làm cả 6 feature vượt; sau `/reload` sang model retrain 0 feature vượt. Chưa kiểm chứng trên cụm vì cần drift monitor.
- Hạn chế nên ghi: PoC chỉ phát hiện drift của dữ liệu đầu vào (không có nhãn thật để đo accuracy khi chạy); `/stats` giữ 200 request gần nhất trong RAM của pod, mất khi pod khởi động lại; orchestrator tự viết bằng Python (không dùng BPMN như paper); dữ liệu tổng hợp, model đơn giản; storage là file trên NFS thay vì MLflow hay DVC.

## Quy ước cập nhật file này

- Mỗi người tự sửa dòng của phần mình khi có thay đổi, ghi ngày vào "Cập nhật lần cuối".
- Chỉ ghi ✅ khi đã chạy thật. Chưa thử trên cluster hoặc GitHub thật thì ghi 🟡 và nói rõ.
- Token, mật khẩu không được ghi vào file này.
