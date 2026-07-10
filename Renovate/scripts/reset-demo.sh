#!/usr/bin/env bash
# reset-demo.sh — Completely wipe the demo environment for a clean re-run.
#
# Removes:
#   • All demo Docker containers (Gitea, Jenkins)
#   • All named Docker volumes (Gitea data, Jenkins data)
#   • The built Jenkins Docker image (so --build recreates it fresh)
#   • Generated credential file (Renovate/.env)
#   • The local 'gitea' git remote
#
# This script is intentionally NOT called from demo.sh.
# Run it manually when you want a clean slate:
#
#   bash Renovate/scripts/reset-demo.sh
#
# Then re-run the demo:
#   bash Renovate/scripts/demo.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENOVATE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$RENOVATE_DIR")"
COMPOSE_FILE="${RENOVATE_DIR}/docker/docker-compose.yml"

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║   HelloConference Demo — Full Reset                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  This will permanently remove:"
echo "    • Gitea container + all repository data"
echo "    • Jenkins container + all job/build history"
echo "    • Renovate/.env (generated API token)"
echo "    • Built Jenkins Docker image (rebuilt on next demo.sh run)"
echo ""
read -r -p "  Continue? [y/N] " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
    echo ""
    echo "  Aborted — nothing was changed."
    echo ""
    exit 0
fi
echo ""

# ── Stop containers and delete named volumes ──────────────────────────────────
echo "→ Stopping containers and removing volumes …"
docker compose -f "${COMPOSE_FILE}" down --volumes --remove-orphans 2>/dev/null \
    || true
echo "   ✅  Containers and volumes removed."
echo ""

# ── Remove the built Jenkins image ───────────────────────────────────────────
# Forces a full rebuild (including plugin download) on the next run.
echo "→ Removing built Jenkins image …"
docker image rm helloconference-jenkins:latest 2>/dev/null \
    && echo "   ✅  Image removed — will be rebuilt on next run." \
    || echo "   ℹ️   Image not found — skipping."
echo ""

# ── Remove generated token/env files ─────────────────────────────────────────
echo "→ Removing generated credential files …"
rm -f "${RENOVATE_DIR}/.env"
echo "   ✅  Renovate/.env removed."
echo ""

# ── Remove the 'gitea' git remote from the local repo ────────────────────────
echo "→ Removing local 'gitea' git remote …"
if git -C "${PROJECT_DIR}" remote get-url gitea > /dev/null 2>&1; then
    git -C "${PROJECT_DIR}" remote remove gitea
    echo "   ✅  Remote removed."
else
    echo "   ℹ️   Remote 'gitea' not configured — skipping."
fi
echo ""

# ── Remove the generated root-level renovate.json ───────────────────────────
# This file is re-created by 03-push-code.sh from Renovate/renovate.json.
if [ -f "${PROJECT_DIR}/renovate.json" ]; then
    echo "→ Removing generated renovate.json at project root …"
    rm -f "${PROJECT_DIR}/renovate.json"
    echo "   ✅  renovate.json removed."
    echo ""
fi

echo "──────────────────────────────────────────────────────────────"
echo "✅  Reset complete."
echo ""
echo "   Re-run the full demo:"
echo "   bash Renovate/scripts/demo.sh"
echo "──────────────────────────────────────────────────────────────"
echo ""

