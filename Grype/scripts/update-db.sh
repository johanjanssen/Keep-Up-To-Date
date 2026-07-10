#!/usr/bin/env bash
# update-db.sh — Download/update the Grype vulnerability database.
# Stores the DB in a Docker volume so it persists between scans.
set -euo pipefail
export MSYS_NO_PATHCONV=1

GRYPE_IMAGE="${GRYPE_IMAGE:-anchore/grype:latest}"
GRYPE_CACHE_VOL="${GRYPE_CACHE_VOL:-grype-db}"

echo ""
echo "============================================================"
echo "  Grype — Updating vulnerability database"
echo "============================================================"
echo ""

echo "-> Pulling Grype image: ${GRYPE_IMAGE} ..."
docker pull --quiet "${GRYPE_IMAGE}" 2>/dev/null || {
    docker image inspect "${GRYPE_IMAGE}" &>/dev/null || \
        { echo "❌  Cannot pull ${GRYPE_IMAGE} and no local copy available."; exit 1; }
    echo "⚠   Could not pull latest image; using local cached version."
}

echo "-> Updating vulnerability database ..."
docker run --rm \
    -v "${GRYPE_CACHE_VOL}:/.cache/grype" \
    "${GRYPE_IMAGE}" db update

echo ""
echo "-> Verifying database ..."
docker run --rm \
    -v "${GRYPE_CACHE_VOL}:/.cache/grype" \
    "${GRYPE_IMAGE}" db status

echo ""
echo "✅  Database ready. Stored in Docker volume '${GRYPE_CACHE_VOL}'."
echo ""
