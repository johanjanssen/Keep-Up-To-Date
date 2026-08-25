#!/usr/bin/env bash
# Builds hello-conference:jlink-distroless-base-debian  (runtime base: gcr.io/distroless/base-debian13)
# Uses jdeps to detect only the modules the application actually needs.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.jlink-distroless-base-debian" \
    --tag   "hello-conference:jlink-distroless-base-debian" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:jlink-distroless-base-debian"


