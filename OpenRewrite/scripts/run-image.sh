#!/usr/bin/env bash
# run-image.sh — Run the openrewrite-demo container.
#
# Prerequisites: build-image.sh must have been run first.
# Run from the OpenRewrite/ directory:
#   bash scripts/run-image.sh
set -euo pipefail

IMAGE_NAME="openrewrite-demo"
IMAGE_TAG="latest"
CONTAINER_NAME="openrewrite-demo"
HOST_PORT=8080

echo ""
echo "============================================================"
echo "  OpenRewrite Demo — Run Container"
echo "============================================================"
echo ""

# Remove any stale container with the same name
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

echo "-> Starting container $CONTAINER_NAME on port $HOST_PORT ..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p "${HOST_PORT}:8080" \
    "${IMAGE_NAME}:${IMAGE_TAG}"

echo ""
echo "------------------------------------------------------------"
echo "OK  Container running: $CONTAINER_NAME"
echo ""
echo "  App   : http://localhost:$HOST_PORT"
echo "  Greet : http://localhost:$HOST_PORT/api/greet?name=World"
echo "  Logs  : docker logs -f $CONTAINER_NAME"
echo "  Stop  : docker stop $CONTAINER_NAME"
echo "------------------------------------------------------------"
echo ""
