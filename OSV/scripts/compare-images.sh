#!/usr/bin/env bash
# compare-images.sh — Scan all base and app images with OSV-Scanner and print a severity table.
# Prerequisites: docker, jq
#
# Usage:
#   bash scripts/compare-images.sh                     # print table to stdout
#   bash scripts/compare-images.sh --json-out <dir>    # also save JSON results to <dir>
#
# Unlike Grype/Trivy, OSV-Scanner's own container image has no docker CLI in
# it, so it can't `docker save` an image itself the way `osv-scanner scan
# image <name>` does when run natively. We do the `docker save` on the host
# instead, per image, and hand OSV-Scanner the resulting archive with
# `scan image --archive` (see docs: "Scan from Exported Image Archive").
set -euo pipefail
export MSYS_NO_PATHCONV=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../../images.conf
source "$ROOT_DIR/images.conf"

OSV_IMAGE="${OSV_IMAGE:-ghcr.io/google/osv-scanner:latest}"
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

# Bucket an OSV vulnerability record into CRITICAL/HIGH/MEDIUM/LOW/UNKNOWN.
# Preference order:
#   1. database_specific.severity — set by GHSA-sourced advisories (npm, PyPI,
#      Maven, Go, RubyGems, crates.io, Packagist, Pub, NuGet, ...): a plain
#      LOW/MODERATE/HIGH/CRITICAL rating.
#   2. A vendor-rated entry in severity[] whose type isn't a bare CVSS vector
#      (e.g. {"type":"Ubuntu","score":"medium"}) — Ubuntu's OSV feed rates
#      severity this way; Debian's does not (see caveat in README).
#   3. UNKNOWN — genuinely no severity rating available from OSV for this
#      finding (common for OS-level Debian CVEs and Go stdlib advisories).
# We deliberately don't compute a score from raw CVSS vector strings (no CVSS
# calculator in jq) rather than guess.
JQ_SEVERITY='
def norm_sev($s):
    ($s | ascii_upcase) as $u
    | if   $u == "CRITICAL" then "CRITICAL"
      elif ($u == "HIGH" or $u == "IMPORTANT") then "HIGH"
      elif ($u == "MEDIUM" or $u == "MODERATE") then "MEDIUM"
      elif ($u == "LOW" or $u == "NEGLIGIBLE" or $u == "UNIMPORTANT") then "LOW"
      else "UNKNOWN"
      end;
def osv_severity:
    if (.database_specific.severity | type) == "string" and (.database_specific.severity | length) > 0 then
        norm_sev(.database_specific.severity)
    else
        ((.severity // []) | map(select(.type != "CVSS_V2" and .type != "CVSS_V3" and .type != "CVSS_V4")) | .[0].score) as $vs
        | if ($vs | type) == "string" and ($vs | length) > 0 then norm_sev($vs) else "UNKNOWN" end
    end;
'

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

    local TMP_DIR JSON_TMP SCAN_ERR
    TMP_DIR=$(mktemp -d)
    JSON_TMP=$(mktemp)
    SCAN_ERR=$(mktemp)

    if ! docker save "$IMG" -o "$TMP_DIR/image.tar" 2>"$SCAN_ERR"; then
        echo "  [DEBUG] docker save failed for: $IMG" >&2
        echo "  [DEBUG] stderr: $(cat "$SCAN_ERR")" >&2
        rm -rf "$TMP_DIR"; rm -f "$JSON_TMP" "$SCAN_ERR"
        printf "$ROW_FMT" "$IMG" "SAVE ERR" "" "" "" "" ""
        return
    fi

    # OSV-Scanner exits 1 when it finds vulnerabilities (not a scan failure) —
    # only treat exit codes above 1 as a real error.
    local RC=0
    docker run --rm -v "$TMP_DIR:/scan:ro" "$OSV_IMAGE" \
            scan image --archive /scan/image.tar --format json \
            >"$JSON_TMP" 2>"$SCAN_ERR" || RC=$?
    rm -rf "$TMP_DIR"
    if [[ $RC -gt 1 ]]; then
        echo "  [DEBUG] OSV-Scanner scan failed for: $IMG (exit $RC)" >&2
        echo "  [DEBUG] stderr: $(cat "$SCAN_ERR")" >&2
        rm -f "$JSON_TMP" "$SCAN_ERR"
        printf "$ROW_FMT" "$IMG" "SCAN ERR" "" "" "" "" ""
        return
    fi
    [[ -s "$SCAN_ERR" ]] && echo "  [DEBUG] OSV-Scanner warnings for $IMG: $(head -5 "$SCAN_ERR")" >&2
    rm -f "$SCAN_ERR"

    if [[ ! -s "$JSON_TMP" ]]; then
        echo "  [DEBUG] OSV-Scanner returned empty JSON for: $IMG" >&2
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
    COUNTS=$(jq -r "
        $JQ_SEVERITY
        [.results[]? | .packages[]? | .vulnerabilities[]?] | unique_by(.id) |
        [
            (length                                       | tostring),
            (map(select(osv_severity == \"CRITICAL\")) | length | tostring),
            (map(select(osv_severity == \"HIGH\"))     | length | tostring),
            (map(select(osv_severity == \"MEDIUM\"))   | length | tostring),
            (map(select(osv_severity == \"LOW\"))      | length | tostring),
            (map(select(osv_severity == \"UNKNOWN\"))  | length | tostring)
        ] | join(\" \")
    " "$JSON_TMP") || { rm -f "$JSON_TMP"; printf "$ROW_FMT" "$IMG" "PARSE ERR" "" "" "" "" ""; return; }

    rm -f "$JSON_TMP"

    # shellcheck disable=SC2162
    read -r TOTAL CRITICAL HIGH MEDIUM LOW UNKNOWN <<< "$COUNTS"
    printf "$ROW_FMT" "$IMG" "$TOTAL" "$CRITICAL" "$HIGH" "$MEDIUM" "$LOW" "$UNKNOWN"
}

echo ""
echo "============================================================"
echo "  OSV-Scanner — Base & Application Image CVE Comparison"
echo "============================================================"

print_header "── Base / runtime images ──"
for IMG in "${BASE_IMAGES[@]}"; do scan_image "$IMG"; done

print_header "── Application images (hello-conference) ──"
for IMG in "${APP_IMAGES[@]}"; do scan_image "$IMG"; done

echo ""
echo "✅  Scan complete."
echo "⚠   Many OS-level findings (esp. Debian) carry no severity rating in OSV — they count as UNKNOWN here."
