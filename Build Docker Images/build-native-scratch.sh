#!/usr/bin/env bash
# Builds hello-conference:native-scratch  (runtime base: scratch – zero OS overhead)
# Improvements over native-minimal-distroless-static:
#   • strip --strip-all removes ELF symbol/debug sections after native compile
#   • FROM scratch eliminates the ~2 MB distroless/static base layer
# ⚠  First build: ~20-25 min (musl + zlib compiled from source + native compile).
#    Subsequent builds use cached toolchain layers and are much faster.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.native-scratch" \
    --tag   "hello-conference:native-scratch" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:native-scratch"

