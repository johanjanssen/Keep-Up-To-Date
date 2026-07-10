#!/usr/bin/env bash
# Builds hello-conference:native-netty-scratch
# Spring WebFlux (Netty) + musl static + -Os + strip + FROM scratch
# ⚠  First build: ~20-25 min. Subsequent source-only rebuilds use cached layers.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.native-netty-scratch" \
    --tag   "hello-conference:native-netty-scratch" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:native-netty-scratch"
