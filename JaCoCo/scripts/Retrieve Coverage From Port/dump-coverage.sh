#!/usr/bin/env bash
# dump-coverage.sh — Dump live coverage data from the running JaCoCo TCP agent.
# The app MUST be running (start-with-agent.sh) when this is called.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"

JACOCO_VERSION="0.8.15"
CLI_JAR="$HOME/.m2/repository/org/jacoco/org.jacoco.cli/${JACOCO_VERSION}/org.jacoco.cli-${JACOCO_VERSION}-nodeps.jar"
JACOCO_PORT=6300
EXEC_FILE="$PROJECT_DIR/target/jacoco-live.exec"

# Ensure CLI jar is present
if [[ ! -f "$CLI_JAR" ]]; then
    echo "-> JaCoCo CLI JAR not found — downloading via Maven ..."
    "$ROOT_DIR/mvnw" -f "$PROJECT_DIR/pom.xml" dependency:get \
        -Dartifact="org.jacoco:org.jacoco.cli:${JACOCO_VERSION}:jar:nodeps" -q
    echo "OK  JaCoCo CLI downloaded."
fi

if ! (bash -c ">/dev/tcp/localhost/${JACOCO_PORT}" 2>/dev/null); then
    echo "ERROR: Nothing listening on port ${JACOCO_PORT}."
    echo "       Start the app first: bash scripts/start-with-agent.sh"
    exit 1
fi

echo "-> Dumping coverage from TCP port $JACOCO_PORT ..."
mkdir -p "$(dirname "$EXEC_FILE")"

# Normalise to native paths so Java can resolve them on any OS
CLI_JAR="$(cygpath -w "$CLI_JAR" 2>/dev/null || echo "$CLI_JAR")"
EXEC_FILE="$(cygpath -w "$EXEC_FILE" 2>/dev/null || echo "$EXEC_FILE")"

java -jar "$CLI_JAR" dump \
    --address localhost --port "$JACOCO_PORT" \
    --destfile "$EXEC_FILE" --reset

echo "OK  Coverage saved: $EXEC_FILE"
echo "    Next: bash scripts/generate-report.sh"
