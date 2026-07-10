#!/usr/bin/env bash
# scan-grype.sh — Scan all images with Grype, saving JSON results.
# Delegates to the Grype tool directory's compare-images.sh with --json-out.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
RESULTS_DIR="$PROJECT_DIR/target/results/grype"

echo ""
echo "============================================================"
echo "  Grype — Scanning all images"
echo "============================================================"
echo ""

# Update DB first
bash "$ROOT_DIR/Grype/scripts/update-db.sh"

# Run comparison and save JSON
bash "$ROOT_DIR/Grype/scripts/compare-images.sh" --json-out "$RESULTS_DIR"

echo ""
echo "OK  Grype results saved to: $RESULTS_DIR/"
echo ""
