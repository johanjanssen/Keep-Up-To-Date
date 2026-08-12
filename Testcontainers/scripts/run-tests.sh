#!/usr/bin/env bash
# run-tests.sh — Run all Testcontainers integration tests.
#
# Requires: Docker running locally.
# On first run, Docker will pull:
#   postgres:16-alpine     (~80 MB)
#
# Usage (run from the Testcontainers/ directory):
#   bash scripts/run-tests.sh
#
# What is tested:
#   UserRepositoryIntegrationTest  — PostgreSQL CRUD (save, find, delete)
#
# Key demo features shown in the tests:
#   @ServiceConnection  — Spring Boot auto-wires Testcontainer host/port/credentials
#                         into DataSource — no @DynamicPropertySource needed
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
MVNW="$ROOT_DIR/mvnw"

echo ""
echo "============================================================"
echo "  Testcontainers Demo — Integration Tests"
echo "============================================================"
echo ""

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker Desktop and retry."
    exit 1
fi

"$MVNW" -f "$PROJECT_DIR/pom.xml" test
