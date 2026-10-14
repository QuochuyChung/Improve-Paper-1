#!/usr/bin/env bash
# Tạo Secret skelty-github trong namespace argo. Token đọc từ biến môi trường hoặc nhập tay
# (không echo ra màn hình, không ghi vào file, không commit).
# Dùng: ./scripts/create-secret.sh [owner/repo]
set -euo pipefail

REPO="${1:-QuochuyChung/Improve-Paper-1}"

if [ -z "${GITHUB_TOKEN:-}" ]; then
  read -r -s -p "GITHUB_TOKEN (fine-grained, chỉ Issues read/write): " GITHUB_TOKEN
  echo
fi

kubectl -n argo create secret generic skelty-github \
  --from-literal=GITHUB_TOKEN="$GITHUB_TOKEN" \
  --from-literal=GITHUB_REPO="$REPO" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl -n argo get secret skelty-github
