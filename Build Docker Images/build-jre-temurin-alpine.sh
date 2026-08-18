#!/usr/bin/env bash
# Builds hello-conference:jre-temurin-alpine  (runtime base: eclipse-temurin:25-jre-alpine)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.jre-temurin-alpine" \
    --tag   "hello-conference:jre-temurin-alpine" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:jre-temurin-alpine"
