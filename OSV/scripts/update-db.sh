#!/usr/bin/env bash
# update-db.sh — Pull/refresh the OSV-Scanner Docker image.
# Unlike Grype/Trivy, OSV-Scanner has no offline vulnerability database to
# download up front: by default it matches packages against the live OSV.dev
# API on every scan, so "updating" just means having the latest scanner image.
set -euo pipefail
export MSYS_NO_PATHCONV=1

OSV_IMAGE="${OSV_IMAGE:-ghcr.io/google/osv-scanner:latest}"

echo ""
echo "============================================================"
echo "  OSV-Scanner — Updating scanner image"
echo "============================================================"
echo ""

echo "-> Pulling OSV-Scanner image: ${OSV_IMAGE} ..."
if ! docker pull --quiet "${OSV_IMAGE}" 2>/dev/null; then
    docker image inspect "${OSV_IMAGE}" &>/dev/null || \
        { echo "❌  Cannot pull ${OSV_IMAGE} and no local copy available."; exit 1; }
    echo "⚠   Could not pull latest image; using local cached version."
fi

echo "-> OSV-Scanner version: $(docker run --rm "${OSV_IMAGE}" --version 2>/dev/null | head -1)"

echo ""
echo "✅  Ready. OSV-Scanner queries the live OSV.dev API — no local DB to cache."
echo ""
