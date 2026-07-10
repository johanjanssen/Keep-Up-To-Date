#!/usr/bin/env bash
# run-demo.sh — Full end-to-end pipeline (port/TCP mode):
#   build → start app → exercise endpoints → dump coverage → generate report → stop app
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

JACOCO_VERSION="0.8.15"
JAR="$PROJECT_DIR/target/jacoco-demo-0.0.1-SNAPSHOT.jar"
AGENT_JAR="$HOME/.m2/repository/org/jacoco/org.jacoco.agent/${JACOCO_VERSION}/org.jacoco.agent-${JACOCO_VERSION}-runtime.jar"
JACOCO_PORT=6300
# Normalise to native paths so Java can resolve them on any OS
AGENT_JAR="$(cygpath -w "$AGENT_JAR" 2>/dev/null || echo "$AGENT_JAR")"

echo ""
echo "============================================================"
echo "  JaCoCo Port Demo — Full pipeline"
echo "============================================================"
echo ""

# 1. Build
bash "$SCRIPT_DIR/build.sh"

# 2. Start app in background
echo "-> Starting app with JaCoCo TCP agent (port $JACOCO_PORT) ..."
java "-javaagent:${AGENT_JAR}=output=tcpserver,port=${JACOCO_PORT},address=0.0.0.0,includes=com.example.*" \
    -jar "$JAR" &>"$PROJECT_DIR/target/app.log" &
APP_PID=$!
echo "   PID: $APP_PID  |  log: target/app.log"

# 3. Wait for app to be ready
echo "   Waiting for app to start ..."
APP_READY=false
for i in $(seq 1 30); do
    if curl -sf "http://localhost:8080/hello" -o /dev/null 2>/dev/null; then
        APP_READY=true; break
    fi
    sleep 1
done
if ! $APP_READY; then
    echo "ERROR: App did not start within 30 s. Check target/app.log"
    kill "$APP_PID" 2>/dev/null || true
    exit 1
fi
echo "   App is ready."
echo ""

# 4. Exercise endpoints
bash "$SCRIPT_DIR/exercise-endpoints.sh"

# 5. Dump coverage over TCP
bash "$SCRIPT_DIR/dump-coverage.sh"

# 6. Generate report
bash "$SCRIPT_DIR/generate-report.sh"

# 7. Stop app
echo "-> Stopping app (PID $APP_PID) ..."
kill "$APP_PID" 2>/dev/null || true
wait "$APP_PID" 2>/dev/null || true
echo "OK  Pipeline complete."
echo ""
