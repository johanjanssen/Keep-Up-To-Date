#!/usr/bin/env bash
# scan-image.sh — Scan a single Docker image with OSV-Scanner.
# Usage: bash scripts/scan-image.sh <image>
# Example: bash scripts/scan-image.sh eclipse-temurin:25-jre
#
# OSV-Scanner's own container image has no docker CLI in it, so it can't
# `docker save` an image itself the way `osv-scanner scan image <name>` does
# when run natively. We do the `docker save` on the host instead and hand
# OSV-Scanner the resulting archive with `scan image --archive`.
set -euo pipefail
export MSYS_NO_PATHCONV=1

IMAGE="${1:-eclipse-temurin:25-jre}"
OSV_IMAGE="${OSV_IMAGE:-ghcr.io/google/osv-scanner:latest}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Scanning: $IMAGE"
docker save "$IMAGE" -o "$TMP_DIR/image.tar"

# OSV-Scanner exits 1 when it finds vulnerabilities (not a real error) —
# don't let `set -e` treat that as a script failure.
docker run --rm -v "$TMP_DIR:/scan:ro" "$OSV_IMAGE" \
    scan image --archive /scan/image.tar --format table || true
