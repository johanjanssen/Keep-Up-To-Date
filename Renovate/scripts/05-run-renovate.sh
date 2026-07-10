#!/usr/bin/env bash
# 05-run-renovate.sh — Run the Renovate bot against the Gitea repository.
#
# Usage:
#   bash Renovate/scripts/05-run-renovate.sh          creates real PRs in Gitea
#   DRY_RUN=true bash Renovate/scripts/05-run-renovate.sh   log only, no PRs
#
# What Renovate will find and act on in this project:
#   • log4j-core 2.0  → IMMEDIATE security PR (CVE-2021-44228, CVSS 10.0)
#   • Spring Boot 4.1 → version update PR (grouped, scheduled weekends)
#   • eclipse-temurin Dockerfile digests → digest-pinned update PRs
#   • gcr.io/distroless digests          → digest-pinned update PRs
#   • gitea/gitea:1.22.3 in docker-compose.yml → version update PR
#
# Each PR triggers a Jenkins build (via Gitea webhook → Jenkins Multibranch
# Pipeline). The build result is posted back to the PR as a required check.
#
# Prerequisites: docker, and configured Gitea (run 01–04 first)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENOVATE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$RENOVATE_DIR")"
TOKEN_FILE="${RENOVATE_DIR}/.env"

ADMIN_USER="gitadmin"
REPO_NAME="hello-conference"
NETWORK="helloconference-dev-net"
# Renovate talks to Gitea over the Docker bridge network using the container hostname.
GITEA_INTERNAL_ENDPOINT="http://gitea:3000/"

# Default: create real PRs.  Set DRY_RUN=true to only log what would be done.
DRY_RUN="${DRY_RUN:-false}"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 5 — Run Renovate"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Read token ────────────────────────────────────────────────────────────────
if [ ! -f "${TOKEN_FILE}" ]; then
    echo "❌  Renovate/.env not found. Run: bash Renovate/scripts/02-setup-gitea.sh"
    exit 1
fi
TOKEN=$(grep '^GITEA_TOKEN=' "${TOKEN_FILE}" | cut -d'=' -f2-)

# ── Verify Docker network exists ──────────────────────────────────────────────
if ! docker network inspect "${NETWORK}" > /dev/null 2>&1; then
    echo "❌  Docker network '${NETWORK}' not found."
    echo "    Run: bash Renovate/scripts/01-start-gitea.sh"
    exit 1
fi

# ── Mode banner ───────────────────────────────────────────────────────────────
if [ "${DRY_RUN}" = "true" ]; then
    DRY_RUN_ARGS="--dry-run=lookup"
    echo "  ℹ️   DRY-RUN mode — Renovate logs proposed changes; no PRs created."
    echo "       Run without DRY_RUN=true to create real pull requests."
else
    DRY_RUN_ARGS=""
    echo "  🚀  LIVE mode — Renovate will create pull requests in Gitea."
    echo "       Each PR triggers a Jenkins build via Gitea webhook."
fi
echo ""
echo "  Scanning : ${ADMIN_USER}/${REPO_NAME}"
echo "  PRs      : http://localhost:3000/${ADMIN_USER}/${REPO_NAME}/pulls"
echo "  Jenkins  : http://localhost:8080/job/hello-conference/"
echo ""
echo "──────────────────────────────────────────────────────────────"
echo ""

# ── Run Renovate ──────────────────────────────────────────────────────────────
# All Renovate settings are passed as environment variables — no config.js
# file or volume mount needed.
#
# RENOVATE_GIT_URL=endpoint is the key fix: Gitea's API returns clone URLs
# with http://localhost:3000/ (its ROOT_URL), which is unreachable inside
# the container. "endpoint" tells Renovate to build the clone URL from
# RENOVATE_ENDPOINT (http://gitea:3000/) instead.
docker run --rm \
    --network "${NETWORK}" \
    --name renovate-runner \
    -e RENOVATE_TOKEN="${TOKEN}" \
    -e RENOVATE_PLATFORM="gitea" \
    -e RENOVATE_ENDPOINT="${GITEA_INTERNAL_ENDPOINT}" \
    -e RENOVATE_GIT_URL="endpoint" \
    -e RENOVATE_ONBOARDING="false" \
    -e RENOVATE_REQUIRE_CONFIG="optional" \
    -e RENOVATE_GIT_AUTHOR="Renovate Bot <renovate@example.com>" \
    -e RENOVATE_DEPENDENCY_DASHBOARD="false" \
    -e LOG_LEVEL="${LOG_LEVEL:-info}" \
    renovate/renovate:latest \
        ${DRY_RUN_ARGS} \
        "${ADMIN_USER}/${REPO_NAME}"

echo ""
echo "──────────────────────────────────────────────────────────────"
if [ "${DRY_RUN}" = "true" ]; then
    echo "✅  Dry run complete. Set DRY_RUN=false to create real PRs."
else
    echo "✅  Renovate finished."
    echo ""
    echo "  Pull requests : http://localhost:3000/${ADMIN_USER}/${REPO_NAME}/pulls"
    echo "  Jenkins builds: http://localhost:8080/job/hello-conference/"
    echo ""

    # ── Trigger Jenkins rescan ────────────────────────────────────────────────
    # Renovate just created PR branches in Gitea. Jenkins must rescan the repo
    # to discover them and start individual builds. Without this, Jenkins waits
    # up to 5 minutes for the periodic folder trigger.
    # (Webhooks may not have fired yet if the initial scan was still in progress
    # when the PRs were created.)
    if curl -sf "http://localhost:8080/api/json" \
            -u "admin:Admin1234!" > /dev/null 2>&1; then
        echo "→ Triggering Jenkins rescan to discover new PR branches …"
        RESCAN_JAR="$(mktemp /tmp/jenkins-rescan.XXXXXX)"
        RESCAN_JSON=$(curl -sf \
            -u "admin:Admin1234!" \
            -c "${RESCAN_JAR}" \
            "http://localhost:8080/crumbIssuer/api/json" 2>/dev/null || echo "{}")
        RESCAN_FIELD=$(echo "${RESCAN_JSON}" | grep -o '"crumbRequestField":"[^"]*"' | cut -d'"' -f4)
        RESCAN_CRUMB=$(echo "${RESCAN_JSON}" | grep -o '"crumb":"[^"]*"' | cut -d'"' -f4)
        curl -s -o /dev/null \
            -X POST "http://localhost:8080/job/hello-conference/build" \
            -u "admin:Admin1234!" \
            -b "${RESCAN_JAR}" \
            ${RESCAN_FIELD:+-H "${RESCAN_FIELD}: ${RESCAN_CRUMB}"} \
            && echo "   ✅  Rescan triggered — Jenkins will build each PR branch shortly." \
            || echo "   ⚠️   Rescan trigger failed (Jenkins may already be scanning)."
        rm -f "${RESCAN_JAR}"
        echo ""
    fi

    echo "  Expected PRs:"
    echo "    🔴 security  log4j-core 2.0 → latest  (CVE-2021-44228, CVSS 10.0)"
    echo "    🟡 update    Spring Boot 4.1 → latest  (grouped, see renovate.json)"
    echo "    🟢 docker    eclipse-temurin digest update"
    echo "    🟢 docker    gcr.io/distroless digest update"
    echo "    🟢 docker    gitea/gitea:1.22.3 → latest"
    echo ""
    echo "  Each PR branch gets its own Jenkins build."
    echo "  Build status (✅ / ❌) appears in the Gitea PR checks section."
fi
echo "──────────────────────────────────────────────────────────────"
echo ""

