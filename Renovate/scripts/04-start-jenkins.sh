#!/usr/bin/env bash
# 04-start-jenkins.sh — Build the Jenkins image, start the container, and
#                       configure the Multibranch Pipeline job.
#
# Usage:
#   bash Renovate/scripts/04-start-jenkins.sh
#
# What it does:
#   1. Builds the custom Jenkins Docker image (installs plugins, Docker CLI).
#      NOTE: first build takes 3–8 minutes while plugins are downloaded.
#   2. Starts the Jenkins container. The Gitea credential is configured via the
#      Jenkins REST API (see step below) using the token from Renovate/.env.
#   3. Waits until Jenkins is fully initialised.
#   4. Creates the "hello-conference" Multibranch Pipeline job via the REST API.
#   5. Triggers an initial branch scan — Jenkins discovers main, registers the
#      Gitea webhook, and builds the branch.
#
# Prerequisites: docker, curl, and token from 02-setup-gitea.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENOVATE_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${RENOVATE_DIR}/docker/docker-compose.yml"
TOKEN_FILE="${RENOVATE_DIR}/.env"
JOB_XML="${RENOVATE_DIR}/docker/jenkins/jobs/hello-conference.xml"

JENKINS_URL="http://localhost:8080"
JENKINS_USER="admin"
JENKINS_PASS="Admin1234!"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 4 — Start Jenkins"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ── Verify token is available ─────────────────────────────────────────────────
if [ ! -f "${TOKEN_FILE}" ]; then
    echo "❌  Renovate/.env not found. Run: bash Renovate/scripts/02-setup-gitea.sh"
    exit 1
fi

# ── Build Jenkins image and start container ───────────────────────────────────
echo "→ Building Jenkins image and starting container …"
echo "   (First build downloads ~30 plugins — may take 3–8 minutes)"
echo ""
docker compose -f "${COMPOSE_FILE}" up -d --build jenkins
echo ""

# ── Wait for Jenkins to be fully ready ───────────────────────────────────────
echo "⏳ Waiting for Jenkins at ${JENKINS_URL} …"
echo "   (Jenkins initialises plugins and applies JCasC — allow up to 3 minutes)"
MAX_RETRIES=36    # 36 × 5 s = 3 minutes
COUNT=0
until curl -sf -u "${JENKINS_USER}:${JENKINS_PASS}" \
        "${JENKINS_URL}/api/json" > /dev/null 2>&1; do
    COUNT=$((COUNT + 1))
    if [ "${COUNT}" -ge "${MAX_RETRIES}" ]; then
        echo ""
        echo "❌  Jenkins did not become ready after $((MAX_RETRIES * 5)) seconds."
        echo "    Check logs: docker compose -f Renovate/docker/docker-compose.yml logs jenkins"
        exit 1
    fi
    printf "   [%2d/%d] not ready — retrying in 5 s …\r" "${COUNT}" "${MAX_RETRIES}"
    sleep 5
done
echo ""
echo "   ✅  Jenkins is up."
echo ""

# ── Get CSRF crumb (with session cookie) ─────────────────────────────────────
# Jenkins ties each crumb to the session cookie issued alongside it.
# All subsequent POST requests must send the SAME cookie, or Jenkins
# rejects the crumb with HTTP 403 "No valid crumb was included in the request".
# Solution: save the session cookie to a jar on crumb fetch (-c) and
#           replay it on every following request (-b).
COOKIE_JAR="$(mktemp /tmp/jenkins-cookies.XXXXXX)"
trap 'rm -f "${COOKIE_JAR}"' EXIT

echo "→ Fetching CSRF crumb …"
CRUMB_JSON=$(curl -sf \
    -u "${JENKINS_USER}:${JENKINS_PASS}" \
    -c "${COOKIE_JAR}" \
    "${JENKINS_URL}/crumbIssuer/api/json" 2>/dev/null || echo "{}")

if command -v jq &>/dev/null; then
    CRUMB_FIELD=$(echo "${CRUMB_JSON}" | jq -r '.crumbRequestField // empty')
    CRUMB=$(echo "${CRUMB_JSON}"       | jq -r '.crumb // empty')
else
    CRUMB_FIELD=$(echo "${CRUMB_JSON}" | grep -o '"crumbRequestField":"[^"]*"' | cut -d'"' -f4)
    CRUMB=$(echo "${CRUMB_JSON}"       | grep -o '"crumb":"[^"]*"' | cut -d'"' -f4)
fi

if [ -z "${CRUMB_FIELD}" ] || [ -z "${CRUMB}" ]; then
    echo "   ⚠️   CSRF crumb not available — proceeding without it."
    CRUMB_HEADER=""
else
    CRUMB_HEADER="${CRUMB_FIELD}: ${CRUMB}"
    echo "   ✅  Crumb obtained."
fi
echo ""

# Helper: run a curl POST that shares the session cookie and crumb header.
jenkins_post() {
    curl -s \
        -u "${JENKINS_USER}:${JENKINS_PASS}" \
        -b "${COOKIE_JAR}" \
        ${CRUMB_HEADER:+-H "${CRUMB_HEADER}"} \
        "$@"
}

# ── Upsert the Gitea credential BEFORE creating the job ──────────────────────
# IMPORTANT: the credential must exist before the Multibranch Pipeline job is
# created, because job creation immediately triggers a branch scan. If the
# credential is set after job creation, the first scan runs with a missing
# credential → "CredentialId gitea-token could not be found".
#
# We use UsernamePasswordCredentials (gitadmin / Admin1234!) rather than a
# StringCredential token. This avoids JCasC env-var substitution edge cases
# and works reliably for git-clone, Gitea API calls, and webhook management.
echo "→ Upserting Gitea credential in Jenkins …"

CRED_XML='<com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>
  <scope>GLOBAL</scope>
  <id>gitea-token</id>
  <description>Gitea admin credentials — git clone + API + webhook management</description>
  <username>gitadmin</username>
  <password>Admin1234!</password>
</com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>'

# Try update first (JCasC created the credential at startup with a placeholder).
UPDATE_STATUS=$(echo "${CRED_XML}" | jenkins_post \
    -o /tmp/jenkins-cred.log \
    -w "%{http_code}" \
    -X POST "${JENKINS_URL}/credentials/store/system/domain/_/credential/gitea-token/config.xml" \
    -H "Content-Type: application/xml" \
    --data-binary @-)

if [ "${UPDATE_STATUS}" = "200" ]; then
    echo "   ✅  Credential updated."
else
    # Credential doesn't exist (e.g. JCasC failed) — create it fresh.
    CREATE_STATUS=$(echo "${CRED_XML}" | jenkins_post \
        -o /tmp/jenkins-cred.log \
        -w "%{http_code}" \
        -X POST "${JENKINS_URL}/credentials/store/system/domain/_/createCredentials" \
        -H "Content-Type: application/xml" \
        --data-binary @-)
    if [ "${CREATE_STATUS}" = "200" ] || [ "${CREATE_STATUS}" = "302" ]; then
        echo "   ✅  Credential created."
    else
        echo "   ❌  Could not set credential (HTTP ${CREATE_STATUS}): $(cat /tmp/jenkins-cred.log)"
        exit 1
    fi
fi
echo ""

# ── Create or update the Multibranch Pipeline job ────────────────────────────
echo "→ Creating Multibranch Pipeline job 'hello-conference' …"
HTTP_STATUS=$(jenkins_post \
    -o /tmp/jenkins-create-job.log \
    -w "%{http_code}" \
    -X POST "${JENKINS_URL}/createItem?name=hello-conference" \
    -H "Content-Type: application/xml" \
    --data-binary @"${JOB_XML}")

case "${HTTP_STATUS}" in
    200|201)
        echo "   ✅  Job created." ;;
    400)
        if grep -q "already exists" /tmp/jenkins-create-job.log 2>/dev/null; then
            # Job exists — update its config so changes to the XML are applied.
            echo "   ℹ️   Job exists — updating config …"
            UP=$(jenkins_post \
                -o /tmp/jenkins-update-job.log \
                -w "%{http_code}" \
                -X POST "${JENKINS_URL}/job/hello-conference/config.xml" \
                -H "Content-Type: application/xml" \
                --data-binary @"${JOB_XML}")
            [ "${UP}" = "200" ] \
                && echo "   ✅  Job config updated." \
                || echo "   ⚠️   Update returned HTTP ${UP} — job may be stale."
        else
            echo "   ❌  HTTP 400: $(cat /tmp/jenkins-create-job.log)"
            exit 1
        fi ;;
    *)
        echo "   ❌  Unexpected HTTP ${HTTP_STATUS}: $(cat /tmp/jenkins-create-job.log)"
        exit 1 ;;
esac
echo ""

# ── Register Gitea webhook → Jenkins ─────────────────────────────────────────
# JCasC has manageHooks:false so Jenkins will not auto-register the webhook.
# We register it here manually, using the Docker-internal Jenkins URL
# (http://jenkins:8080/) so that Gitea — running in the same Docker network —
# can deliver push and pull_request events directly to Jenkins.
#
# location.url in JCasC is http://localhost:8080/ (browser-friendly links in
# Gitea PR checks), which is a different URL from this webhook endpoint.
echo "→ Registering Gitea webhook …"
WEBHOOK_TARGET="http://jenkins:8080/gitea-webhook/post"

# Check whether the webhook is already present (idempotent re-runs).
EXISTING_HOOKS=$(curl -s \
    "http://localhost:3000/api/v1/repos/gitadmin/hello-conference/hooks" \
    -u "gitadmin:Admin1234!" 2>/dev/null || echo "[]")

if echo "${EXISTING_HOOKS}" | grep -q "jenkins:8080"; then
    echo "   ℹ️   Webhook already registered — skipping."
else
    HOOK_STATUS=$(curl -s -o /tmp/gitea-hook.log -w "%{http_code}" \
        -X POST "http://localhost:3000/api/v1/repos/gitadmin/hello-conference/hooks" \
        -u "gitadmin:Admin1234!" \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"gitea\",
            \"config\": {
                \"url\": \"${WEBHOOK_TARGET}\",
                \"content_type\": \"json\"
            },
            \"events\": [\"push\", \"pull_request\"],
            \"branch_filter\": \"*\",
            \"active\": true
        }")
    [ "${HOOK_STATUS}" = "201" ] \
        && echo "   ✅  Webhook registered: Gitea → ${WEBHOOK_TARGET}" \
        || echo "   ❌  Webhook registration failed (HTTP ${HOOK_STATUS}): $(cat /tmp/gitea-hook.log)"
fi
echo ""

# ── Trigger initial branch scan ───────────────────────────────────────────────
echo "→ Triggering initial branch scan …"
jenkins_post \
    -o /dev/null \
    -X POST "${JENKINS_URL}/job/hello-conference/build" \
    && echo "   ✅  Scan triggered." \
    || echo "   ℹ️   Scan trigger returned non-zero (scan may already be running)."
echo ""

# ── Final summary ─────────────────────────────────────────────────────────────
echo "──────────────────────────────────────────────────────────────"
echo "  Jenkins UI   : ${JENKINS_URL}"
echo "  Login        : ${JENKINS_USER}  /  ${JENKINS_PASS}"
echo "  Pipeline job : ${JENKINS_URL}/job/hello-conference/"
echo "  Build log    : ${JENKINS_URL}/job/hello-conference/job/main/"
echo "──────────────────────────────────────────────────────────────"
echo ""
echo "   Next step: bash Renovate/scripts/05-run-renovate.sh"
echo ""

