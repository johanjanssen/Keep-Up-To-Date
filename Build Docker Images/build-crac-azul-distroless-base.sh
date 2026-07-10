#!/usr/bin/env bash
# Builds hello-conference:crac-azul-distroless-base  (CRaC – Coordinated Restore at Checkpoint)
#
# Three steps (no BuildKit insecure mode required):
#   1. docker build   – produces hello-conference:crac-azul-pre
#                       (minimal jlink JRE + app JAR, no checkpoint yet)
#   2. docker run     – starts the app with --privileged so CRIU can write the
#                       checkpoint; Spring exits after context refresh
#   3. docker commit  – commits the stopped container (containing /crac-checkpoint)
#                       as hello-conference:crac-azul-distroless-base with the restore ENTRYPOINT
#
# --privileged is needed only in step 2 (build time).
# The final image only needs:
#   docker run --privileged ...
set -euo pipefail

# MSYS_NO_PATHCONV is set inline on individual docker commands (not globally)
# because Git Bash must still convert ${PROJECT_ROOT} for `docker build`, while
# Linux container-internal paths like /jre/bin/java must NOT be converted.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")/Vulnerable Application"

BASE_TAG="hello-conference:crac-azul-pre"
FINAL_TAG="hello-conference:crac-azul-distroless-base"
CONTAINER_NAME="crac-checkpoint-run"

# Remove any leftover checkpoint container from a previous run
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

# ── Step 1: Build base image (app + CRaC JDK, no checkpoint yet) ─────────────
echo "Step 1/3 – Building base image ${BASE_TAG} …"
docker build \
    --file  "${SCRIPT_DIR}/Dockerfile.crac-azul-distroless-base" \
    --tag   "${BASE_TAG}" \
    --pull=false \
    --progress=plain \
    "${PROJECT_ROOT}"

# ── Step 2: Run to create CRaC checkpoint ────────────────────────────────────
# --privileged gives CRIU the capabilities it needs to write /proc memory maps
# and freeze the process during checkpoint creation.  This is a build-time
# operation; the final image does not require --privileged at runtime.
#
# --entrypoint /jre/bin/java is REQUIRED.  Without it, Docker appends the
# arguments below to the ENTRYPOINT already baked into the image
# ("/jre/bin/java -jar app.jar"), so -XX:CRaCCheckpointTo and
# -Dspring.context.checkpoint are treated as Spring application arguments
# instead of JVM flags, and no checkpoint is ever triggered.
echo ""
echo "Step 2/3 – Creating CRaC checkpoint (--privileged required for CRIU) …"
echo "  Spring Boot will start, refresh the context, checkpoint, then exit."
MSYS_NO_PATHCONV=1 docker run \
    --name "${CONTAINER_NAME}" \
    --privileged \
    --entrypoint "/jre/bin/java" \
    "${BASE_TAG}" \
        -XX:CRaCCheckpointTo=/crac-checkpoint \
        -Dspring.context.checkpoint=onRefresh \
        -jar /app/app.jar \
    || true   # CRIU may exit the process with a non-zero code after checkpoint

EXIT_CODE=$(docker inspect "${CONTAINER_NAME}" \
    --format '{{.State.ExitCode}}' 2>/dev/null || echo "unknown")

# Exit codes 0 and 137 both indicate a successful checkpoint:
#   0   – JVM exited cleanly after Spring's System.exit(0) call
#   137 – CRIU sent SIGKILL to the process after the dump (also normal)
if [[ "${EXIT_CODE}" != "0" ]] && [[ "${EXIT_CODE}" != "137" ]]; then
    echo "❌ Unexpected exit code ${EXIT_CODE} – checkpoint likely failed"
    docker logs "${CONTAINER_NAME}" | tail -30
    docker rm "${CONTAINER_NAME}"
    exit 1
fi
echo "✅ Checkpoint complete (container exit code: ${EXIT_CODE})"

# ── Step 3: Commit stopped container as the final image ──────────────────────
# The stopped container's filesystem contains /crac-checkpoint.
# docker commit captures it and sets the restore ENTRYPOINT.
echo ""
echo "Step 3/3 – Committing checkpoint into ${FINAL_TAG} …"
MSYS_NO_PATHCONV=1 docker commit \
    --change='ENTRYPOINT ["/jre/bin/java", "-XX:CRaCRestoreFrom=/crac-checkpoint"]' \
    --message "CRaC checkpoint created by build-crac-azul-distroless-base.sh" \
    "${CONTAINER_NAME}" \
    "${FINAL_TAG}"

docker rm "${CONTAINER_NAME}"

echo ""
echo "✅  ${FINAL_TAG}"
echo ""
echo "Run with:  docker run --privileged -p 8080:8080 ${FINAL_TAG}"
