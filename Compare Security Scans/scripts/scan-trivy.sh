#!/usr/bin/env bash
# scan-trivy.sh — Scan all images with Trivy, saving JSON results.
# Delegates to the Trivy tool directory's compare-images.sh with --json-out.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$PROJECT_DIR")"
RESULTS_DIR="$PROJECT_DIR/target/results/trivy"

echo ""
echo "============================================================"
echo "  Trivy — Scanning all images"
echo "============================================================"
echo ""

# Update DB first
bash "$ROOT_DIR/Trivy/scripts/update-db.sh"

# Run comparison and save JSON
bash "$ROOT_DIR/Trivy/scripts/compare-images.sh" --json-out "$RESULTS_DIR"

echo ""
echo "OK  Trivy results saved to: $RESULTS_DIR/"
echo ""
