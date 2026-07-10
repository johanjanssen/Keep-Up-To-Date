#!/usr/bin/env bash
# build-image.sh — Build the openrewrite-demo Docker image.
#
# The Dockerfile uses a two-stage build:
#   Stage 1 (eclipse-temurin:21-jdk-alpine) — compiles the app with Maven
#   Stage 2 (eclipse-temurin:21-jre-alpine)  — minimal runtime image
#
# Run from the OpenRewrite/ directory:
#   bash scripts/build-image.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
IMAGE_NAME="openrewrite-demo"
IMAGE_TAG="latest"

echo ""
echo "============================================================"
echo "  OpenRewrite Demo — Build Docker Image"
echo "============================================================"
echo ""
echo "  Project : $PROJECT_DIR"
echo "  Image   : $IMAGE_NAME:$IMAGE_TAG"
echo ""

# Copy Maven wrapper from root into OpenRewrite/ for the Docker build context.
# The Dockerfile COPY instruction expects mvnw and .mvn/ in the build context.
echo "-> Copying Maven wrapper from project root ..."
cp "$ROOT_DIR/mvnw"     "$PROJECT_DIR/mvnw"
cp "$ROOT_DIR/mvnw.cmd" "$PROJECT_DIR/mvnw.cmd"
cp -r "$ROOT_DIR/.mvn"  "$PROJECT_DIR/.mvn" 2>/dev/null || true
chmod +x "$PROJECT_DIR/mvnw"

echo "-> Building image (first run downloads layers, ~1 min) ..."
docker build \
    --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
    --file "$PROJECT_DIR/Dockerfile" \
    "$PROJECT_DIR"

echo ""
echo "------------------------------------------------------------"
echo "OK  Image built: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "  Run with:  bash scripts/run-image.sh"
echo "  Or:        docker run -p 8080:8080 ${IMAGE_NAME}:${IMAGE_TAG}"
echo "------------------------------------------------------------"
echo ""
