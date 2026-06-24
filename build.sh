#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "  ${CYAN}◆${NC}  $*"; }
ok()   { echo -e "  ${GREEN}✔${NC}  $*"; }
err()  { echo -e "  ${RED}✘${NC}  $*"; }

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE="isms-demo-builder"

command -v docker &>/dev/null || { err "Docker not found."; exit 1; }

log "Building Windows .exe (first build may take 15-30 min)…"
docker build -f "$SRC_DIR/Dockerfile.build" -t "$IMAGE" "$SRC_DIR"

mkdir -p "$SRC_DIR/dist"
CID=$(docker create "$IMAGE")
docker cp "$CID:/ISMS-Demo" "$SRC_DIR/dist/"
docker rm "$CID" >/dev/null 2>&1 || true

if [ -f "$SRC_DIR/dist/ISMS-Demo/ISMS-Demo.exe" ]; then
  ok "Build complete!"
  echo ""
  echo "  Output: ${SRC_DIR}/dist/ISMS-Demo/ISMS-Demo.exe"
  echo "  Size:   $(du -sh "$SRC_DIR/dist/ISMS-Demo" | cut -f1)"
  echo ""
  echo "  To distribute:"
  echo "    cd ${SRC_DIR}/dist && zip -r ISMS-Demo ISMS-Demo"
else
  err "Build failed — ISMS-Demo.exe not found in dist/"
  exit 1
fi
