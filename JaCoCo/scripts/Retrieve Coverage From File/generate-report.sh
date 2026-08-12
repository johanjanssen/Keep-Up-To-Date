#!/usr/bin/env bash
# generate-report.sh — Produce an HTML coverage report from target/jacoco.exec.
# Run AFTER stopping the app (Ctrl+C) so the JVM has flushed the exec file.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
JACOCO_VERSION="0.8.15"
CLI_JAR="$HOME/.m2/repository/org/jacoco/org.jacoco.cli/${JACOCO_VERSION}/org.jacoco.cli-${JACOCO_VERSION}-nodeps.jar"
EXEC_FILE="$PROJECT_DIR/target/jacoco.exec"
REPORT_DIR="$PROJECT_DIR/target/coverage-report"
CLASSFILES="$PROJECT_DIR/target/classes"
SOURCEFILES="$PROJECT_DIR/src/main/java"

# Ensure CLI jar is present
if [[ ! -f "$CLI_JAR" ]]; then
    echo "-> JaCoCo CLI JAR not found — downloading via Maven ..."
    "$ROOT_DIR/mvnw" -f "$PROJECT_DIR/pom.xml" dependency:get \
        -Dartifact="org.jacoco:org.jacoco.cli:${JACOCO_VERSION}:jar:nodeps" -q
    echo "OK  JaCoCo CLI downloaded."
fi

if [[ ! -f "$EXEC_FILE" ]]; then
    echo "ERROR: $EXEC_FILE not found."
    echo "       Stop the app first (Ctrl+C) so JaCoCo writes the exec file."
    exit 1
fi

# Normalise to native paths so Java can resolve them on any OS
CLI_JAR="$(cygpath -w "$CLI_JAR" 2>/dev/null || echo "$CLI_JAR")"
EXEC_FILE="$(cygpath -w "$EXEC_FILE" 2>/dev/null || echo "$EXEC_FILE")"
REPORT_DIR="$(cygpath -w "$REPORT_DIR" 2>/dev/null || echo "$REPORT_DIR")"
CLASSFILES="$(cygpath -w "$CLASSFILES" 2>/dev/null || echo "$CLASSFILES")"
SOURCEFILES="$(cygpath -w "$SOURCEFILES" 2>/dev/null || echo "$SOURCEFILES")"

echo "-> Generating HTML report from $EXEC_FILE ..."
mkdir -p "$REPORT_DIR"
java -jar "$CLI_JAR" report "$EXEC_FILE" \
    --classfiles "$CLASSFILES" \
    --sourcefiles "$SOURCEFILES" \
    --html        "$REPORT_DIR" \
    --name        "JaCoCo File Coverage Demo"
echo "OK  Report: file://$REPORT_DIR/index.html"
echo "    Look for HelloController.diagnostics() — RED (0% coverage)"
