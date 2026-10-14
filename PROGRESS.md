# Tiến độ PoC SkeltyMLOps

Cập nhật lần cuối: 2026-10-14 (Quochuy, Phần 9). Chi tiết phân việc xem [task.md](task.md).

Repo: `QuochuyChung/Improve-Paper-1`. **Hiện đang Public** (thấy trên GitHub ngày 2026-10-13), task.md yêu cầu private: Quochuy cần đổi sang private. Mọi người đã được mời làm collaborator.

Ký hiệu: ✅ xong và đã kiểm chứng · 🟡 đã chuẩn bị nhưng chưa chạy hoặc làm dở · ⏳ đang chờ · ⬜ chưa làm

## Tổng quan theo phần

| Phần | Việc | Người | Trạng thái | Ghi chú |
| --- | --- | --- | --- | --- |
| 1 | Chấm điểm 4 kiến trúc | Người A | ⬜ | Chưa có `scoring_section.tex` trong repo |
| 2 | FastAPI serving | Người B | 🟡 | Đã có code trên `main` (`serving/`, `k8s/serving.yaml`, `k8s/servicemonitor.yaml`, `scenario/`). Quochuy chưa đọc kỹ hay chạy test |
| 3 | Monitoring, drift, tạo ticket | Người D | ⬜ | Chưa thấy `monitoring/` hay `k8s/drift-cronjob.yaml` trên `main`. Pushgateway đã sẵn sàng trên cụm (xem mục 6c) |
| 4 | Orchestrator | Người C | 🟡 | Đã có code trên `main` (`orchestrator/`, `k8s/orchestrator.yaml`, có test). Workflow do orchestrator tạo chưa đặt `serviceAccountName` ([orchestrator/argo_client.py:57](orchestrator/argo_client.py:57)); tạm xử lý phía cụm bằng RoleBinding cho `default` (mục 6h). Nên thêm `serviceAccountName: argo-workflow` vào code cho rõ ràng |
| 5 | Script kịch bản end-to-end | Người B | 🟡 | Có `scenario/run_scenario.py` trên `main`, chưa chạy thật |
| 6 | Viết phần PoC trong báo cáo | Người A | ⬜ | Chưa thấy `poc_section.tex` |
| 7 | Review chéo | Người D | ⬜ | Làm sau khi Phần 2 đến 5 có code (còn thiếu Phần 3) |
| 8 | Tích hợp báo cáo | Người C | 🟡 | Bị chặn, xem `report/INTEGRATION_STATUS.md`: thiếu source LaTeX báo cáo, `scoring_section.tex`, `poc_section.tex` và log chạy thật |
| 9 | Việc trên cluster | Quochuy | 🟡 | Xem bảng chi tiết dưới |

## Phần 9 (Quochuy) chi tiết

| # | Việc | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| 1 | Tạo repo GitHub | ✅ | `QuochuyChung/Improve-Paper-1` |
| 2 | Mời 4 người làm collaborator | ✅ | Quochuy xác nhận đã mời |
| 3 | Tạo 3 label `retrain`, `in-progress`, `done` | 🟡 | Script: `scripts/setup-github.sh` (cần `gh`, máy Windows chưa cài), hoặc tạo tay trên web |
| 4 | Fine-grained token (chỉ repo này, Issues read/write) | 🟡 | Đã tạo (Quochuy lưu riêng). Chưa kiểm tra dùng được: chạy `curl` tới `api.github.com/repos/QuochuyChung/Improve-Paper-1/issues` bằng token trong Secret, mong đợi `200`. KHÔNG dán token vào chat, KHÔNG commit |
| 5 | Gửi tên repo cho nhóm | ✅ | `QuochuyChung/Improve-Paper-1` (dạng `owner/repo` cho `GITHUB_REPO`) |
| 6 | Kiểm tra môi trường homelab | ✅ | Kết quả ở mục "Kết quả kiểm tra môi trường" |
| 6a | Cài Argo Workflows (namespace `argo`) bằng helm | ✅ | Release `argo-workflows` (chart 2.0.12, app v4.1.5) `deployed`, 2 pod `Running`, đủ CRD `workflows`, `workflowtemplates`, `workflowtaskresults` |
| 6b | PV NFS cho PVC `skelty-artifacts` | ✅ | `skelty-artifacts-pv`, 2Gi, RWO, `Retain`, `nfs-storage`, NFS `192.168.58.24:/data/skelty-artifacts`, trạng thái `Available` (chờ PVC). Manifest: `k8s/pv-skelty-artifacts.yaml` |
| 6c | Cài Pushgateway | ✅ | Release `prometheus-pushgateway` trong `monitoring-namespace`, pod `Running`. Service `prometheus-pushgateway:9091`. ServiceMonitor có label `release=huydevops`. Chưa kiểm tra Prometheus có kéo được target chưa |
| 6d | Điều tra API server chậm trên `kubernetes1` | 🟡 | Chưa tìm ra nguyên nhân gốc, xem mục "Sự cố API server" |
| 6e | Đổi repo sang private | ⬜ | Quochuy tự làm trên GitHub Settings |
| 6f | Cài CLI `argo` v4.1.5 trên `kubernetes1` | ✅ | `argo version` chạy được, khớp server |
| 6g | Tạo ServiceAccount `argo-workflow` trong `argo` | ✅ | Role/RoleBinding `argo-workflows-workflow` (quyền `create`, `patch` trên `workflowtaskresults`) gán cho SA này nhưng SA không tồn tại sẵn, đã tạo. Workflow phải chạy với `serviceAccountName: argo-workflow` |
| 6h | RoleBinding `default-workflowtaskresults` (namespace `argo`) | ✅ | Gán Role `argo-workflows-workflow` (chỉ `create`, `patch` trên `workflowtaskresults`) cho SA `default`, để workflow không gán `serviceAccountName` vẫn chạy được. Chưa kiểm chứng bằng workflow thật |
| 7 | Viết lại bản `skelty-poc` gốc (không ai trong nhóm có bản gốc, B cũng dùng pipeline giả) | 🟡 | Đã viết lại 2026-10-14: `pipeline/` (storage, acquire, process, train), `Dockerfile`, `.dockerignore`, `k8s/pvc.yaml`, `k8s/workflow-template.yaml`, `pipeline/tests/`, `pipeline/README.md`. **16/16 pytest đạt** (Python 3.12, scikit-learn 1.9.1). Đã chạy thử API serving của B trên artifact của pipeline mới: dữ liệu gốc 0 feature vượt 1,0 std, dữ liệu dịch 1,5 std cả 6 feature vượt, sau `/reload` sang model retrain 0 feature vượt. Chưa commit |
| 8 | Build image `skelty-poc:0.1`, apply PVC + WorkflowTemplate, chạy `baseline-001` | ⬜ | Chờ commit mục 7 và quyết định cách đưa image vào cụm (Harbor hay import vào 3 node; t nghiêng về import vào node cho PoC). Docker Desktop trên máy Windows chưa bật. Chưa build, chưa apply, chưa chạy Workflow thật |
| 9 | Tạo Secret `skelty-github` | ✅ | Đã tạo ngày 2026-10-14, có đủ hai khóa `GITHUB_TOKEN` và `GITHUB_REPO` (`QuochuyChung/Improve-Paper-1`). Chưa kiểm tra token dùng được (xem mục 4) |
| 10 | Deploy API (`k8s/serving.yaml`) | ⏳ | Code của B đã có trên `main`. Chờ mục 7, 8 |
| 11 | Deploy CronJob drift | ⏳ | Chờ Người D (Phần 3) |
| 12 | Deploy orchestrator, `DEFAULT_SHIFT=1.5` | ⏳ | Chờ Người C (Phần 4) |
| 13 | Chạy script kịch bản, giữ `scenario/logs/` | ⏳ | Chờ Phần 2 đến 4 chạy được |
| 14 | Chụp bằng chứng (Argo UI, issue, Grafana hoặc `/metrics`) | ⬜ | |
| 15 | Gửi log + ảnh cho Người C | ⬜ | |

## Thông tin môi trường đã biết

- Cụm K8s v1.30.14, containerd: `kubernetes1` control plane (chạy `kubectl` ở đây), `kubernetes2` và `kubernetes3` worker. Node `kubernetes1` chỉ có 3,8 GiB RAM, 3 nhân CPU, không swap.
- Có hai hệ NFS (cụm không có provisioner động, mọi PV tạo tay, reclaim `Retain`):
  - `nfs-storage` -> `deploy-server` `192.168.58.24`, export `/data` (`rw,sync,no_subtree_check,no_root_squash`, thư mục `/data` mode 777). Dùng cho uptime-kuma, Prometheus, maria, blog, và `skelty-artifacts`.
  - `nfs-storage-data-cluster` -> VIP `192.168.58.110` (cụm data, keepalived trên `data1`). Dùng cho mysql, postgres, mssql, vault, keycloak. Chưa kiểm tra cấu hình Ganesha.
- Phải bật `deploy-server` (`.24`) và cụm `data1/2/3` thì pod mới mount được volume.
- Prometheus: kube-prometheus-stack, release `huydevops`, namespace `monitoring-namespace`. ServiceMonitor phải có label `release: huydevops` (selector `matchLabels: release: huydevops`, quét mọi namespace).
- Cụm có sẵn Argo CD (khác Argo Workflows) và Rancher (Rancher UI báo cluster `huydevops` "agent is not connected").
- Registry: có Harbor trong homelab. Chưa quyết định push image lên Harbor hay import thẳng vào node.
- PVC `skelty-artifacts` là ReadWriteOnce. Vì backend là NFS nên nhiều khả năng pod trên node khác nhau vẫn mount được, nhưng chưa kiểm chứng. Pod `Pending` vì volume thì kiểm tra điều này trước.

## Kết quả kiểm tra môi trường

| Câu hỏi | Trả lời | Người cần biết |
| --- | --- | --- |
| Argo Workflows đã cài chưa? | **Đã cài** (2026-10-13), namespace `argo`. CLI `argo` v4.1.5 có trên `kubernetes1` | B, C, D |
| StorageClass cho PVC? | `nfs-storage` (cho PoC, trỏ vào `.24`). PV `skelty-artifacts-pv` đã tạo sẵn | B |
| Prometheus thu bằng annotation hay ServiceMonitor? | **ServiceMonitor** (Prometheus Operator). Giữ `k8s/servicemonitor.yaml` và đặt label `release: huydevops` | B (Phần 2) |
| Có Pushgateway không? | **Có.** URL trong cụm: `http://prometheus-pushgateway.monitoring-namespace:9091` (suy từ tên Service, chưa gọi thử) | D (Phần 3) |
| ServiceAccount cho workflow? | `argo-workflow` (namespace `argo`) | B, C |
| Cách đưa image vào cluster (Harbor hay import node)? | _chưa quyết định_ | B, C, D |

## Sự cố API server trên `kubernetes1` (mục 6d)

- Hiện tượng: `kubectl` và `helm` báo `TLS handshake timeout`, `/readyz` chập chờn 9 đến 22 giây, etcd lúc ok lúc fail, API server restart 47 lần, etcd 34 lần.
- Nguyên nhân gần nhất đã xác định: tiến trình `kube-apiserver` chiếm 2,3 đến 2,47 GB RAM trên node 3,8 GB, load average 63, node thrashing. Không phải pod của project khác. Số object trong etcd nhỏ (cao nhất 116 object/resource, cả cụm chừng 1.000), nên không phải do quá nhiều object. Có 107 CRD.
- Đợt vọt RAM sau reboot ngày 2026-10-13 (lên 2,3 GB trong 2 đến 3 phút) trùng với lúc cài Argo Workflows và Pushgateway (16:19). Reboot lần sau, không cài thêm gì, RSS chỉ 1,56 GB, available 1,1 GB. Nghi CRD lớn của Argo góp phần (chưa kiểm chứng).
- Chưa xác định: hai tiến trình `agent` (khoảng 120 đến 130 MB mỗi cái) trên `kubernetes1`. Nghi `cattle-cluster-agent` của Rancher, giả thuyết này yếu đi nhưng chưa loại.
- Cách xử lý đã thống nhất: theo dõi RSS của `kube-apiserver` khi chạy pipeline, KHÔNG cài thêm CRD lớn lên cụm cho tới khi biết thủ phạm. Hướng dự phòng: tăng RAM VM (Quochuy cho biết khó), hoặc chạy PoC trên Kubernetes của Docker Desktop trên máy cá nhân.
- Theo dõi: `watch -n5 'ps -o rss=,comm= -C kube-apiserver; free -m | sed -n 2p'`

## Việc đang chặn

1. **Quyết định cách đưa image vào cụm** (Harbor hay import vào 3 node) rồi build `skelty-poc:0.1`. Chặn mục 8: chạy `baseline-001`. Pod có thể chạy trên bất kỳ node nào nên image phải có trên cả 3 node nếu dùng import. Bản `skelty-poc` đã viết lại (mục 7), chờ commit.
2. **Người D chưa có code monitoring** (`monitoring/`, `k8s/drift-cronjob.yaml`), nên chưa dựng được vòng drift → ticket.
3. **Source LaTeX báo cáo chính, `scoring_section.tex`, `poc_section.tex` chưa có** (Người A, C).
4. Quochuy chưa xác nhận đã tạo 3 label và đổi repo sang private (làm tay trên web GitHub). Orchestrator và drift monitor cần 3 label này.
5. Pipeline mới chưa chạy thật trên Argo (có thể Argo 4.x đòi thêm trường mà test cục bộ không phát hiện được).
6. Người C nên thêm `serviceAccountName: argo-workflow` vào Workflow trong `orchestrator/argo_client.py` (hiện đang dựa vào RoleBinding cho `default`, mục 6h). Người B có thể cập nhật `serving/tests` dùng pipeline thật thay cho `fake_pipeline.py`.

## Tình trạng code trên `main` (ghi nhận 2026-10-14, chưa chạy test của ai)

Có file nghĩa là có trong repo, chưa nghĩa là chạy đúng. Máy của Quochuy chưa cài Python nên chưa chạy pytest.

| Phần | Người | Có trong repo |
| --- | --- | --- |
| 0 (nền) | Quochuy | `pipeline/`, `Dockerfile`, `k8s/pvc.yaml`, `k8s/workflow-template.yaml`, `k8s/pv-skelty-artifacts.yaml`. Test pipeline đã chạy: 16/16 đạt |
| 2 | B | `serving/`, `k8s/serving.yaml`, `k8s/servicemonitor.yaml` |
| 4 | C | `orchestrator/`, `k8s/orchestrator.yaml` |
| 5 | B | `scenario/run_scenario.py`, `scenario/tests/` |
| 8 | C | `report/INTEGRATION_STATUS.md` |
| 3, 1, 6 | D, A | chưa có gì |

## Quy ước cập nhật file này

- Mỗi người tự sửa dòng của phần mình khi có thay đổi, ghi ngày vào "Cập nhật lần cuối".
- Chỉ ghi ✅ khi đã chạy thật. Chưa thử trên cluster hoặc GitHub thật thì ghi 🟡 và nói rõ.
- Token, mật khẩu, IP công khai không được ghi vào file này.
