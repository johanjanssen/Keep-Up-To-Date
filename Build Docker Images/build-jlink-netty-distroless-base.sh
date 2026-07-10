#!/usr/bin/env bash
# Builds hello-conference:jlink-netty-distroless-base  (runtime base: gcr.io/distroless/base-debian12)
# Uses Spring WebFlux (Netty) instead of Spring MVC (Tomcat) and jdeps to detect
# only the modules the application actually needs – yielding a smaller JRE than
# the Tomcat-based jlink-distroless-base variant.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.jlink-netty-distroless-base" \
    --tag   "hello-conference:jlink-netty-distroless-base" \
    --pull=false \
    --progress=plain \
    "$(dirname "$SCRIPT_DIR")/Vulnerable Application"
echo "✅  hello-conference:jlink-netty-distroless-base"

