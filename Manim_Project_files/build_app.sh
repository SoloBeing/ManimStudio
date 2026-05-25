#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$ROOT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# Build React UI before packaging
echo "Building React UI..."
cd ui && npm run build
cd "$ROOT_DIR"

echo "Running PyInstaller..."
uv run python -m PyInstaller \
  --clean \
  --noconfirm \
  --distpath "$PROJECT_DIR/dist" \
  --workpath "build" \
  ManimStudio.spec

echo "Built app: $PROJECT_DIR/dist/ManimStudio"
