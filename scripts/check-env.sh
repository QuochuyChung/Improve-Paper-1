#!/usr/bin/env bash
# Kiểm tra môi trường homelab cho PoC. Chạy trên kubernetes1 (control plane, có kubectl).
# Dán toàn bộ output vào PROGRESS.md (mục "Kết quả kiểm tra môi trường") hoặc gửi nhóm.
# Không in ra token / secret.
set -uo pipefail

section() { printf '\n===== %s =====\n' "$1"; }

section "Nodes (PVC ReadWriteOnce => pod dùng chung phải cùng node)"
kubectl get nodes -o wide

section "Namespace argo"
kubectl get ns argo

section "Argo Workflows (pods + CRD)"
kubectl -n argo get pods
kubectl get crd | grep -i argoproj || echo "KHÔNG thấy CRD argoproj => Argo Workflows chưa cài"
command -v argo >/dev/null && argo version || echo "CLI argo chưa cài trên máy này"

section "StorageClass (cho PVC skelty-artifacts)"
kubectl get storageclass

section "PV/PVC hiện có trong argo"
kubectl get pv
kubectl -n argo get pvc

section "Prometheus: Operator (ServiceMonitor) hay annotation?"
kubectl get crd | grep -i -E "servicemonitor|prometheus" || echo "Không có CRD Prometheus Operator => dùng annotation prometheus.io/scrape, bỏ servicemonitor.yaml"
kubectl get pods -A | grep -i -E "prometheus|pushgateway|grafana" || echo "Không thấy pod prometheus/pushgateway/grafana"

section "Registry / import image"
echo "Harbor nằm ở harbor-server (xem Resource.xlsx). Cần xác nhận: push image vào Harbor hay import thẳng vào node?"
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.nodeInfo.containerRuntimeVersion}{"\n"}{end}'
