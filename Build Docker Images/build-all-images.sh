#!/usr/bin/env bash
# Builds all Docker images used by this project.
# Order: pull base images, build JVM images, then native images.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_step() {
    local SCRIPT_NAME="$1"
    echo ""
    echo "============================================================"
    echo "Running ${SCRIPT_NAME}"
    echo "============================================================"
    bash "${SCRIPT_DIR}/${SCRIPT_NAME}"
}

run_step "pull-base-images.sh"
run_step "build-jre-temurin.sh"
run_step "build-jlink-distroless-base.sh"
run_step "build-jlink-full-distroless-base.sh"
run_step "build-jlink-netty-distroless-base.sh"
run_step "build-jlink-cds-distroless-base.sh"
run_step "build-jlink-tuned-distroless-base.sh"
run_step "build-crac-azul-distroless-base.sh"
run_step "build-native-debian-slim.sh"
run_step "build-native-minimal-distroless-static.sh"
run_step "build-native-scratch.sh"
run_step "build-native-netty-scratch.sh"

echo ""
echo "✅  All Docker images built successfully."

