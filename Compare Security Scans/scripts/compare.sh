#!/usr/bin/env bash
# compare.sh — Parse results from Grype, Trivy, and OWASP and produce comparison views:
#   1. Severity count comparison (Grype + Trivy) with coverage indicator
#   2. OS-level vs Application-level vulnerability breakdown
#
# Run after: scan-grype.sh, scan-trivy.sh, and OWASP Dependency Check/scripts/run-check.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_DIR/target/results"
ROOT_DIR="$(cd "$PROJECT_DIR/.." && pwd)"
# shellcheck source=../../images.conf
source "$ROOT_DIR/images.conf"

OWASP_JSON="$ROOT_DIR/OWASP Dependency Check/target/dependency-check-report.json"

for TOOL in jq; do
    command -v "$TOOL" &>/dev/null || { echo "❌  '$TOOL' not found."; exit 1; }
done

# ── Helpers ───────────────────────────────────────────────────
count_trivy() {
    local FILE="$1"
    [[ -f "$FILE" ]] || { echo "- - - - - -"; return; }
    jq -r '
        [.Results[]? | .Vulnerabilities // [] | .[]] | unique_by(.VulnerabilityID) |
        {
            total: length,
            critical: (map(select(.Severity == "CRITICAL")) | length),
            high:     (map(select(.Severity == "HIGH"))     | length),
            medium:   (map(select(.Severity == "MEDIUM"))   | length),
            low:      (map(select(.Severity == "LOW"))      | length),
            unknown:  (map(select(.Severity == "UNKNOWN"))  | length)
        } | "\(.total) \(.critical) \(.high) \(.medium) \(.low) \(.unknown)"
    ' "$FILE" 2>/dev/null || echo "- - - - - -"
}

count_grype() {
    local FILE="$1"
    [[ -f "$FILE" ]] || { echo "- - - - - -"; return; }
    jq -r '
        [.matches[]?] | unique_by(.vulnerability.id) |
        {
            total: length,
            critical: (map(select(.vulnerability.severity == "Critical")) | length),
            high:     (map(select(.vulnerability.severity == "High"))     | length),
            medium:   (map(select(.vulnerability.severity == "Medium"))   | length),
            low:      (map(select(.vulnerability.severity == "Low"))      | length),
            unknown:  (map(select(.vulnerability.severity | IN("Critical","High","Medium","Low") | not)) | length)
        } | "\(.total) \(.critical) \(.high) \(.medium) \(.low) \(.unknown)"
    ' "$FILE" 2>/dev/null || echo "- - - - - -"
}

extract_trivy_cve_ids() {
    local FILE="$1"
    [[ -f "$FILE" ]] || return
    jq -r '[.Results[]? | .Vulnerabilities // [] | .[].VulnerabilityID] | unique | .[]' "$FILE" 2>/dev/null
}

extract_grype_cve_ids() {
    local FILE="$1"
    [[ -f "$FILE" ]] || return
    jq -r '[.matches[]? | .vulnerability.id] | unique | .[]' "$FILE" 2>/dev/null
}

# Check if Grype found all CVEs that Trivy found
# Returns: "Yes", "No (N missed)", or "-"
check_grype_covers_trivy() {
    local GRYPE_FILE="$1" TRIVY_FILE="$2"
    [[ -f "$TRIVY_FILE" ]] || { echo "-"; return; }
    [[ -f "$GRYPE_FILE" ]] || { echo "all"; return; }

    local TRIVY_CVES GRYPE_CVES MISSED
    TRIVY_CVES=$(extract_trivy_cve_ids "$TRIVY_FILE")
    [[ -z "$TRIVY_CVES" ]] && { echo "-"; return; }
    GRYPE_CVES=$(extract_grype_cve_ids "$GRYPE_FILE")

    MISSED=0
    while IFS= read -r CVE; do
        if ! echo "$GRYPE_CVES" | grep -qxF "$CVE"; then
            MISSED=$((MISSED + 1))
        fi
    done <<< "$TRIVY_CVES"

    if [[ $MISSED -eq 0 ]]; then
        echo "-"
    else
        echo "$MISSED"
    fi
}

# Count vulnerabilities by class for Trivy (os vs app)
count_trivy_by_class() {
    local FILE="$1" CLASS="$2"
    [[ -f "$FILE" ]] || { echo "- - - - - -"; return; }
    local FILTER
    if [[ "$CLASS" == "os" ]]; then
        FILTER='.Results[]? | select(.Class == "os-pkgs") | .Vulnerabilities // [] | .[]'
    else
        FILTER='.Results[]? | select(.Class == "lang-pkgs") | .Vulnerabilities // [] | .[]'
    fi
    jq -r "
        [$FILTER] | unique_by(.VulnerabilityID) |
        {
            total: length,
            critical: (map(select(.Severity == \"CRITICAL\")) | length),
            high:     (map(select(.Severity == \"HIGH\"))     | length),
            medium:   (map(select(.Severity == \"MEDIUM\"))   | length),
            low:      (map(select(.Severity == \"LOW\"))      | length),
            unknown:  (map(select(.Severity == \"UNKNOWN\"))  | length)
        } | \"\(.total) \(.critical) \(.high) \(.medium) \(.low) \(.unknown)\"
    " "$FILE" 2>/dev/null || echo "- - - - - -"
}

# Count vulnerabilities by type for Grype (os vs app)
count_grype_by_type() {
    local FILE="$1" TYPE="$2"
    [[ -f "$FILE" ]] || { echo "- - - - - -"; return; }
    local FILTER
    if [[ "$TYPE" == "os" ]]; then
        FILTER='.matches[]? | select(.artifact.type | IN("deb","rpm","apk","pacman","alpm"))'
    else
        FILTER='.matches[]? | select(.artifact.type | IN("deb","rpm","apk","pacman","alpm") | not)'
    fi
    jq -r "
        [$FILTER] | unique_by(.vulnerability.id) |
        {
            total: length,
            critical: (map(select(.vulnerability.severity == \"Critical\")) | length),
            high:     (map(select(.vulnerability.severity == \"High\"))     | length),
            medium:   (map(select(.vulnerability.severity == \"Medium\"))   | length),
            low:      (map(select(.vulnerability.severity == \"Low\"))      | length),
            unknown:  (map(select(.vulnerability.severity | IN(\"Critical\",\"High\",\"Medium\",\"Low\") | not)) | length)
        } | \"\(.total) \(.critical) \(.high) \(.medium) \(.low) \(.unknown)\"
    " "$FILE" 2>/dev/null || echo "- - - - - -"
}

# Count OWASP vulnerabilities (deduplicated by CVE name)
count_owasp() {
    [[ -f "$OWASP_JSON" ]] || { echo "- - - - - -"; return; }
    jq -r '
        [.dependencies[]? | .vulnerabilities // [] | .[]] | unique_by(.name) |
        {
            total: length,
            critical: (map(select(.severity == "CRITICAL" or .severity == "Critical")) | length),
            high:     (map(select(.severity == "HIGH" or .severity == "High"))         | length),
            medium:   (map(select(.severity == "MEDIUM" or .severity == "Medium"))     | length),
            low:      (map(select(.severity == "LOW" or .severity == "Low"))           | length),
            unknown:  (map(select(.severity | ascii_downcase | IN("critical","high","medium","low") | not)) | length)
        } | "\(.total) \(.critical) \(.high) \(.medium) \(.low) \(.unknown)"
    ' "$OWASP_JSON" 2>/dev/null || echo "- - - - - -"
}

# ══════════════════════════════════════════════════════════════════
# VIEW 1: Severity Count — Both Tools + Coverage
# ══════════════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║  VIEW 1: Severity Count Comparison — Grype vs Trivy                                                            ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""

BOTH_FMT="%-50s │ %5s %4s %4s %4s %4s %4s │ %5s %4s %4s %4s %4s %4s │ %-12s\n"

printf "%-50s │ %-30s │ %-30s │ %-12s\n" "IMAGE" "  GRYPE (Tot/C/H/M/L/U)" "  TRIVY (Tot/C/H/M/L/U)" "Unique in Trivy"
printf '%s┼%s┼%s┼%s\n' "$(printf '─%.0s' {1..51})" "$(printf '─%.0s' {1..32})" "$(printf '─%.0s' {1..32})" "$(printf '─%.0s' {1..18})"

for IMG in "${ALL_IMAGES[@]}"; do
    FNAME=$(image_to_filename "$IMG")
    GRYPE_FILE="$RESULTS_DIR/grype/${FNAME}.json"
    TRIVY_FILE="$RESULTS_DIR/trivy/${FNAME}.json"
    GRYPE_COUNTS=$(count_grype "$GRYPE_FILE")
    TRIVY_COUNTS=$(count_trivy "$TRIVY_FILE")
    COVERAGE=$(check_grype_covers_trivy "$GRYPE_FILE" "$TRIVY_FILE")
    # shellcheck disable=SC2086
    printf "$BOTH_FMT" "$IMG" $GRYPE_COUNTS $TRIVY_COUNTS "$COVERAGE"
done

echo ""
echo "Legend: Tot=Total  C=Critical  H=High  M=Medium  L=Low  U=Unknown"
echo "        All counts are unique CVEs (deduplicated by CVE ID)"
echo "        '-' = scan not run, or no unique findings"
echo "        Unique Trivy = Number of CVEs found by Trivy but NOT by Grype"

# ══════════════════════════════════════════════════════════════════
# VIEW 2: OS-level vs Application-level Breakdown
# ══════════════════════════════════════════════════════════════════
echo ""
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║  VIEW 2: OS Packages vs Application Dependencies — Vulnerability Breakdown                                     ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "── OS-level vulnerabilities (packages from the base image) ──"
echo ""

OS_FMT="%-50s │ %5s %4s %4s %4s %4s %4s │ %5s %4s %4s %4s %4s %4s\n"

printf "%-50s │ %-30s │ %-30s\n" "IMAGE" "  GRYPE (Tot/C/H/M/L/U)" "  TRIVY (Tot/C/H/M/L/U)"
printf '%s┼%s┼%s\n' "$(printf '─%.0s' {1..51})" "$(printf '─%.0s' {1..32})" "$(printf '─%.0s' {1..32})"

for IMG in "${ALL_IMAGES[@]}"; do
    FNAME=$(image_to_filename "$IMG")
    GRYPE_COUNTS=$(count_grype_by_type "$RESULTS_DIR/grype/${FNAME}.json" "os")
    TRIVY_COUNTS=$(count_trivy_by_class "$RESULTS_DIR/trivy/${FNAME}.json" "os")
    # shellcheck disable=SC2086
    printf "$OS_FMT" "$IMG" $GRYPE_COUNTS $TRIVY_COUNTS
done

echo ""
echo ""
echo "── Application-level vulnerabilities (JAR/language dependencies) ──"
echo "   ⚠ OWASP scans a different project (demo with intentionally vulnerable deps)"
echo ""

APP_FMT="%-50s │ %5s %4s %4s %4s %4s %4s │ %5s %4s %4s %4s %4s %4s │ %5s %4s %4s %4s %4s %4s\n"

printf "%-50s │ %-30s │ %-30s │ %-30s\n" "IMAGE" "  GRYPE (Tot/C/H/M/L/U)" "  TRIVY (Tot/C/H/M/L/U)" "  OWASP (Tot/C/H/M/L/U)"
printf '%s┼%s┼%s┼%s\n' "$(printf '─%.0s' {1..51})" "$(printf '─%.0s' {1..32})" "$(printf '─%.0s' {1..32})" "$(printf '─%.0s' {1..32})"

OWASP_COUNTS=$(count_owasp)

for IMG in "${APP_IMAGES[@]}"; do
    FNAME=$(image_to_filename "$IMG")
    GRYPE_COUNTS=$(count_grype_by_type "$RESULTS_DIR/grype/${FNAME}.json" "app")
    TRIVY_COUNTS=$(count_trivy_by_class "$RESULTS_DIR/trivy/${FNAME}.json" "app")
    # shellcheck disable=SC2086
    printf "$APP_FMT" "$IMG" $GRYPE_COUNTS $TRIVY_COUNTS $OWASP_COUNTS
done

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║  Key Takeaways                                                                                                 ║"
echo "╠══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣"
echo "║  • All counts show unique CVEs (deduplicated) — not raw vulnerability entries                                  ║"
echo "║  • OS-level: vulnerabilities in distro packages (apt/rpm) — reduced by distroless/scratch images               ║"
echo "║  • App-level: vulnerabilities in JARs/dependencies — same across images (same app)                             ║"
echo "║  • ⚠ OWASP scans a DIFFERENT project (demo with intentionally vulnerable deps like log4j 2.0,                 ║"
echo "║    jackson-databind 2.9.10, Spring Boot 2.7) — NOT the hello-conference app that Trivy/Grype scan              ║"
echo "║  • Unique Trivy = CVEs that only Trivy found — use both tools for best coverage                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""

