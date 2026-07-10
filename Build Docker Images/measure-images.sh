#!/usr/bin/env bash
# Prints size, overhead vs base image, and installed-package count for every image.
set -euo pipefail

source "$(dirname "$0")/../images.conf"

IMAGES=("${ALL_IMAGES[@]}")

# Runtime base image for each hello-conference application image
# Use "scratch" for images built FROM scratch (base has 0 bytes → overhead = full size)
declare -A BASE_FOR=(
    ["hello-conference:jre-temurin"]="eclipse-temurin:25-jre"
    ["hello-conference:jlink-full-distroless-base"]="gcr.io/distroless/base-debian12"
    ["hello-conference:jlink-distroless-base"]="gcr.io/distroless/base-debian12"
    ["hello-conference:jlink-netty-distroless-base"]="gcr.io/distroless/base-debian12"
    ["hello-conference:jlink-cds-distroless-base"]="gcr.io/distroless/base-debian12"
    ["hello-conference:jlink-tuned-distroless-base"]="gcr.io/distroless/base-debian12"
    ["hello-conference:crac-azul-distroless-base"]="gcr.io/distroless/base-debian12"
    ["hello-conference:native-debian-slim"]="debian:12-slim"
    ["hello-conference:native-minimal-distroless-static"]="gcr.io/distroless/static-debian12"
    ["hello-conference:native-scratch"]="scratch"
    ["hello-conference:native-netty-scratch"]="scratch"
)

# ── Package counter ───────────────────────────────────────────
# All strategies run the package manager DIRECTLY (no shell wrapper, --entrypoint "").
# If the binary is not found the docker run exits non-zero; || true + the > 0 guard
# cause the function to fall through to the next strategy cleanly.
count_packages() {
    local IMG="$1"
    local COUNT

    # Debian / Ubuntu: dpkg-query outputs one line per installed package
    COUNT=$(docker run --rm --entrypoint "" "${IMG}" \
        dpkg-query -f 'x\n' -W 2>/dev/null | wc -l | tr -d ' ' || true)
    [[ "${COUNT}" =~ ^[0-9]+$ ]] && [[ "${COUNT}" -gt 0 ]] && { echo "${COUNT}"; return; }

    # AlmaLinux / RHEL / Fedora: rpm outputs one line per installed package
    COUNT=$(docker run --rm --entrypoint "" "${IMG}" \
        rpm -qa 2>/dev/null | wc -l | tr -d ' ' || true)
    [[ "${COUNT}" =~ ^[0-9]+$ ]] && [[ "${COUNT}" -gt 0 ]] && { echo "${COUNT}"; return; }

    # Distroless / no-shell: read dpkg metadata via docker cp (no running process needed).
    # Try the traditional single status file first, then the modern per-package status.d/.
    local CID
    CID=$(docker create "${IMG}" /FAKE 2>/dev/null || docker create "${IMG}" 2>/dev/null || true)
    if [[ -n "${CID}" ]]; then
        COUNT=$(docker cp "${CID}:/var/lib/dpkg/status" - 2>/dev/null \
            | tar xO 2>/dev/null | grep -c '^Package:' || true)
        if [[ ! "${COUNT}" =~ ^[0-9]+$ ]] || [[ "${COUNT}" -eq 0 ]]; then
            COUNT=$(docker cp "${CID}:/var/lib/dpkg/status.d" - 2>/dev/null \
                | tar xO 2>/dev/null | grep -c '^Package:' || true)
        fi
        docker rm -f "${CID}" >/dev/null 2>&1 || true
        [[ "${COUNT}" =~ ^[0-9]+$ ]] && [[ "${COUNT}" -gt 0 ]] && { echo "${COUNT}"; return; }
    fi

    echo "N/A"
}

# ── Output ────────────────────────────────────────────────────
printf "%-50s  %-12s  %-12s  %-18s  %s\n" "IMAGE" "IMAGE SIZE" "APP SIZE" "APP+RUNTIME SIZE" "PACKAGES"
printf "%-50s  %-12s  %-12s  %-18s  %s\n" \
    "--------------------------------------------------" "------------" "------------" "------------------" "--------"
for IMG in "${IMAGES[@]}"; do
    SIZE=$(docker images "${IMG}" --format "{{.Size}}")
    if [[ -z "${SIZE}" ]]; then
        printf "%-50s  %-12s  %-12s  %-18s  %s\n" "${IMG}" "NOT BUILT" "" "" "N/A"
        continue
    fi

    # Compute overhead for hello-conference images
    APP_SIZE=""
    APP_RUNTIME_SIZE=""
    BASE="${BASE_FOR[$IMG]:-}"
    if [[ -n "${BASE}" ]]; then
        APP_BYTES=$(docker inspect "${IMG}" --format '{{.Size}}' 2>/dev/null || echo 0)
        # scratch has no image to inspect; treat its size as 0 bytes
        if [[ "${BASE}" == "scratch" ]]; then
            BASE_BYTES=0
        else
            BASE_BYTES=$(docker inspect "${BASE}" --format '{{.Size}}' 2>/dev/null || echo 0)
        fi
        if [[ "${APP_BYTES}" -gt 0 ]]; then
            OVERHEAD=$(awk "BEGIN { printf \"+%.1f MB\", (${APP_BYTES}-${BASE_BYTES})/1048576 }")
            if [[ "${IMG}" == "hello-conference:jre-temurin" ]]; then
                APP_SIZE="${OVERHEAD}"
            else
                APP_RUNTIME_SIZE="${OVERHEAD}"
            fi
        fi
    fi

    PKGS=$(count_packages "${IMG}")
    printf "%-50s  %-12s  %-12s  %-18s  %s\n" "${IMG}" "${SIZE}" "${APP_SIZE}" "${APP_RUNTIME_SIZE}" "${PKGS}"
done
echo ""

