#!/usr/bin/env bash
# Builds hello-conference:jlink-cds-distroless-base-debian
# Minimal jlink JRE (tighter module set) + AppCDS archive pre-generated at
# image-build time + SerialGC + container-aware heap sizing.
# Expected vs jlink-distroless-base-debian: smaller image, ~60% lower memory, ~3x faster startup.
# ⚠  The CDS training run adds ~1-2 min to the build (one cold JVM start).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.jlink-cds-distroless-base-debian" \
    --tag   "hello-conference:jlink-cds-distroless-base-debian" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:jlink-cds-distroless-base-debian"
