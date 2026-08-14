#!/usr/bin/env bash
# 06-export-prs.sh — Export every PR Renovate opened in Gitea to a JSON file,
# including each PR's real unified diff.
#
# Used to feed generate-html-report.py, which publishes a report to GitHub
# Pages. Because the Gitea container is torn down at the end of the CI job
# (it's an ephemeral demo instance, not a real forge), the report can't link
# back to a live PR — so this script captures everything needed to render
# each PR faithfully (title, labels, description, real diff) while Gitea is
# still up.
#
# Usage:
#   bash Renovate/scripts/06-export-prs.sh [output.json]
#
# Prerequisites: docker, jq, and a Renovate run against Gitea (run 01–05 first)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RENOVATE_DIR="$(dirname "$SCRIPT_DIR")"
TOKEN_FILE="${RENOVATE_DIR}/.env"
OUTPUT="${1:-${RENOVATE_DIR}/target/renovate-prs.json}"

GITEA_URL="http://localhost:3000"
ADMIN_USER="gitadmin"
REPO_NAME="hello-conference"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  Step 6 — Export pull requests"
echo "═══════════════════════════════════════════════════════════════"
echo ""

if [ ! -f "${TOKEN_FILE}" ]; then
    echo "❌  Renovate/.env not found. Run: bash Renovate/scripts/02-setup-gitea.sh"
    exit 1
fi
if ! command -v jq &>/dev/null; then
    echo "❌  jq is required. See https://jqlang.github.io/jq/download/"
    exit 1
fi
TOKEN=$(grep '^GITEA_TOKEN=' "${TOKEN_FILE}" | cut -d'=' -f2-)

mkdir -p "$(dirname "${OUTPUT}")"

echo "→ Fetching pull requests opened against ${ADMIN_USER}/${REPO_NAME} …"
PRS_JSON=$(curl -sf \
    -H "Authorization: token ${TOKEN}" \
    "${GITEA_URL}/api/v1/repos/${ADMIN_USER}/${REPO_NAME}/pulls?state=all&limit=50&sort=oldest")

COUNT=$(echo "${PRS_JSON}" | jq 'length')
echo "   ${COUNT} pull request(s) found."
echo ""

# Renovate PR bodies (changelog tables) and diffs (lockfile-style updates)
# can both grow past the kernel's argv size limit (ARG_MAX), so neither is
# ever passed to jq as a command-line argument below — each PR's body and
# diff are written to a temp file and read back with --rawfile instead.
# Entries are likewise appended one-per-line to a temp file and combined
# with a single `jq -s` slurp at the end, rather than re-passing the
# growing result array through --argjson on every loop iteration.
ENTRIES_FILE="$(mktemp)"
BODY_FILE="$(mktemp)"
DIFF_FILE="$(mktemp)"
trap 'rm -f "${ENTRIES_FILE}" "${BODY_FILE}" "${DIFF_FILE}"' EXIT

for ROW in $(echo "${PRS_JSON}" | jq -r '.[] | @base64'); do
    _jq() { echo "${ROW}" | base64 -d | jq -r "${1}"; }
    NUMBER=$(_jq '.number')
    TITLE=$(_jq '.title')
    BASE=$(_jq '.base.ref')
    HEAD=$(_jq '.head.ref')
    CREATED=$(_jq '.created_at')
    LABELS=$(_jq '[.labels[].name]')

    echo "   → PR #${NUMBER}: ${TITLE}"

    _jq '.body // ""' > "${BODY_FILE}"

    # Gitea supports GitHub-style ".diff" suffixes on the PR API endpoint.
    curl -sf \
        -H "Authorization: token ${TOKEN}" \
        "${GITEA_URL}/api/v1/repos/${ADMIN_USER}/${REPO_NAME}/pulls/${NUMBER}.diff" \
        > "${DIFF_FILE}" || : > "${DIFF_FILE}"

    jq -n \
        --argjson number "${NUMBER}" \
        --arg title "${TITLE}" \
        --rawfile body "${BODY_FILE}" \
        --arg base "${BASE}" \
        --arg head "${HEAD}" \
        --arg created "${CREATED}" \
        --argjson labels "${LABELS}" \
        --rawfile diff "${DIFF_FILE}" \
        '{number: $number, title: $title, body: $body, base: $base, head: $head,
          created_at: $created, labels: $labels, diff: $diff}' >> "${ENTRIES_FILE}"
done

jq -s '.' "${ENTRIES_FILE}" > "${OUTPUT}"
echo ""
echo "✅  Wrote ${COUNT} pull request(s) to ${OUTPUT}"
echo ""
