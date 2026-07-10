#!/usr/bin/env bash
# start-with-agent.sh — Start the JAR with the JaCoCo file-based agent.
# The agent writes coverage data to target/jacoco.exec when the JVM exits (Ctrl+C).
# Build the JAR first: bash scripts/build.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
JACOCO_VERSION="0.8.15"
JAR="$PROJECT_DIR/target/jacoco-demo-0.0.1-SNAPSHOT.jar"
AGENT_JAR="$HOME/.m2/repository/org/jacoco/org.jacoco.agent/${JACOCO_VERSION}/org.jacoco.agent-${JACOCO_VERSION}-runtime.jar"
EXEC_FILE="$PROJECT_DIR/target/jacoco.exec"
if [[ ! -f "$JAR" ]]; then
    echo "ERROR: JAR not found — run bash scripts/build.sh first."
    exit 1
fi
if [[ ! -f "$AGENT_JAR" ]]; then
    echo "-> JaCoCo agent JAR not found — downloading via Maven ..."
    ROOT_DIR="$(dirname "$PROJECT_DIR")"
    "$ROOT_DIR/mvnw" dependency:get \
        -Dartifact="org.jacoco:org.jacoco.agent:${JACOCO_VERSION}:jar:runtime" -q
    echo "OK  JaCoCo agent downloaded."
fi
# Normalise to native paths so Java can resolve them on any OS
AGENT_JAR="$(cygpath -w "$AGENT_JAR" 2>/dev/null || echo "$AGENT_JAR")"
EXEC_FILE="$(cygpath -w "$EXEC_FILE" 2>/dev/null || echo "$EXEC_FILE")"
echo ""
echo "============================================================"
echo "  JaCoCo File Demo — Start with file agent"
echo "============================================================"
echo ""
echo "   App   : http://localhost:8080"
echo "   Output: $EXEC_FILE  (written on JVM exit)"
echo ""
echo "   In another terminal:"
echo "     bash scripts/exercise-endpoints.sh"
echo ""
echo "   Then press Ctrl+C here — JaCoCo flushes coverage to file."
echo "   Then:  bash scripts/generate-report.sh"
echo "   Or run everything at once: bash scripts/run-demo.sh"
echo ""
echo "   Press Ctrl+C to stop."
echo "------------------------------------------------------------"
echo ""
java "-javaagent:${AGENT_JAR}=destfile=${EXEC_FILE},output=file,append=false,includes=com.example.*" \
    -jar "$JAR"
