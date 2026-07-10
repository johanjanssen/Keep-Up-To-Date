#!/usr/bin/env bash
# compare-images.sh — Scan all base and app images with Grype and print a severity table.
# Prerequisites: docker, jq
#   Run update-db.sh first to cache the vulnerability database.
#
# Usage:
#   bash scripts/compare-images.sh                     # print table to stdout
#   bash scripts/compare-images.sh --json-out <dir>    # also save JSON results to <dir>
set -euo pipefail
export MSYS_NO_PATHCONV=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../../images.conf
source "$ROOT_DIR/images.conf"

GRYPE_IMAGE="${GRYPE_IMAGE:-anchore/grype:latest}"
GRYPE_CACHE_VOL="${GRYPE_CACHE_VOL:-grype-db}"
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
        printf "$ROW_FMT" "$IMG" "NOT BUILT" "" "" "" "" ""
        return
    fi

    local JSON
    if ! JSON=$(docker run --rm \
            -v "$DOCKER_SOCK:$DOCKER_SOCK" \
            -v "$GRYPE_CACHE_VOL:/.cache/grype" \
            "$GRYPE_IMAGE" "$IMG" -o json 2>/dev/null); then
        printf "$ROW_FMT" "$IMG" "SCAN ERR" "" "" "" "" ""
        return
    fi

    if [[ -n "$JSON_OUT" ]]; then
        local FNAME
        FNAME=$(image_to_filename "$IMG")
        printf '%s' "$JSON" > "$JSON_OUT/${FNAME}.json"
    fi

    local COUNTS
    COUNTS=$(printf '%s' "$JSON" | jq -r '
        [.matches[]?] |
        [
            (length                                                              | tostring),
            (map(select(.vulnerability.severity == "Critical")) | length | tostring),
            (map(select(.vulnerability.severity == "High"))     | length | tostring),
            (map(select(.vulnerability.severity == "Medium"))   | length | tostring),
            (map(select(.vulnerability.severity == "Low"))      | length | tostring),
            (map(select(.vulnerability.severity | IN("Critical","High","Medium","Low") | not)) | length | tostring)
        ] | join(" ")
    ') || { printf "$ROW_FMT" "$IMG" "PARSE ERR" "" "" "" "" ""; return; }

    # shellcheck disable=SC2162
    read -r TOTAL CRITICAL HIGH MEDIUM LOW UNKNOWN <<< "$COUNTS"
    printf "$ROW_FMT" "$IMG" "$TOTAL" "$CRITICAL" "$HIGH" "$MEDIUM" "$LOW" "$UNKNOWN"
}

echo ""
echo "============================================================"
echo "  Grype — Base & Application Image CVE Comparison"
echo "============================================================"

print_header "── Base / runtime images ──"
for IMG in "${BASE_IMAGES[@]}"; do scan_image "$IMG"; done

print_header "── Application images (hello-conference) ──"
for IMG in "${APP_IMAGES[@]}"; do scan_image "$IMG"; done

echo ""
echo "✅  Scan complete."
