#!/usr/bin/env bash
# Prints size, overhead vs base image, and installed-package count for every image.
set -euo pipefail

source "$(dirname "$0")/../images.conf"

IMAGES=("${ALL_IMAGES[@]}")

# Runtime base image for each hello-conference application image
# Use "scratch" for images built FROM scratch (base has 0 bytes → overhead = full size).
# scratch-probe:local (see images.conf / Dockerfile.scratch-probe) shows up as its
# own row below with its real measured size/packages, so it's not referenced here.
declare -A BASE_FOR=(
    ["hello-conference:jre-temurin"]="eclipse-temurin:25-jre"
    ["hello-conference:jre-temurin-alpine"]="eclipse-temurin:25-jre-alpine"
    ["hello-conference:jlink-full-distroless-base-debian"]="gcr.io/distroless/base-debian13"
    ["hello-conference:jlink-distroless-base-debian"]="gcr.io/distroless/base-debian13"
    ["hello-conference:jlink-netty-distroless-base-debian"]="gcr.io/distroless/base-debian13"
    ["hello-conference:jlink-cds-distroless-base-debian"]="gcr.io/distroless/base-debian13"
    ["hello-conference:crac-azul-distroless-base-debian"]="gcr.io/distroless/base-debian13"
    ["hello-conference:native-debian-slim"]="debian:13-slim"
    ["hello-conference:native-minimal-distroless-static-debian"]="gcr.io/distroless/static-debian13"
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

    # A "FROM scratch" image with nothing else added has zero filesystem
    # layers — genuinely 0 packages, not merely "couldn't be determined".
    local LAYERS
    LAYERS=$(docker inspect "${IMG}" --format '{{len .RootFS.Layers}}' 2>/dev/null || true)
    [[ "${LAYERS}" == "0" ]] && { echo "0"; return; }

    # Debian / Ubuntu: dpkg-query outputs one line per installed package
    COUNT=$(docker run --rm --entrypoint "" "${IMG}" \
        dpkg-query -f 'x\n' -W 2>/dev/null | wc -l | tr -d ' ' || true)
    [[ "${COUNT}" =~ ^[0-9]+$ ]] && [[ "${COUNT}" -gt 0 ]] && { echo "${COUNT}"; return; }

    # AlmaLinux / RHEL / Fedora: rpm outputs one line per installed package
    COUNT=$(docker run --rm --entrypoint "" "${IMG}" \
        rpm -qa 2>/dev/null | wc -l | tr -d ' ' || true)
    [[ "${COUNT}" =~ ^[0-9]+$ ]] && [[ "${COUNT}" -gt 0 ]] && { echo "${COUNT}"; return; }

    # Alpine: apk info outputs one line per installed package
    COUNT=$(docker run --rm --entrypoint "" "${IMG}" \
        apk info 2>/dev/null | wc -l | tr -d ' ' || true)
    [[ "${COUNT}" =~ ^[0-9]+$ ]] && [[ "${COUNT}" -gt 0 ]] && { echo "${COUNT}"; return; }

    # Distroless / no-shell: read package-manager metadata via docker cp (no running process needed).
    # Try dpkg's traditional single status file first, then the modern per-package status.d/,
    # then Alpine's apk installed db.
    local CID
    CID=$(docker create "${IMG}" /FAKE 2>/dev/null || docker create "${IMG}" 2>/dev/null || true)
    if [[ -n "${CID}" ]]; then
        COUNT=$(docker cp "${CID}:/var/lib/dpkg/status" - 2>/dev/null \
            | tar xO 2>/dev/null | grep -c '^Package:' || true)
        if [[ ! "${COUNT}" =~ ^[0-9]+$ ]] || [[ "${COUNT}" -eq 0 ]]; then
            COUNT=$(docker cp "${CID}:/var/lib/dpkg/status.d" - 2>/dev/null \
                | tar xO 2>/dev/null | grep -c '^Package:' || true)
        fi
        # Alpine symlinks /lib -> /usr/lib, so its apk db lives under /lib/apk/db/
        # on the paths that matter here; BellSoft's Alpaquita Linux (musl base
        # images) doesn't carry that symlink and keeps its apk db directly under
        # /var/lib/apk/db/ instead, so both locations are tried.
        if [[ ! "${COUNT}" =~ ^[0-9]+$ ]] || [[ "${COUNT}" -eq 0 ]]; then
            COUNT=$(docker cp "${CID}:/lib/apk/db/installed" - 2>/dev/null \
                | tar xO 2>/dev/null | grep -c '^P:' || true)
        fi
        if [[ ! "${COUNT}" =~ ^[0-9]+$ ]] || [[ "${COUNT}" -eq 0 ]]; then
            COUNT=$(docker cp "${CID}:/var/lib/apk/db/installed" - 2>/dev/null \
                | tar xO 2>/dev/null | grep -c '^P:' || true)
        fi
        # AlmaLinux/RHEL "micro" variants and UBI-micro ship no rpm binary AND
        # use the modern SQLite-backed rpmdb (not the old Berkeley-DB file the
        # strategies above would grep), so those checks find nothing here even
        # though the database is very much present. Pull rpmdb.sqlite out
        # directly and count its Packages table with python3 (already a repo
        # dependency via generate-html-report.py). The file lives under
        # /usr/lib/sysimage/rpm/ on AlmaLinux but directly under /var/lib/rpm/
        # on UBI, so both locations are tried.
        if [[ ! "${COUNT}" =~ ^[0-9]+$ ]] || [[ "${COUNT}" -eq 0 ]]; then
            local TMP_DB
            TMP_DB=$(mktemp)
            if docker cp "${CID}:/usr/lib/sysimage/rpm/rpmdb.sqlite" "${TMP_DB}" 2>/dev/null \
                || docker cp "${CID}:/var/lib/rpm/rpmdb.sqlite" "${TMP_DB}" 2>/dev/null; then
                COUNT=$(python3 -c "
import sqlite3, sys
try:
    print(sqlite3.connect(sys.argv[1]).execute('SELECT COUNT(*) FROM Packages').fetchone()[0])
except Exception:
    print(0)
" "${TMP_DB}" 2>/dev/null || true)
            fi
            rm -f "${TMP_DB}"
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
        # NOTE: the `|| echo 0` fallback must sit OUTSIDE the command substitution.
        # `docker inspect` on an unresolvable ref (e.g. our "scratch" placeholder)
        # can still print a blank line to stdout before it errors out; with the
        # fallback nested inside $(...) that blank line and the "0" both get
        # captured, leaving a literal embedded newline in the variable (e.g.
        # "$'\n0'") that breaks the awk arithmetic below. Keeping `||` outside
        # the substitution discards any such partial stdout on failure.
        APP_BYTES=$(docker inspect "${IMG}" --format '{{.Size}}' 2>/dev/null) || APP_BYTES=0
        BASE_BYTES=$(docker inspect "${BASE}" --format '{{.Size}}' 2>/dev/null) || BASE_BYTES=0
        [[ "${APP_BYTES}" =~ ^[0-9]+$ ]] || APP_BYTES=0
        [[ "${BASE_BYTES}" =~ ^[0-9]+$ ]] || BASE_BYTES=0
        if [[ "${APP_BYTES}" -gt 0 ]]; then
            OVERHEAD=$(awk "BEGIN { printf \"+%.1f MB\", (${APP_BYTES}-${BASE_BYTES})/1048576 }")
            if [[ "${IMG}" == "hello-conference:jre-temurin" || "${IMG}" == "hello-conference:jre-temurin-alpine" ]]; then
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

