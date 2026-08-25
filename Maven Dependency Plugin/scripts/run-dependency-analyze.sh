#!/usr/bin/env bash
# run-dependency-analyze.sh — Run the Maven Dependency Plugin's `analyze` goal
# against the demo project.
#
# No plugin configuration in pom.xml is required to run the goal itself — it's
# invoked on-the-fly via its full Maven coordinates, straight from the compiled
# classes in target/classes and target/test-classes. (pom.xml DOES carry a small
# <usedDependencies>/<ignoredUsedUndeclaredDependencies> block, but only to
# silence noise from the Spring Boot starter POMs — see the comment on that
# <plugin> entry. It does nothing to hide the three findings this demo is about.)
#
# Usage (run from the "Maven Dependency Plugin/" directory):
#   bash scripts/run-dependency-analyze.sh              report only — list findings, build stays green
#   STRICT=true bash scripts/run-dependency-analyze.sh  fail the build on any finding (opt-in CI gate)
#
# ── What it checks ────────────────────────────────────────────────────────
#
#  Goal: org.apache.maven.plugins:maven-dependency-plugin:analyze
#
#  Compares two views of this project's dependencies:
#    - what's DECLARED in pom.xml
#    - what's actually REFERENCED in the compiled bytecode (target/classes,
#      target/test-classes) — i.e. which dependency's classes does a
#      `import`/direct type use actually resolve to
#
#  and reports the mismatches. This demo's pom.xml declares three dependencies
#  that are flagged "Unused declared dependencies":
#
#    org.apache.commons:commons-lang3  — genuinely unused, never imported anywhere → delete it
#    com.google.guava:guava            — genuinely unused, never imported anywhere → delete it
#    com.h2database:h2                 — FALSE POSITIVE: DatabaseController needs it at
#                                         runtime (see src/.../DatabaseController.java), but it's
#                                         only ever reached through java.sql.DriverManager +
#                                         the JDBC 4 ServiceLoader mechanism, never a direct
#                                         org.h2.* reference — so the bytecode scan can't see it
#
#  Unlike the Old GroupIds Alerter demo's plugin, `analyze`'s failOnWarning
#  defaults to false — it's advisory out of the box, not a CI gate. STRICT=true
#  below opts into the gate real teams normally add on top (-DfailOnWarning=true),
#  it does not reproduce a plugin default.
#
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
MVNW="$ROOT_DIR/mvnw"

# Pinned to the latest release on Maven Central at the time of writing:
# https://search.maven.org/artifact/org.apache.maven.plugins/maven-dependency-plugin
PLUGIN_VERSION="3.11.0"

STRICT="${STRICT:-false}"

echo ""
echo "============================================================"
echo "  Maven Dependency Plugin Demo - Run Analyze"
echo "============================================================"
echo ""

if [ ! -f "$MVNW" ]; then
    echo "ERROR: Maven wrapper not found at $MVNW"
    exit 1
fi

if [ "$STRICT" = "true" ]; then
    echo "  STRICT: failOnWarning=true (opt-in CI gate) — build FAILS if any finding remains."
    FAIL_ON_WARNING="true"
else
    echo "  REPORT: failOnWarning=false (the goal's actual default) — findings are listed, build stays green."
    FAIL_ON_WARNING="false"
fi
echo ""
echo "  Plugin : org.apache.maven.plugins:maven-dependency-plugin:${PLUGIN_VERSION}"
echo "  Goal   : analyze"
echo ""
echo "------------------------------------------------------------"
echo ""

# analyze reads compiled bytecode, so test-compile has to run first — analyze
# itself doesn't compile anything, it only inspects target/classes and
# target/test-classes for the classes each dependency's jar actually contributes.
"$MVNW" \
    -f "$PROJECT_DIR/pom.xml" \
    test-compile \
    "org.apache.maven.plugins:maven-dependency-plugin:${PLUGIN_VERSION}:analyze" \
    "-DfailOnWarning=${FAIL_ON_WARNING}"

echo ""
echo "------------------------------------------------------------"
echo "OK  Analyze complete."
echo ""
echo "  Next steps:"
echo "    1. Review the 'Unused declared dependencies found' list above."
echo "    2. For each one, check whether the code actually needs it at runtime"
echo "       through reflection/SPI (like h2's JDBC driver here) before deleting —"
echo "       dependency:analyze only sees direct bytecode references."
echo "    3. Delete the genuinely dead ones from pom.xml; for a real reflection-only"
echo "       dependency, keep it declared and suppress the warning explicitly via"
echo "       <usedDependencies> in the plugin's <configuration> instead."
echo "    4. STRICT=true bash scripts/run-dependency-analyze.sh   # confirm the build now passes"
echo "------------------------------------------------------------"
echo ""
