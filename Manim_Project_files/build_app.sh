#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$ROOT_DIR/.." && pwd)"
cd "$ROOT_DIR"

python3 -m PyInstaller \
  --clean \
  --noconfirm \
  --distpath "$PROJECT_DIR/dist" \
  --workpath "build" \
  ManimStudio.spec

echo "Built app: $PROJECT_DIR/dist/ManimStudio"
