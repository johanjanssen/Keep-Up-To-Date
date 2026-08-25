#!/usr/bin/env bash
# Builds all Docker images used by this project.
# Order: pull base images, build JVM images, then native images.
#
# A failure building one image (e.g. a transient network blip fetching musl/zlib
# for the native builds) does NOT abort the whole run — it's recorded and every
# remaining image is still attempted, so one flaky variant can't block building
# (and later scanning) of the other ten. The script still exits non-zero if
# anything failed, so CI surfaces it.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAILED=()

run_step() {
    local SCRIPT_NAME="$1"
    echo ""
    echo "============================================================"
    echo "Running ${SCRIPT_NAME}"
    echo "============================================================"
    if ! bash "${SCRIPT_DIR}/${SCRIPT_NAME}"; then
        echo "❌  ${SCRIPT_NAME} FAILED"
        FAILED+=("${SCRIPT_NAME}")
    fi
}

# Nothing can build without the base images — fail fast here.
run_step "pull-base-images.sh"
if [[ ${#FAILED[@]} -gt 0 ]]; then
    echo ""
    echo "❌  Cannot continue without base images."
    exit 1
fi

run_step "build-jre-temurin.sh"
run_step "build-jre-temurin-alpine.sh"
run_step "build-jlink-distroless-base-debian.sh"
run_step "build-jlink-full-distroless-base-debian.sh"
run_step "build-jlink-netty-distroless-base-debian.sh"
run_step "build-jlink-cds-distroless-base-debian.sh"
run_step "build-crac-azul-distroless-base-debian.sh"
run_step "build-native-debian-slim.sh"
run_step "build-native-minimal-distroless-static-debian.sh"
run_step "build-native-scratch.sh"
run_step "build-native-netty-scratch.sh"

echo ""
if [[ ${#FAILED[@]} -eq 0 ]]; then
    echo "✅  All Docker images built successfully."
else
    echo "⚠️   ${#FAILED[@]} image(s) failed to build:"
    printf '    - %s\n' "${FAILED[@]}"
    echo "    (the other images were still built — see the log above for details)"
    exit 1
fi