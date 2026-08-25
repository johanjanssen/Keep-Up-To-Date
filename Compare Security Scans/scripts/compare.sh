#!/usr/bin/env bash
# compare.sh — Parse results from Grype, Trivy, OSV-Scanner, and OWASP and produce comparison views:
#   1. Severity count comparison — Grype, Trivy, and OSV-Scanner side-by-side, each with
#      a "unique" column (a CVE that tool found and neither of the other two did)
#   2. OS-level vs Application-level vulnerability breakdown
#
# Run after: scan-grype.sh, scan-trivy.sh, scan-osv.sh, and OWASP Dependency Check/scripts/run-check.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_DIR/target/results"
ROOT_DIR="$(cd "$PROJECT_DIR/.." && pwd)"
# shellcheck source=../../images.conf
source "$ROOT_DIR/images.conf"

OWASP_JSON="$ROOT_DIR/Vulnerable Application/target/dependency-check-report.json"

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

count_osv() {
    local FILE="$1"
    [[ -f "$FILE" ]] || { echo "- - - - - -"; return; }
    # Severity bucketing mirrors OSV/scripts/compare-images.sh's JQ_SEVERITY —
    # see there for the full rationale (GHSA database_specific.severity first,
    # then a vendor-rated severity[] entry, else UNKNOWN; no CVSS-vector math).
    jq -r '
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
        [.results[]? | .packages[]? | .vulnerabilities[]?] | unique_by(.id) |
        {
            total: length,
            critical: (map(select(osv_severity == "CRITICAL")) | length),
            high:     (map(select(osv_severity == "HIGH"))     | length),
            medium:   (map(select(osv_severity == "MEDIUM"))   | length),
            low:      (map(select(osv_severity == "LOW"))      | length),
            unknown:  (map(select(osv_severity == "UNKNOWN"))  | length)
        } | "\(.total) \(.critical) \(.high) \(.medium) \(.low) \(.unknown)"
    ' "$FILE" 2>/dev/null || echo "- - - - - -"
}

extract_trivy_cve_ids() {
    local FILE="$1"
    # `return 0` (not bare `return`, which propagates the `[[ ]]`'s failing
    # status) — under `set -e` a bare-status return here would abort the whole
    # script the moment any one image is missing this tool's JSON (e.g. it
    # wasn't built, or that scanner failed on it) via `IDS=$(extract_...)`.
    [[ -f "$FILE" ]] || return 0
    jq -r '[.Results[]? | .Vulnerabilities // [] | .[].VulnerabilityID] | unique | .[]' "$FILE" 2>/dev/null
}

extract_grype_cve_ids() {
    local FILE="$1"
    [[ -f "$FILE" ]] || return 0
    # Grype often reports app-layer findings under a GHSA-* id while Trivy reports
    # the exact same vulnerability under its CVE-* id (e.g. GHSA-jjjh-jjxp-wpff is
    # CVE-2022-42003). Comparing raw ids would then count that one shared finding
    # as "unique" to BOTH tools at once. relatedVulnerabilities carries the NVD
    # CVE alias when one exists, so prefer that id for cross-tool comparison.
    jq -r '
        [.matches[]? |
            (.vulnerability.id) as $id |
            if ($id | startswith("CVE-")) then $id
            else ((.relatedVulnerabilities // [])[] | select(.id | startswith("CVE-")) | .id) // $id
            end
        ] | unique | .[]
    ' "$FILE" 2>/dev/null
}

extract_osv_cve_ids() {
    local FILE="$1"
    [[ -f "$FILE" ]] || return 0
    # OSV findings are mostly native ids (GHSA-*, GO-*, UBUNTU-CVE-*, ...) rather
    # than CVE-*. Prefer a real CVE id — from the id itself, its aliases (GHSA
    # entries), or its upstream list (Ubuntu/Debian OS advisories) — so OSV lines
    # up with Trivy/Grype's CVE-keyed ids. Falls back to the native id when no
    # CVE alias exists, same as extract_grype_cve_ids above.
    jq -r '
        [.results[]? | .packages[]? | .vulnerabilities[]? |
            (.id) as $id |
            if ($id | startswith("CVE-")) then $id
            else ((([(.aliases // [])[], (.upstream // [])[]]) | map(select(startswith("CVE-"))))[0]) // $id
            end
        ] | unique | .[]
    ' "$FILE" 2>/dev/null
}

# Count ids present in FILE_A's list but not in the OTHER ids (already
# CVE-normalized, newline-separated, may combine several tools' id lists).
# Used for "Unique in X" — a finding X has that none of the other tools do.
unique_count() {
    local IDS_A="$1" IDS_OTHER="$2"
    [[ -z "$IDS_A" ]] && { echo "-"; return; }
    local MISSING=0
    while IFS= read -r ID; do
        echo "$IDS_OTHER" | grep -qxF "$ID" || MISSING=$((MISSING + 1))
    done <<< "$IDS_A"
    [[ $MISSING -eq 0 ]] && echo "-" || echo "$MISSING"
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
echo "║  VIEW 1: Severity Count Comparison — Grype vs Trivy vs OSV-Scanner                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""

BOTH_FMT="%-50s │ %5s %4s %4s %4s %4s %4s │ %5s %4s %4s %4s %4s %4s │ %5s %4s %4s %4s %4s %4s │ %-12s │ %-12s │ %-12s\n"

printf "%-50s │ %-30s │ %-30s │ %-30s │ %-12s │ %-12s │ %-12s\n" "IMAGE" "  GRYPE (Tot/C/H/M/L/U)" "  TRIVY (Tot/C/H/M/L/U)" "  OSV (Tot/C/H/M/L/U)" "Unique Grype" "Unique Trivy" "Unique OSV"
printf '%s┼%s┼%s┼%s┼%s┼%s┼%s\n' "$(printf '─%.0s' {1..51})" "$(printf '─%.0s' {1..32})" "$(printf '─%.0s' {1..32})" "$(printf '─%.0s' {1..32})" "$(printf '─%.0s' {1..14})" "$(printf '─%.0s' {1..14})" "$(printf '─%.0s' {1..14})"

for IMG in "${ALL_IMAGES[@]}"; do
    FNAME=$(image_to_filename "$IMG")
    GRYPE_FILE="$RESULTS_DIR/grype/${FNAME}.json"
    TRIVY_FILE="$RESULTS_DIR/trivy/${FNAME}.json"
    OSV_FILE="$RESULTS_DIR/osv/${FNAME}.json"
    GRYPE_COUNTS=$(count_grype "$GRYPE_FILE")
    TRIVY_COUNTS=$(count_trivy "$TRIVY_FILE")
    OSV_COUNTS=$(count_osv "$OSV_FILE")
    GRYPE_CVES=$(extract_grype_cve_ids "$GRYPE_FILE")
    TRIVY_CVES=$(extract_trivy_cve_ids "$TRIVY_FILE")
    OSV_CVES=$(extract_osv_cve_ids "$OSV_FILE")
    UNIQUE_GRYPE=$(unique_count "$GRYPE_CVES" "$(printf '%s\n%s' "$TRIVY_CVES" "$OSV_CVES")")
    UNIQUE_TRIVY=$(unique_count "$TRIVY_CVES" "$(printf '%s\n%s' "$GRYPE_CVES" "$OSV_CVES")")
    UNIQUE_OSV=$(unique_count "$OSV_CVES" "$(printf '%s\n%s' "$GRYPE_CVES" "$TRIVY_CVES")")
    # shellcheck disable=SC2086
    printf "$BOTH_FMT" "$IMG" $GRYPE_COUNTS $TRIVY_COUNTS $OSV_COUNTS "$UNIQUE_GRYPE" "$UNIQUE_TRIVY" "$UNIQUE_OSV"
done

echo ""
echo "Legend: Tot=Total  C=Critical  H=High  M=Medium  L=Low  U=Unknown"
echo "        All counts are unique CVEs (deduplicated by CVE ID, with Grype's GHSA ids and OSV's native ids resolved to"
echo "        their CVE alias — via relatedVulnerabilities for Grype, aliases/upstream for OSV — so the same finding"
echo "        under a different id scheme isn't double-counted or wrongly called 'unique')"
echo "        '-' = scan not run, or no unique findings"
echo "        Unique Grype/Trivy/OSV = CVEs that tool found and NEITHER of the other two did"
echo "        ⚠ Trivy may show 0 for Oracle Linux 10 images (e.g. GraalVM) — its vuln DB lacks OL10 coverage"
echo "        ⚠ OSV often has no severity rating for OS-level CVEs (esp. Debian) — those count as UNKNOWN, not missing"

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
echo "   OWASP scans the same hello-conference app (Vulnerable Application/pom.xml) that every image is built from"
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
echo "║  • OWASP DC scans Vulnerable Application/pom.xml directly (log4j-core 2.14.1, jackson-databind 2.13.4.1)       ║"
echo "║    — the exact same source every hello-conference:* image is built from, so its counts are the same everywhere║"
echo "║  • Unique Grype/Trivy/OSV = CVEs only that tool found — use multiple tools for best coverage                   ║"
echo "║  • OSV-Scanner (View 1) adds a 3rd independent data source (OSV.dev) — but its OS-level severity data is       ║"
echo "║    patchier than Grype/Trivy's (esp. Debian), so more of its findings land in the Unknown bucket here          ║"
echo "╚══════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""

