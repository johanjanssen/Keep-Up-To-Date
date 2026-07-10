#!/usr/bin/env bash
# run-check.sh — Run OWASP Dependency Check against the vulnerable demo project.
#
# Expected result: BUILD FAILURE — 2+ HIGH/CRITICAL CVEs found.
#
# Usage:
#   bash scripts/run-check.sh           # normal scan
#   bash scripts/run-check.sh --purge   # wipe the local H2 database first, then scan
#                                       # use --purge when you see schema errors such as:
#                                       # "Value too long for column URL CHARACTER VARYING(1000)"
#
# NVD cache (required)
# ────────────────────
# This script requires the local NVD cache container to be running on port 7070.
# Start it first (one-time setup, then it persists across restarts):
#   bash scripts/start-cache.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
MVNW="$ROOT_DIR/mvnw"
VULN_APP_DIR="$ROOT_DIR/Vulnerable Application"

CACHE_PORT=7070
CACHE_URL="http://localhost:${CACHE_PORT}/"
PURGE=false
[[ "${1:-}" == "--purge" ]] && PURGE=true

echo ""
echo "============================================================"
echo "  OWASP Dependency Check — Scanning vulnerable dependencies"
echo "============================================================"
echo ""
echo "  Known CVEs in this project:"
echo "    log4j-core 2.0          CVE-2021-44228 (Log4Shell)  CVSS 10.0"
echo "    jackson-databind 2.9.10  multiple deserialization CVEs"
echo ""

# ── Optionally purge the local H2 database ────────────────────────────────────
# Drops and recreates the dependency-check H2 database with the current schema.
# Required when upgrading the plugin or after "Value too long for column URL" errors.
if $PURGE; then
    echo "-> Purging local dependency-check H2 database ..."
    "$MVNW" -f "$VULN_APP_DIR/pom.xml" dependency-check:purge -q
    echo "OK  Database purged — will be recreated fresh on this scan."
    echo ""
fi

# ── Require local NVD cache ───────────────────────────────────────────────────
# cache.properties appearing at the root URL means data is fully loaded.
# Start the cache first with:  bash scripts/start-cache.sh
if ! curl -sf "${CACHE_URL}cache.properties" -o /dev/null 2>/dev/null; then
    echo "  ERROR: NVD cache is not ready at ${CACHE_URL}"
    echo ""
    echo "  Please start the cache first:"
    echo "    bash scripts/start-cache.sh"
    echo ""
    echo "  Wait for it to finish downloading the NVD database, then re-run this script."
    exit 1
fi

echo "  NVD cache : READY at ${CACHE_URL}  (no internet download needed)"
DATAFEED_ARGS=(-DnvdDatafeedUrl="${CACHE_URL}")

echo ""
echo "  Report will be at: $VULN_APP_DIR/target/dependency-check-report.html"
echo "------------------------------------------------------------"
echo ""

"$MVNW" -f "$VULN_APP_DIR/pom.xml" dependency-check:check "${DATAFEED_ARGS[@]}"

echo ""
echo "OK  Reports:"
echo "    HTML : file://$VULN_APP_DIR/target/dependency-check-report.html"
echo "    JSON : $VULN_APP_DIR/target/dependency-check-report.json"
echo "    SARIF: $VULN_APP_DIR/target/dependency-check-report.sarif"
