#!/usr/bin/env bash
# Measures startup time and idle memory for each application image.
#
# Why sequential startup?
#   Starting 10 containers simultaneously forces every JVM to compete for CPU
#   cores during the most CPU-intensive phase: class loading and JIT warm-up.
#   In a fair comparison each image should have the machine to itself during
#   startup, just as it would in a real deployment.  Sequential startup ensures
#   that.
#
# Two startup columns:
#   STARTUP(log)  – Spring Boot's "Started … in X.XXX seconds"; precise
#                   internal measurement from main() to application context
#                   ready.  Unaffected by Docker / OS container init overhead.
#   STARTUP(wall) – milliseconds from "docker run" to the first successful
#                   HTTP 2xx on the health endpoint.  This is the number a
#                   load balancer or Kubernetes readiness probe experiences.
#
# Memory is sampled once after ALL containers are up and have been idle for
# a few seconds, so no container is penalised by being sampled mid-startup.
#
# Requirements: bash 4+, docker, curl, GNU date (available in WSL2 / Git Bash).
set -euo pipefail

source "$(dirname "$0")/../images.conf"

STARTUP_TIMEOUT=90   # max seconds to wait for one container to become ready
POLL_INTERVAL=0.1    # seconds between readiness polls (100 ms)
SETTLE_SLEEP=3       # seconds to let all containers idle before memory snapshot
ENDPOINT="/hello"
PREFIX="hello-conference"

# Derive tags from APP_IMAGES (strip "hello-conference:" prefix)
TAGS=()
for IMG in "${APP_IMAGES[@]}"; do
    TAGS+=("${IMG#hello-conference:}")
done

PORTS=(8081 8082 8083 8088 8090 8091 8092 8084 8085 8086 8087)

# Extra docker run flags required by specific images.
# crac-azul-distroless-base restores a CRIU checkpoint.  CAP_CHECKPOINT_RESTORE
# requires Linux kernel 5.9+ and a matching runc; --privileged is the portable fallback.
declare -A EXTRA_RUN_ARGS=(
    ["crac-azul-distroless-base"]="--privileged"
)

declare -A WALL_MS
declare -A WARMUP_STATUS

cleanup() {
    for TAG in "${TAGS[@]}"; do
        docker rm -f "measure-${TAG}" >/dev/null 2>&1 || true
    done
}
trap cleanup EXIT
cleanup   # remove any stale containers from a previous run

# ── Sequential startup + readiness polling ────────────────────
echo "Starting containers one at a time (sequential for fair startup timing) …"
echo ""
for i in "${!TAGS[@]}"; do
    TAG="${TAGS[$i]}"; PORT="${PORTS[$i]}"
    printf "  %-52s" "${PREFIX}:${TAG}"

    docker run -d ${EXTRA_RUN_ARGS[$TAG]:-} \
        --name "measure-${TAG}" -p "${PORT}:8080" "${PREFIX}:${TAG}" >/dev/null
    T0=$(date +%s%3N)   # milliseconds since epoch

    WARMUP_STATUS[$TAG]="TIMEOUT"
    while (( $(date +%s%3N) - T0 < STARTUP_TIMEOUT * 1000 )); do
        HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 \
            "http://localhost:${PORT}${ENDPOINT}" 2>/dev/null || echo "000")
        if [[ "${HTTP}" =~ ^2[0-9][0-9]$ ]]; then
            WALL_MS[$TAG]=$(( $(date +%s%3N) - T0 ))
            WARMUP_STATUS[$TAG]="OK"
            break
        fi
        sleep "${POLL_INTERVAL}"
    done

    if [[ "${WARMUP_STATUS[$TAG]}" == "OK" ]]; then
        printf "ready  (%d ms wall-clock)\n" "${WALL_MS[$TAG]}"
    else
        WALL_MS[$TAG]=0
        printf "⚠  did not respond within %ds\n" "${STARTUP_TIMEOUT}"
    fi
done

echo ""
printf "All containers up – settling %ds before memory snapshot …\n" "${SETTLE_SLEEP}"
sleep "${SETTLE_SLEEP}"

# ── Results ───────────────────────────────────────────────────
printf "\n%-52s  %-20s  %-8s  %-14s  %s\n" \
    "IMAGE" "MEMORY" "WARMUP" "STARTUP(log)" "STARTUP(wall)"
printf "%-52s  %-20s  %-8s  %-14s  %s\n" \
    "----------------------------------------------------" \
    "--------------------" "--------" "--------------" "-------------"

for i in "${!TAGS[@]}"; do
    TAG="${TAGS[$i]}"; NAME="measure-${TAG}"

    MEM=$(docker stats --no-stream --format "{{.MemUsage}}" "${NAME}" 2>/dev/null \
          || echo "N/A")

    # Spring Boot logs "Started XxxApplication in 1.234 seconds"
    RAW=$(docker logs "${NAME}" 2>&1 \
          | grep -oE "in [0-9]+\.[0-9]+ seconds" | tail -1 \
          | grep -oE "[0-9]+\.[0-9]+" || echo "")
    LOG_STARTUP="${RAW:+${RAW}s}"
    LOG_STARTUP="${LOG_STARTUP:-N/A}"

    if [[ "${WARMUP_STATUS[$TAG]:-TIMEOUT}" == "OK" ]]; then
        WALL_FMT="${WALL_MS[$TAG]} ms"
    else
        WALL_FMT="TIMEOUT"
    fi

    printf "%-52s  %-20s  %-8s  %-14s  %s\n" \
        "${PREFIX}:${TAG}" "${MEM}" "${WARMUP_STATUS[$TAG]:-TIMEOUT}" \
        "${LOG_STARTUP}" "${WALL_FMT}"
done
echo ""

