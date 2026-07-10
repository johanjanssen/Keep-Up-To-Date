#!/usr/bin/env bash
# update-db.sh — Download/update the Trivy vulnerability database.
# Stores the DB in a Docker volume so it persists between scans.
set -euo pipefail
export MSYS_NO_PATHCONV=1

TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.71.2}"
TRIVY_CACHE_VOL="${TRIVY_CACHE_VOL:-trivy-db}"

echo ""
echo "============================================================"
echo "  Trivy — Updating vulnerability database"
echo "============================================================"
echo ""

echo "-> Pulling Trivy image: ${TRIVY_IMAGE} ..."
if ! docker pull --quiet "${TRIVY_IMAGE}" 2>/dev/null; then
    docker image inspect "${TRIVY_IMAGE}" &>/dev/null || \
        { echo "❌  Cannot pull ${TRIVY_IMAGE} and no local copy available."; exit 1; }
    echo "⚠   Could not pull latest image; using local cached version."
fi

echo "-> Trivy version: $(docker run --rm "${TRIVY_IMAGE}" --version 2>/dev/null | head -1)"

echo "-> Downloading vulnerability database ..."
docker run --rm \
    -v "${TRIVY_CACHE_VOL}:/root/.cache" \
    "${TRIVY_IMAGE}" image --download-db-only --quiet

echo "-> Downloading Java vulnerability database ..."
docker run --rm \
    -v "${TRIVY_CACHE_VOL}:/root/.cache" \
    "${TRIVY_IMAGE}" image --download-java-db-only --quiet

echo ""
echo "✅  Database ready. Stored in Docker volume '${TRIVY_CACHE_VOL}'."
echo ""
