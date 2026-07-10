#!/usr/bin/env bash
# demo.sh — Full end-to-end demo: Gitea + Jenkins + Renovate.
#
# Runs all five steps in sequence:
#   1. Start Gitea
#   2. Configure Gitea (admin user, repository, API token)
#   3. Push HelloConference project code
#   4. Build Jenkins image, start container, create pipeline job
#   5. Run Renovate — creates real dependency-update PRs
#
# Each Renovate PR is automatically built by Jenkins (via Gitea webhook).
# Build status (pass/fail) is reported back to the PR as a required check.
#
# Usage:
#   bash Renovate/scripts/demo.sh                          full setup + live PRs
#   RENOVATE_ONLY=true bash Renovate/scripts/demo.sh       skip setup, re-run Renovate
#   DRY_RUN=true bash Renovate/scripts/demo.sh             setup only, Renovate dry run
#
# Individual steps:
#   bash Renovate/scripts/01-start-gitea.sh
#   bash Renovate/scripts/02-setup-gitea.sh
#   bash Renovate/scripts/03-push-code.sh
#   bash Renovate/scripts/04-start-jenkins.sh
#   bash Renovate/scripts/05-run-renovate.sh
#
# Cleanup:
#   docker compose -f Renovate/docker/docker-compose.yml down      keep data
#   docker compose -f Renovate/docker/docker-compose.yml down -v   wipe everything
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RENOVATE_ONLY="${RENOVATE_ONLY:-false}"
export DRY_RUN="${DRY_RUN:-false}"

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║   HelloConference — Gitea + Jenkins + Renovate Demo          ║"
echo "║   'Never Fall Behind: A Practical Guide to Staying Current'  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Services:"
echo "    • Gitea   — self-hosted Git forge     (http://localhost:3000)"
echo "    • Jenkins — CI build server           (http://localhost:8080)"
echo "    • Renovate — dependency update bot    (one-shot container)"
echo ""
echo "  Prerequisites: Docker, git, curl"
echo ""

if [ "${DRY_RUN}" = "true" ]; then
    echo "  Mode: DRY RUN — Renovate logs proposed changes; no PRs created."
else
    echo "  Mode: LIVE — Renovate creates real PRs; Jenkins builds each one."
fi
echo ""

# ── Error handler ─────────────────────────────────────────────────────────────
on_error() {
    echo ""
    echo "❌  Demo failed at the step above."
    echo ""
    echo "   Retry individual steps:"
    echo "     bash Renovate/scripts/01-start-gitea.sh"
    echo "     bash Renovate/scripts/02-setup-gitea.sh"
    echo "     bash Renovate/scripts/03-push-code.sh"
    echo "     bash Renovate/scripts/04-start-jenkins.sh"
    echo "     bash Renovate/scripts/05-run-renovate.sh"
    echo ""
    echo "   Logs:"
    echo "     docker compose -f Renovate/docker/docker-compose.yml logs gitea"
    echo "     docker compose -f Renovate/docker/docker-compose.yml logs jenkins"
    echo ""
    echo "   Clean reset:"
    echo "     docker compose -f Renovate/docker/docker-compose.yml down -v"
}
trap on_error ERR

# ── Run steps ─────────────────────────────────────────────────────────────────
if [ "${RENOVATE_ONLY}" != "true" ]; then
    bash "${SCRIPT_DIR}/01-start-gitea.sh"
    echo ""
    bash "${SCRIPT_DIR}/02-setup-gitea.sh"
    echo ""
    bash "${SCRIPT_DIR}/03-push-code.sh"
    echo ""
    bash "${SCRIPT_DIR}/04-start-jenkins.sh"
    echo ""
fi

bash "${SCRIPT_DIR}/05-run-renovate.sh"

# ── Final summary ─────────────────────────────────────────────────────────────
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║   ✅  Demo Complete                                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "  🌐 Gitea UI        http://localhost:3000"
echo "  📁 Repository      http://localhost:3000/gitadmin/hello-conference"
echo "  🔀 Pull requests   http://localhost:3000/gitadmin/hello-conference/pulls"
echo "  🔑 Gitea login     gitadmin  /  Admin1234!"
echo ""
echo "  🔧 Jenkins UI      http://localhost:8080"
echo "  🏗  Pipeline job    http://localhost:8080/job/hello-conference/"
echo "  🔑 Jenkins login   admin  /  Admin1234!"
echo ""
echo "  Useful commands:"
echo ""
echo "    # Re-run Renovate (e.g. after changing renovate.json):"
echo "    bash Renovate/scripts/05-run-renovate.sh"
echo ""
echo "    # Stop services, keep data:"
echo "    docker compose -f Renovate/docker/docker-compose.yml down"
echo ""
echo "    # Stop services and delete all data (clean slate):"
echo "    docker compose -f Renovate/docker/docker-compose.yml down -v"
echo ""

