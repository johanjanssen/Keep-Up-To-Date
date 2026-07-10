#!/usr/bin/env bash
# compare-images.sh — Scan all base and app images with Trivy and print a severity table.
# Prerequisites: docker, jq
#   Run update-db.sh first to cache the vulnerability database.
#
# Usage:
#   bash scripts/compare-images.sh                     # print table to stdout
#   bash scripts/compare-images.sh --json-out <dir>    # also save JSON results to <dir>
#
# Tip: add '--ignore-unfixed' to the trivy command in scan_image() to hide
#      CVEs that have no available fix yet.
set -euo pipefail
export MSYS_NO_PATHCONV=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../../images.conf
source "$ROOT_DIR/images.conf"

TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.71.2}"
TRIVY_CACHE_VOL="${TRIVY_CACHE_VOL:-trivy-db}"
DOCKER_SOCK="/var/run/docker.sock"
JSON_OUT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --json-out) JSON_OUT="$2"; shift 2 ;;
        *) shift ;;
    esac
done

[[ -n "$JSON_OUT" ]] && mkdir -p "$JSON_OUT"

for TOOL in docker jq; do
    command -v "$TOOL" &>/dev/null || { echo "❌  '$TOOL' not found."; exit 1; }
done

ROW_FMT="%-50s  %8s  %8s  %8s  %8s  %8s  %8s\n"

print_header() {
    echo ""
    echo "$1"
    printf "$ROW_FMT" "IMAGE" "TOTAL" "CRITICAL" "HIGH" "MEDIUM" "LOW" "UNKNOWN"
    printf "$ROW_FMT" \
        "--------------------------------------------------" \
        "--------" "--------" "--------" "--------" "--------" "--------"
}

scan_image() {
    local IMG="$1"

    if ! docker image inspect "$IMG" &>/dev/null; then
        echo "  [DEBUG] docker image inspect failed for: $IMG" >&2
        printf "$ROW_FMT" "$IMG" "NOT BUILT" "" "" "" "" ""
        return
    fi

    # Write JSON to a temp file to avoid bash variable size limits on large images
    local JSON_TMP SCAN_ERR
    JSON_TMP=$(mktemp)
    SCAN_ERR=$(mktemp)
    if ! docker run --rm \
            -v "$DOCKER_SOCK:$DOCKER_SOCK" \
            -v "$TRIVY_CACHE_VOL:/root/.cache" \
            "$TRIVY_IMAGE" image \
            --skip-db-update --skip-java-db-update \
            --format json --quiet --scanners vuln \
            "$IMG" \
            >"$JSON_TMP" 2>"$SCAN_ERR"; then
        echo "  [DEBUG] Trivy scan failed for: $IMG (exit $?)" >&2
        echo "  [DEBUG] stderr: $(cat "$SCAN_ERR")" >&2
        rm -f "$JSON_TMP" "$SCAN_ERR"
        printf "$ROW_FMT" "$IMG" "SCAN ERR" "" "" "" "" ""
        return
    fi
    [[ -s "$SCAN_ERR" ]] && echo "  [DEBUG] Trivy warnings for $IMG: $(head -5 "$SCAN_ERR")" >&2
    rm -f "$SCAN_ERR"

    if [[ ! -s "$JSON_TMP" ]]; then
        echo "  [DEBUG] Trivy returned empty JSON for: $IMG" >&2
        rm -f "$JSON_TMP"
        printf "$ROW_FMT" "$IMG" "EMPTY" "" "" "" "" ""
        return
    fi

    if [[ -n "$JSON_OUT" ]]; then
        local FNAME
        FNAME=$(image_to_filename "$IMG")
        cp "$JSON_TMP" "$JSON_OUT/${FNAME}.json"
    fi

    local COUNTS
    COUNTS=$(cat "$JSON_TMP" | jq -r '
        [.Results[]? | .Vulnerabilities // [] | .[]] |
        [
            (length                                                    | tostring),
            (map(select(.Severity == "CRITICAL")) | length | tostring),
            (map(select(.Severity == "HIGH"))     | length | tostring),
            (map(select(.Severity == "MEDIUM"))   | length | tostring),
            (map(select(.Severity == "LOW"))      | length | tostring),
            (map(select(.Severity == "UNKNOWN"))  | length | tostring)
        ] | join(" ")
    ') || { rm -f "$JSON_TMP"; printf "$ROW_FMT" "$IMG" "PARSE ERR" "" "" "" "" ""; return; }

    rm -f "$JSON_TMP"

    # shellcheck disable=SC2162
    read -r TOTAL CRITICAL HIGH MEDIUM LOW UNKNOWN <<< "$COUNTS"
    printf "$ROW_FMT" "$IMG" "$TOTAL" "$CRITICAL" "$HIGH" "$MEDIUM" "$LOW" "$UNKNOWN"
}

echo ""
echo "============================================================"
echo "  Trivy — Base & Application Image CVE Comparison"
echo "============================================================"

print_header "── Base / runtime images ──"
for IMG in "${BASE_IMAGES[@]}"; do scan_image "$IMG"; done

print_header "── Application images (hello-conference) ──"
for IMG in "${APP_IMAGES[@]}"; do scan_image "$IMG"; done

echo ""
echo "✅  Scan complete."
