#!/usr/bin/env bash
# 01-start-gitea.sh — Start the Gitea container via Docker Compose.
#
# Usage:
#   bash Renovate/scripts/01-start-gitea.sh
#
# What it does:
#   • Runs `docker compose up -d gitea` from Renovate/docker/.
#   • Polls http://localhost:3000 until Gitea responds (up to ~90 seconds).
#
# Prerequisites: Docker with Compose v2 plugin
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENOVATE_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${RENOVATE_DIR}/docker/docker-compose.yml"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 1 — Start Gitea"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Verify Docker is running ──────────────────────────────────────────────────
if ! docker info > /dev/null 2>&1; then
    echo "❌  Docker daemon is not running. Start Docker Desktop and re-run."
    exit 1
fi

# ── Start Gitea ───────────────────────────────────────────────────────────────
echo "→ Starting Gitea …"
docker compose -f "${COMPOSE_FILE}" up -d gitea
echo ""

# ── Wait for Gitea to be ready ────────────────────────────────────────────────
echo "⏳ Waiting for Gitea at http://localhost:3000 …"
MAX_RETRIES=30
COUNT=0
until curl -sf http://localhost:3000/ > /dev/null 2>&1; do
    COUNT=$((COUNT + 1))
    if [ "${COUNT}" -ge "${MAX_RETRIES}" ]; then
        echo ""
        echo "❌  Gitea did not respond after $((MAX_RETRIES * 3)) seconds."
        echo "    Check logs: docker compose -f Renovate/docker/docker-compose.yml logs gitea"
        exit 1
    fi
    printf "   [%2d/%d] not ready — retrying in 3 s …\r" "${COUNT}" "${MAX_RETRIES}"
    sleep 3
done

echo ""
echo "✅  Gitea is ready at http://localhost:3000"
echo ""
echo "   Next step: bash Renovate/scripts/02-setup-gitea.sh"
echo ""

