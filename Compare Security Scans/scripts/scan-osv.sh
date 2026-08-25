#!/usr/bin/env bash
# scan-osv.sh — Scan all images with OSV-Scanner, saving JSON results.
# Delegates to the OSV tool directory's compare-images.sh with --json-out.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
RESULTS_DIR="$PROJECT_DIR/target/results/osv"

echo ""
echo "============================================================"
echo "  OSV-Scanner — Scanning all images"
echo "============================================================"
echo ""

# No local DB to update — OSV-Scanner queries the live OSV.dev API. Still
# refresh the scanner image itself, same spirit as the Grype/Trivy DB update.
bash "$ROOT_DIR/OSV/scripts/update-db.sh"

# Run comparison and save JSON
bash "$ROOT_DIR/OSV/scripts/compare-images.sh" --json-out "$RESULTS_DIR"

echo ""
echo "OK  OSV-Scanner results saved to: $RESULTS_DIR/"
echo ""
