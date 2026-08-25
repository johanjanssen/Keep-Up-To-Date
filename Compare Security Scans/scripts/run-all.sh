#!/usr/bin/env bash
# run-all.sh — Run Grype, Trivy, OSV-Scanner, and OWASP scanners and then produce comparison tables.
# Usage: bash "Compare Security Scans/scripts/run-all.sh"
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Compare Security Scans — Full Pipeline                     ║"
echo "║  Scanning all images with Grype, Trivy, OSV-Scanner, OWASP  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

echo "═══════════════════════ Step 0: Pull base images ══════════════"
bash "$ROOT_DIR/Build Docker Images/pull-base-images.sh"

echo "═══════════════════════ Step 1/5: Grype ═══════════════════════"
bash "$SCRIPT_DIR/scan-grype.sh"

echo "═══════════════════════ Step 2/5: Trivy ═══════════════════════"
bash "$SCRIPT_DIR/scan-trivy.sh"

echo "═══════════════════════ Step 3/5: OSV-Scanner ═════════════════"
bash "$SCRIPT_DIR/scan-osv.sh"

echo "═══════════════════════ Step 4/5: OWASP Dependency Check ═════"
bash "$ROOT_DIR/OWASP Dependency Check/scripts/run-check.sh"

echo "═══════════════════════ Step 5/5: Compare ═════════════════════"
bash "$SCRIPT_DIR/compare.sh"
