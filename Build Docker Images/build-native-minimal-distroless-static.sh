#!/usr/bin/env bash
# Builds hello-conference:native-minimal-distroless-static  (runtime base: gcr.io/distroless/static-debian12)
# Static musl binary + -Os optimisation.
# ⚠  First build: ~20 minutes (musl + zlib compiled from source + native compile).
#    Subsequent builds use cached toolchain layers and are much faster.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.native-minimal-distroless-static" \
    --tag   "hello-conference:native-minimal-distroless-static" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:native-minimal-distroless-static"


