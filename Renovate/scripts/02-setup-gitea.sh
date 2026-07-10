#!/usr/bin/env bash
# 02-setup-gitea.sh — Create the Gitea admin user, repository, and API token.
#
# Usage:
#   bash Renovate/scripts/02-setup-gitea.sh
#
# What it does:
#   1. Creates admin user "gitadmin" via the Gitea CLI inside the container.
#   2. Creates the "hello-conference" repository via the Gitea REST API.
#   3. Creates a personal access token named "renovate-token".
#   4. Saves the token to:
#        Renovate/.env                   GITEA_TOKEN=<value>  (read by scripts 03–05)
#
# Idempotent: safe to re-run. Existing user/repo is detected and skipped.
# The API token is always revoked and re-created so the token files are fresh.
#
# Prerequisites: Docker with a running Gitea container (run 01-start-gitea.sh first)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENOVATE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$RENOVATE_DIR")"

GITEA_URL="http://localhost:3000"
ADMIN_USER="gitadmin"
ADMIN_PASS="Admin1234!"
ADMIN_EMAIL="admin@example.com"
REPO_NAME="hello-conference"
TOKEN_NAME="renovate-token"

TOKEN_FILE="${RENOVATE_DIR}/.env"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 2 — Configure Gitea"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Verify Gitea is reachable ─────────────────────────────────────────────────
if ! curl -sf "${GITEA_URL}/" > /dev/null 2>&1; then
    echo "❌  Gitea is not reachable at ${GITEA_URL}."
    echo "    Run: bash Renovate/scripts/01-start-gitea.sh"
    exit 1
fi

# ── 1. Create admin user ──────────────────────────────────────────────────────
# IMPORTANT: docker exec must run as the 'git' user (UID 1000) inside the
# Gitea container. Running as root causes Gitea to exit with:
#   "Gitea is not supposed to be run as root."
echo "→ Creating admin user '${ADMIN_USER}' …"
docker exec --user git gitea gitea admin user create \
    --username "${ADMIN_USER}" \
    --password "${ADMIN_PASS}" \
    --email    "${ADMIN_EMAIL}" \
    --admin \
    --must-change-password=false 2>&1 \
    | sed 's/^/   /' \
    || true   # non-zero exit = user already exists; verified below

# Verify the credentials actually work before proceeding.
# This catches the case where creation silently failed for any other reason.
echo ""
echo "→ Verifying admin credentials …"
if ! curl -sf "${GITEA_URL}/api/v1/user" \
        -u "${ADMIN_USER}:${ADMIN_PASS}" > /dev/null 2>&1; then
    echo "   ❌  Admin credentials do not work."
    echo "       The user may not have been created. Check Gitea logs:"
    echo "       docker compose -f Renovate/docker/docker-compose.yml logs gitea"
    exit 1
fi
echo "   ✅  Credentials verified."
echo ""

# ── 2. Create repository ──────────────────────────────────────────────────────
echo "→ Creating repository '${ADMIN_USER}/${REPO_NAME}' …"
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${GITEA_URL}/api/v1/user/repos" \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\":           \"${REPO_NAME}\",
        \"description\":    \"Spring Boot 4.1 — Never Fall Behind conference demo\",
        \"private\":        false,
        \"auto_init\":      false,
        \"default_branch\": \"main\"
    }")

case "${HTTP_STATUS}" in
    201) echo "   ✅  Repository created: ${GITEA_URL}/${ADMIN_USER}/${REPO_NAME}" ;;
    409) echo "   ℹ️   Repository already exists — continuing." ;;
    *)   echo "   ❌  Unexpected HTTP ${HTTP_STATUS} from Gitea API." ; exit 1 ;;
esac
echo ""

# ── 3. Create Renovate + Jenkins API token ────────────────────────────────────
echo "→ Creating API token '${TOKEN_NAME}' …"
# Always delete first so re-runs are idempotent and the token file stays valid.
curl -s -o /dev/null \
    -X DELETE "${GITEA_URL}/api/v1/users/${ADMIN_USER}/tokens/${TOKEN_NAME}" \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    || true

TOKEN_JSON=$(curl -s \
    -X POST "${GITEA_URL}/api/v1/users/${ADMIN_USER}/tokens" \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"${TOKEN_NAME}\",
        \"scopes\": [
            \"read:issue\",  \"write:issue\",
            \"read:repository\", \"write:repository\",
            \"read:user\",   \"write:user\",
            \"read:organization\",
            \"read:notification\",
            \"read:misc\",   \"write:misc\"
        ]
    }")

if command -v jq &>/dev/null; then
    TOKEN=$(echo "${TOKEN_JSON}" | jq -r '.sha1 // empty')
else
    TOKEN=$(echo "${TOKEN_JSON}" | grep -o '"sha1":"[^"]*"' | cut -d'"' -f4)
fi

if [ -z "${TOKEN}" ]; then
    echo "   ❌  Could not extract token from response: ${TOKEN_JSON}"
    exit 1
fi

# Write token to Renovate/.env.
# All scripts (03–05) read GITEA_TOKEN from this file.
printf 'GITEA_TOKEN=%s\n' "${TOKEN}" > "${TOKEN_FILE}"
chmod 600 "${TOKEN_FILE}"
echo "   ✅  Token saved to Renovate/.env (GITEA_TOKEN)"
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "──────────────────────────────────────────────────────────────"
echo "  Gitea UI    : ${GITEA_URL}"
echo "  Login       : ${ADMIN_USER}  /  ${ADMIN_PASS}"
echo "  Repository  : ${GITEA_URL}/${ADMIN_USER}/${REPO_NAME}"
echo "──────────────────────────────────────────────────────────────"
echo ""
echo "   Next step: bash Renovate/scripts/03-push-code.sh"
echo ""

