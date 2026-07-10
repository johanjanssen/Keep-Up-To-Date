#!/usr/bin/env bash
# Builds hello-conference:native-debian-slim  (runtime base: debian:12-slim)
# Dynamically-linked GraalVM native executable; needs glibc + libz at runtime.
# ⚠  Native compilation takes 5-15 minutes.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.native-debian-slim" \
    --tag   "hello-conference:native-debian-slim" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:native-debian-slim"


