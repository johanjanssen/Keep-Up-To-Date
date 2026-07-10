#!/usr/bin/env bash
# update-cache.sh — Incrementally update the NVD mirror inside the running
# cache container.  Calls /mirror.sh (vulnz cve --cache) inside the container,
# which fetches only new / modified CVEs and creates any missing year files
# (e.g. nvdcve-2025.json.gz, nvdcve-2026.json.gz).  Existing year files are
# updated in-place; nothing is deleted.
#
# cache.properties (written on first completion) is the incremental checkpoint:
#   - Present  → only CVEs modified since lastModifiedDate are downloaded (fast)
#   - Absent   → full download from 2002 to today (5-15 min, once)
#
# Prerequisites: cache container must already be running.
#   bash scripts/start-cache.sh   # start Apache + container first
#   bash scripts/update-cache.sh  # then run this to fetch / refresh NVD data
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

CONTAINER_NAME="nvd-cache"
HOST_PORT=7070
DATA_DIR="${PROJECT_DIR}/data/nvd-cache"

echo ""
echo "============================================================"
echo "  OWASP Demo — NVD data mirror update"
echo "============================================================"
echo ""

# ── Ensure container is running ───────────────────────────────────────────────
if ! docker ps --filter "name=^/${CONTAINER_NAME}$" --format '{{.Names}}' \
        | grep -q "^${CONTAINER_NAME}$"; then
    echo "-> Container '${CONTAINER_NAME}' is not running — starting it first ..."
    echo ""
    bash "${SCRIPT_DIR}/start-cache.sh"
    echo ""
fi

# ── Pre-update state ──────────────────────────────────────────────────────────
CURRENT_YEAR=$(date +%Y)
echo "   Container : ${CONTAINER_NAME}"
echo "   Data dir  : ${DATA_DIR}"
echo ""
echo "   Year files before update:"
for YEAR in $(seq 2020 "$CURRENT_YEAR"); do
    if [[ -f "${DATA_DIR}/nvdcve-${YEAR}.json.gz" ]]; then
        echo "     nvdcve-${YEAR}.json.gz  [ok]"
    else
        echo "     nvdcve-${YEAR}.json.gz  [missing]"
    fi
done
echo ""

if [[ -f "${DATA_DIR}/cache.properties" ]]; then
    LAST_MOD="$(grep 'lastModifiedDate' "${DATA_DIR}/cache.properties" 2>/dev/null || echo '(unknown)')"
    echo "   cache.properties : found  — update will be incremental"
    echo "   ${LAST_MOD}"
else
    echo "   cache.properties : not found — first run will download all data from 2002"
    echo "   This will take 5-15 min.  Subsequent runs are incremental (seconds/minutes)."
fi
echo ""

# ── Trigger update inside the running container ───────────────────────────────
echo "-> Running /mirror.sh inside container '${CONTAINER_NAME}' ..."
echo "   NVD_API_KEY is read from the container's own environment."
echo ""

docker exec -u mirror "${CONTAINER_NAME}" /mirror.sh

# ── Post-update state ─────────────────────────────────────────────────────────
echo ""
echo "   Year files after update:"
for YEAR in $(seq 2020 "$CURRENT_YEAR"); do
    if [[ -f "${DATA_DIR}/nvdcve-${YEAR}.json.gz" ]]; then
        echo "     nvdcve-${YEAR}.json.gz  [ok]"
    else
        echo "     nvdcve-${YEAR}.json.gz  [missing — check docker logs ${CONTAINER_NAME}]"
    fi
done
echo ""

echo "------------------------------------------------------------"
echo "OK  NVD data update complete."
echo "    Served at : http://localhost:${HOST_PORT}/"
echo "    Run scan  : bash scripts/run-check.sh"
echo "------------------------------------------------------------"
echo ""

