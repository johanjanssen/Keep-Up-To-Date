#!/usr/bin/env bash
# start-with-agent.sh — Start the JAR with the JaCoCo TCP agent.
# Coverage can be dumped from the live JVM at any time (no restart needed).
# Build the JAR first: bash scripts/build.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

JACOCO_VERSION="0.8.15"
JAR="$PROJECT_DIR/target/jacoco-demo-0.0.1-SNAPSHOT.jar"
AGENT_JAR="$HOME/.m2/repository/org/jacoco/org.jacoco.agent/${JACOCO_VERSION}/org.jacoco.agent-${JACOCO_VERSION}-runtime.jar"
JACOCO_PORT=6300

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

echo ""
echo "============================================================"
echo "  JaCoCo Port Demo — Start with TCP agent"
echo "============================================================"
echo ""
echo "   App  : http://localhost:8080"
echo "   Agent: TCP port $JACOCO_PORT  (keep this terminal open)"
echo ""
echo "   In another terminal:"
echo "     bash scripts/exercise-endpoints.sh"
echo "     bash scripts/dump-coverage.sh"
echo "     bash scripts/generate-report.sh"
echo "   Or run everything at once: bash scripts/run-demo.sh"
echo ""
echo "   Press Ctrl+C to stop."
echo "------------------------------------------------------------"
echo ""

java "-javaagent:${AGENT_JAR}=output=tcpserver,port=${JACOCO_PORT},address=0.0.0.0,includes=com.example.*" \
    -jar "$JAR"
