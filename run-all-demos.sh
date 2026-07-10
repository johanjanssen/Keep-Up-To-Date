#!/usr/bin/env bash
# run-all-demos.sh — Exercise every demo in the repository to verify the full setup.
#
# ⚠  This takes a LONG time (native image builds alone can take 20+ minutes each).
#
# Prerequisites: Docker, Java 25, jq, curl, git
#
# Steps:
#   1. Build all Docker images          (Build Docker Images/)
#   2. Measure image sizes              (Build Docker Images/)
#   3. Measure startup & memory         (Build Docker Images/)
#   4. Grype — scan a single image      (Grype/)
#   5. Trivy — scan a single image      (Trivy/)
#   6. OWASP DC — scan dependencies     (OWASP Dependency Check/)
#   7. Compare all scan results         (Compare Security Scans/)
#   8. Testcontainers integration tests (Testcontainers/)
#   9. JaCoCo port-based demo           (Jacoco/)
#  10. JaCoCo file-based demo           (Jacoco/)
#  11. OpenRewrite dry-run              (OpenRewrite/)
#  12. Renovate demo                    (Renovate/) — optional, requires git
#
# Usage:
#   bash run-all-demos.sh                     # run all steps
#   SKIP_RENOVATE=true bash run-all-demos.sh  # skip Renovate (needs Gitea + Jenkins)
#   SKIP_BUILD=true bash run-all-demos.sh     # skip Docker image builds (reuse existing)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SKIP_BUILD="${SKIP_BUILD:-false}"
SKIP_RENOVATE="${SKIP_RENOVATE:-false}"

PASS=0
FAIL=0
SKIPPED=0
RESULTS=()

run_step() {
    local STEP_NUM="$1"
    local STEP_NAME="$2"
    shift 2

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    printf "║  Step %2s: %-49s ║\n" "$STEP_NUM" "$STEP_NAME"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    if "$@"; then
        echo ""
        echo "✅  Step ${STEP_NUM} passed: ${STEP_NAME}"
        PASS=$((PASS + 1))
        RESULTS+=("✅  ${STEP_NUM}. ${STEP_NAME}")
    else
        echo ""
        echo "❌  Step ${STEP_NUM} FAILED: ${STEP_NAME}"
        FAIL=$((FAIL + 1))
        RESULTS+=("❌  ${STEP_NUM}. ${STEP_NAME}")
    fi
}

skip_step() {
    local STEP_NUM="$1"
    local STEP_NAME="$2"
    echo ""
    echo "⏭   Step ${STEP_NUM} skipped: ${STEP_NAME}"
    SKIPPED=$((SKIPPED + 1))
    RESULTS+=("⏭   ${STEP_NUM}. ${STEP_NAME} (skipped)")
}

# ── Prerequisites ─────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   Keep Up To Date — Full Demo Run                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

for TOOL in docker java jq curl; do
    if ! command -v "$TOOL" &>/dev/null; then
        echo "❌  Required tool not found: $TOOL"
        exit 1
    fi
done
echo "  Prerequisites OK: docker, java, jq, curl"

if ! docker info >/dev/null 2>&1; then
    echo "❌  Docker is not running. Please start Docker Desktop and retry."
    exit 1
fi
echo "  Docker daemon: running"
echo ""

# ══════════════════════════════════════════════════════════════════════════════
# BUILD
# ══════════════════════════════════════════════════════════════════════════════

if [ "$SKIP_BUILD" = "true" ]; then
    skip_step 1 "Build all Docker images"
else
    run_step 1 "Build all Docker images" \
        bash "$ROOT_DIR/Build Docker Images/build-all-images.sh"
fi

# ══════════════════════════════════════════════════════════════════════════════
# MEASURE
# ══════════════════════════════════════════════════════════════════════════════

run_step 2 "Measure image sizes" \
    bash "$ROOT_DIR/Build Docker Images/measure-images.sh"

run_step 3 "Measure startup & memory" \
    bash "$ROOT_DIR/Build Docker Images/measure-performance.sh"

# ══════════════════════════════════════════════════════════════════════════════
# SECURITY SCANNING
# ══════════════════════════════════════════════════════════════════════════════

run_step 4 "Grype — update DB + scan single image" \
    bash -c "bash '${ROOT_DIR}/Grype/scripts/update-db.sh' && bash '${ROOT_DIR}/Grype/scripts/scan-image.sh' eclipse-temurin:25-jre"

run_step 5 "Trivy — update DB + scan single image" \
    bash -c "bash '${ROOT_DIR}/Trivy/scripts/update-db.sh' && bash '${ROOT_DIR}/Trivy/scripts/scan-image.sh' eclipse-temurin:25-jre"

# Note: run-check.sh may exit non-zero if failBuildOnCVSS is enabled in pom.xml.
# We wrap it in || true to handle both configurations.
run_step 6 "OWASP DC — start cache + scan dependencies" \
    bash -c "bash '${ROOT_DIR}/OWASP Dependency Check/scripts/start-cache.sh' && bash '${ROOT_DIR}/OWASP Dependency Check/scripts/update-cache.sh' && (bash '${ROOT_DIR}/OWASP Dependency Check/scripts/run-check.sh' || true)"

# run-all.sh scans ALL images with both Grype and Trivy (saving JSON results),
# runs OWASP DC, then produces side-by-side comparison tables.
# It calls run-check.sh internally which exits non-zero, so we tolerate that.
run_step 7 "Compare all security scan results" \
    bash -c "(bash '${ROOT_DIR}/Compare Security Scans/scripts/run-all.sh' || true)"

# ══════════════════════════════════════════════════════════════════════════════
# TESTING
# ══════════════════════════════════════════════════════════════════════════════

run_step 8 "Testcontainers integration tests" \
    bash "$ROOT_DIR/Testcontainers/scripts/run-tests.sh"

# ══════════════════════════════════════════════════════════════════════════════
# JACOCO
# ══════════════════════════════════════════════════════════════════════════════

run_step 9 "JaCoCo port-based demo" \
    bash "$ROOT_DIR/Jacoco/scripts/Retrieve Coverage From Port/run-demo.sh"

run_step 10 "JaCoCo file-based demo" \
    bash "$ROOT_DIR/Jacoco/scripts/Retrieve Coverage From File/run-demo.sh"

# ══════════════════════════════════════════════════════════════════════════════
# OPENREWRITE
# ══════════════════════════════════════════════════════════════════════════════

run_step 11 "OpenRewrite dry-run" \
    env DRY_RUN=true bash "$ROOT_DIR/OpenRewrite/scripts/run-openrewrite.sh"

# ══════════════════════════════════════════════════════════════════════════════
# RENOVATE
# ══════════════════════════════════════════════════════════════════════════════

if [ "$SKIP_RENOVATE" = "true" ]; then
    skip_step 12 "Renovate demo (Gitea + Jenkins)"
else
    run_step 12 "Renovate demo (Gitea + Jenkins)" \
        env DRY_RUN=true bash "$ROOT_DIR/Renovate/scripts/demo.sh"
fi

# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

echo ""
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   Summary                                                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
for R in "${RESULTS[@]}"; do
    echo "  $R"
done
echo ""
echo "  Passed: $PASS   Failed: $FAIL   Skipped: $SKIPPED"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo "⚠  Some steps failed — check the output above for details."
    exit 1
else
    echo "✅  All steps completed successfully."
fi

