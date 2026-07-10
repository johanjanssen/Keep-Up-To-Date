#!/usr/bin/env bash
# start-cache.sh — Start the local NVD data-feed cache server.
#
# Uses the official jeremylong/open-vulnerability-data-mirror image.
# NVD data is stored in data/nvd-cache/ on the host (bind-mount) so it
# survives container removal and is directly inspectable on disk.
#
# Usage:
#   bash scripts/start-cache.sh
#   NVD_API_KEY=your-key bash scripts/start-cache.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load NVD_API_KEY from .env if present and not already set in the environment
ENV_FILE="${PROJECT_DIR}/.env"
if [[ -f "${ENV_FILE}" ]] && [[ -z "${NVD_API_KEY:-}" ]]; then
    # shellcheck source=../.env
    set -o allexport; source "${ENV_FILE}"; set +o allexport
fi

MIRROR_IMAGE="jeremylong/open-vulnerability-data-mirror:latest"
CONTAINER_NAME="nvd-cache"
HOST_PORT=7070
DATA_DIR="${PROJECT_DIR}/data/nvd-cache"
mkdir -p "${DATA_DIR}"

# Docker on Windows (Git Bash / MSYS2) mangles Unix paths that contain spaces.
# cygpath -m converts  /c/Some Path/...  →  C:/Some Path/...  which Docker
# Desktop accepts reliably.  On Linux/macOS cygpath is absent so we keep the
# original path.
DOCKER_DATA_DIR="${DATA_DIR}"
if command -v cygpath &>/dev/null; then
    DOCKER_DATA_DIR="$(cygpath -m "${DATA_DIR}")"
fi

echo ""
echo "============================================================"
echo "  OWASP Demo — NVD data-feed cache server"
echo "============================================================"
echo ""

# ── Already running? ──────────────────────────────────────────────────────────
if docker ps --filter "name=^/${CONTAINER_NAME}$" --format '{{.Names}}' \
        | grep -q "^${CONTAINER_NAME}$"; then
    echo "   Container '${CONTAINER_NAME}' is already running on port ${HOST_PORT}."
    echo ""
    echo "------------------------------------------------------------"
    echo "OK  NVD cache server: http://localhost:${HOST_PORT}/"
    echo "    Run the scan : bash scripts/run-check.sh"
    echo "------------------------------------------------------------"
    echo ""
    exit 0
fi

# Remove a stopped container with the same name
docker rm -f "${CONTAINER_NAME}" &>/dev/null || true

# ── Detect whether NVD data already exists on disk ───────────────────────────
shopt -s nullglob
_NVD_FILES=( "${DATA_DIR}"/nvdcve-*.json.gz )
shopt -u nullglob
DATA_EXISTS=false
[[ ${#_NVD_FILES[@]} -gt 0 ]] && DATA_EXISTS=true

# Warn if data looks stale (missing the previous calendar year)
CURRENT_YEAR=$(date +%Y)
PREV_YEAR=$(( CURRENT_YEAR - 1 ))
if $DATA_EXISTS && [[ ! -f "${DATA_DIR}/nvdcve-${PREV_YEAR}.json.gz" ]]; then
    echo "   WARNING: NVD data may be stale — nvdcve-${PREV_YEAR}.json.gz not found."
    echo "   Run: bash scripts/update-cache.sh"
    echo ""
fi

# ── Start the mirror container ───────────────────────────────────────────────
echo "   Image : ${MIRROR_IMAGE}"
echo "   Port  : ${HOST_PORT}"
echo "   Data  : ${DATA_DIR}"
echo ""

if [[ -n "${NVD_API_KEY:-}" ]]; then
    echo "   NVD_API_KEY detected — fast download mode."
else
    echo "   TIP: Set NVD_API_KEY for faster first-time downloads:"
    echo "     export NVD_API_KEY=your-key   # https://nvd.nist.gov/developers/request-an-api-key"
fi
echo ""

if $DATA_EXISTS; then
    echo "-> NVD data found on disk — starting container to serve existing data ..."
else
    echo "-> No local NVD data found — starting container (run update-cache.sh to download) ..."
fi

ENV_ARGS=()
[[ -n "${NVD_API_KEY:-}" ]] && ENV_ARGS=(--env "NVD_API_KEY=${NVD_API_KEY}")

docker run \
    --detach \
    --name "${CONTAINER_NAME}" \
    --publish "${HOST_PORT}:80" \
    --volume "${DOCKER_DATA_DIR}:/usr/local/apache2/htdocs" \
    "${ENV_ARGS[@]}" \
    "${MIRROR_IMAGE}"

# ── Wait for Apache to be ready ───────────────────────────────────────────────
echo "   Waiting for Apache to start ..."
for i in $(seq 1 15); do
    if curl -sf "http://localhost:${HOST_PORT}/" -o /dev/null 2>/dev/null; then
        break
    fi
    sleep 2
done

if $DATA_EXISTS; then
    echo "   Serving existing NVD data."
else
    echo "   Container started. Run update-cache.sh to download NVD data."
fi

echo ""
echo "------------------------------------------------------------"
echo "OK  NVD cache server is running:"
echo "    URL      : http://localhost:${HOST_PORT}/"
echo "    Container: ${CONTAINER_NAME}"
echo "    Data dir : ${DATA_DIR}"
echo ""
echo "  Fetch / refresh NVD data (incremental):"
echo "    bash scripts/update-cache.sh"
echo ""
echo "  Run the scan:"
echo "    bash scripts/run-check.sh"
echo ""
echo "  To stop:"
echo "    docker stop ${CONTAINER_NAME}"
echo "------------------------------------------------------------"
echo ""

