#!/usr/bin/env bash
# Builds hello-conference:jlink-tuned-distroless-base
# Tighter jlink module set + SerialGC + container-aware heap sizing.
# Same optimisations as jlink-cds-distroless-base but without the AppCDS training run.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.jlink-tuned-distroless-base" \
    --tag   "hello-conference:jlink-tuned-distroless-base" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:jlink-tuned-distroless-base"
