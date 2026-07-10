#!/usr/bin/env bash
# build.sh — Build the JaCoCo demo JAR with Maven (skipping tests).
# Run this once before starting the app with start-with-agent.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"

echo ""
echo "============================================================"
echo "  JaCoCo Demo — Build JAR"
echo "============================================================"
echo ""

echo "-> Building JAR with Maven ..."
"$ROOT_DIR/mvnw" -f "$PROJECT_DIR/pom.xml" clean package -DskipTests -q

echo ""
echo "OK  JAR built: $PROJECT_DIR/target/jacoco-demo-0.0.1-SNAPSHOT.jar"
echo "    Run: bash scripts/start-with-agent.sh"
echo ""

