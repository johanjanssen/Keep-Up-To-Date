#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# run-benchmarks.sh — Runs JMH benchmarks on Java 17, 25, and 28 EA,
# then compares the results side by side.
#
# Usage:
#   ./scripts/run-benchmarks.sh                  # all benchmarks, all versions
#   ./scripts/run-benchmarks.sh ".*Valhalla.*"   # Valhalla only
#   ./scripts/run-benchmarks.sh ".*Stream.*"     # Stream only
# ─────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_DIR/results"

mkdir -p "$RESULTS_DIR"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m'

BENCHMARK_FILTER="${1:-.*}"

cd "$PROJECT_DIR"

echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Java Performance: 17 vs 25 vs 28 EA (Valhalla)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo ""

for VER in java17 java25 java28; do
  echo -e "${GREEN}▶ Building bench:$VER ...${NC}"
  docker build -f "Dockerfile.$VER" -t "bench:$VER" .
done

for VER in java17 java25 java28; do
  echo ""
  echo -e "${GREEN}▶ Running benchmarks on $VER ...${NC}"
  docker run --rm -v "$RESULTS_DIR:/results" "bench:$VER" \
    -f 1 -wi 2 -i 3 -p size=1000000 -p taskCount=10000 "$BENCHMARK_FILTER" \
    2>&1 | tee "$RESULTS_DIR/${VER}-output.txt" || true
  cp "$RESULTS_DIR/results.json" "$RESULTS_DIR/${VER}.json" 2>/dev/null || true
done

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Comparison: Java 17 vs Java 25${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
python3 "$SCRIPT_DIR/compare-results.py" \
  "$RESULTS_DIR/java17.json" "$RESULTS_DIR/java25.json" 2>/dev/null || true

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  Comparison: Java 25 vs Java 28 EA (Valhalla)${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
python3 "$SCRIPT_DIR/compare-results.py" \
  "$RESULTS_DIR/java25.json" "$RESULTS_DIR/java28.json" 2>/dev/null || true
