#!/usr/bin/env bash
# Builds hello-conference:jlink-full-distroless-base  (runtime base: gcr.io/distroless/base-debian12)
# Includes ALL JDK modules (no jdeps analysis) – equivalent to a full JRE.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.jlink-full-distroless-base" \
    --tag   "hello-conference:jlink-full-distroless-base" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:jlink-full-distroless-base"


