#!/usr/bin/env bash
# Tạo 3 label dùng cho ticket retrain. Cần `gh` đã đăng nhập (gh auth login).
# Dùng: ./scripts/setup-github.sh [owner/repo]
set -euo pipefail

REPO="${1:-QuochuyChung/Improve-Paper-1}"

gh label create retrain     --repo "$REPO" --color D93F0B --description "Ticket yêu cầu retrain model (drift)" --force
gh label create in-progress --repo "$REPO" --color FBCA04 --description "Orchestrator đang xử lý"              --force
gh label create done        --repo "$REPO" --color 0E8A16 --description "Đã retrain xong"                      --force

gh label list --repo "$REPO"
