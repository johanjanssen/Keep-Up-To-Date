#!/usr/bin/env bash
# run-demo.sh — Full end-to-end pipeline (file mode):
#   build → start app → exercise endpoints → stop app → generate report
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

JACOCO_VERSION="0.8.15"
JAR="$PROJECT_DIR/target/jacoco-demo-0.0.1-SNAPSHOT.jar"
AGENT_JAR="$HOME/.m2/repository/org/jacoco/org.jacoco.agent/${JACOCO_VERSION}/org.jacoco.agent-${JACOCO_VERSION}-runtime.jar"
EXEC_FILE="$PROJECT_DIR/target/jacoco.exec"
# Normalise to native paths so Java can resolve them on any OS
AGENT_JAR="$(cygpath -w "$AGENT_JAR" 2>/dev/null || echo "$AGENT_JAR")"
EXEC_FILE="$(cygpath -w "$EXEC_FILE" 2>/dev/null || echo "$EXEC_FILE")"

echo ""
echo "============================================================"
echo "  JaCoCo File Demo — Full pipeline"
echo "============================================================"
echo ""

# 1. Build
bash "$SCRIPT_DIR/build.sh"

# 2. Start app in background with file-based agent
mkdir -p "$PROJECT_DIR/target"
echo "-> Starting app with JaCoCo file agent ..."
java "-javaagent:${AGENT_JAR}=destfile=${EXEC_FILE},output=file,append=false,includes=com.example.*" \
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

# 5. Stop the app gracefully — triggers shutdown hooks so JaCoCo flushes the exec file
echo "-> Stopping app gracefully — JaCoCo will flush to $EXEC_FILE ..."
curl -sf -X POST http://localhost:8080/actuator/shutdown -o /dev/null || kill "$APP_PID"
wait "$APP_PID" 2>/dev/null || true
echo "OK  App stopped. Exec file: $EXEC_FILE"
echo ""

# 6. Generate report
bash "$SCRIPT_DIR/generate-report.sh"

echo ""
echo "OK  Pipeline complete."
echo ""
