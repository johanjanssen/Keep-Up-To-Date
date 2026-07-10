#!/usr/bin/env bash
# scan-image.sh — Scan a single Docker image with Grype.
# Usage: bash scripts/scan-image.sh <image>
# Example: bash scripts/scan-image.sh eclipse-temurin:25-jre
set -euo pipefail
export MSYS_NO_PATHCONV=1

IMAGE="${1:-eclipse-temurin:25-jre}"
GRYPE_IMAGE="${GRYPE_IMAGE:-anchore/grype:latest}"
GRYPE_CACHE_VOL="${GRYPE_CACHE_VOL:-grype-db}"
DOCKER_SOCK="/var/run/docker.sock"

echo "Scanning: $IMAGE"
docker run --rm \
    -v "$DOCKER_SOCK:$DOCKER_SOCK" \
    -v "$GRYPE_CACHE_VOL:/.cache/grype" \
    "$GRYPE_IMAGE" "$IMAGE" -o table
