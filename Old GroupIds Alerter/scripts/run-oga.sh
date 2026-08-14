#!/usr/bin/env bash
# run-oga.sh — Run the Old GroupIds Alerter (OGA) Maven plugin against the demo project.
#
# No plugin configuration in pom.xml is required. oga-maven-plugin's `check`
# goal is invoked on-the-fly via its Maven coordinates, straight from Maven
# Central's community-maintained og-definitions.json — nothing is baked into
# the build file.
#
# Usage (run from the "Old GroupIds Alerter/" directory):
#   bash scripts/run-oga.sh              report only — list findings, build stays green
#   STRICT=true bash scripts/run-oga.sh  real-world default — build FAILS if any are found
#
# ── What it checks ────────────────────────────────────────────────────────
#
#  Goal: biz.lermitage.oga:oga-maven-plugin:check
#
#  Walks every <dependency> in the (effective) pom.xml and looks up its
#  groupId[:artifactId] against a community-maintained list of known
#  relocations — libraries that moved to a new Maven coordinate after the
#  original was abandoned, renamed, or absorbed elsewhere. This demo's
#  pom.xml declares four dependencies that match:
#
#    com.graphql-java:graphql-java-tools   -> com.graphql-java-kickstart:graphql-java-tools
#    javax.xml.bind:jaxb-api               -> jakarta.xml.bind:jakarta.xml.bind-api
#    javax.validation:validation-api       -> jakarta.validation:jakarta.validation-api
#    javax.activation:javax.activation-api -> jakarta.activation:jakarta.activation-api
#
#  By default (failOnError=true) the plugin FAILS the build the moment it
#  finds one — it's meant to be a CI gate, not just advice. This script runs
#  with -DfailOnError=false so the report step below can collect every
#  finding in one pass; STRICT=true reproduces the real default so you can
#  see the build actually break.
#
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
MVNW="$ROOT_DIR/mvnw"

# Pinned to the latest release on Maven Central at the time of writing:
# https://search.maven.org/artifact/biz.lermitage.oga/oga-maven-plugin
PLUGIN_VERSION="1.9.2"

STRICT="${STRICT:-false}"

echo ""
echo "============================================================"
echo "  Old GroupIds Alerter Demo - Run Check"
echo "============================================================"
echo ""

if [ ! -f "$MVNW" ]; then
    echo "ERROR: Maven wrapper not found at $MVNW"
    exit 1
fi

if [ "$STRICT" = "true" ]; then
    echo "  STRICT: failOnError=true (plugin default) — build FAILS if any old groupIds are found."
    FAIL_ON_ERROR="true"
else
    echo "  REPORT: failOnError=false — findings are listed, build stays green."
    FAIL_ON_ERROR="false"
fi
echo ""
echo "  Plugin : biz.lermitage.oga:oga-maven-plugin:${PLUGIN_VERSION}"
echo "  Goal   : check"
echo ""
echo "------------------------------------------------------------"
echo ""

"$MVNW" \
    -f "$PROJECT_DIR/pom.xml" \
    "biz.lermitage.oga:oga-maven-plugin:${PLUGIN_VERSION}:check" \
    "-DfailOnError=${FAIL_ON_ERROR}"

echo ""
echo "------------------------------------------------------------"
echo "OK  Check complete."
echo ""
echo "  Next steps:"
echo "    1. Review the [ERROR]/[WARNING] lines above for each old groupId."
echo "    2. Replace the flagged groupId (and artifactId, where it changed)"
echo "       in pom.xml, then re-resolve a compatible version for the new"
echo "       coordinate — versions do NOT carry over automatically."
echo "    3. STRICT=true bash scripts/run-oga.sh   # confirm the build now passes"
echo "------------------------------------------------------------"
echo ""
