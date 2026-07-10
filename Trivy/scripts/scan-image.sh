#!/usr/bin/env bash
# scan-image.sh — Scan a single Docker image with Trivy.
# Usage: bash scripts/scan-image.sh <image>
# Example: bash scripts/scan-image.sh eclipse-temurin:25-jre
set -euo pipefail
export MSYS_NO_PATHCONV=1

IMAGE="${1:-eclipse-temurin:25-jre}"
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.71.2}"
TRIVY_CACHE_VOL="${TRIVY_CACHE_VOL:-trivy-db}"
DOCKER_SOCK="/var/run/docker.sock"
SEVERITY="${SEVERITY:-CRITICAL,HIGH}"

echo "Scanning: $IMAGE  (severity filter: $SEVERITY)"
docker run --rm \
    -v "$DOCKER_SOCK:$DOCKER_SOCK" \
    -v "$TRIVY_CACHE_VOL:/root/.cache" \
    "$TRIVY_IMAGE" image \
    --severity "$SEVERITY" \
    --format table \
    --scanners vuln \
    "$IMAGE"
