#!/usr/bin/env python3
"""
Compares JMH JSON results from two Java versions and prints a formatted table.
Usage: python3 compare-results.py java17.json java25.json
"""
import json
import sys

def load_results(path):
    with open(path) as f:
        data = json.load(f)
    results = {}
    for entry in data:
        name = entry["benchmark"].split(".")[-1]
        score = entry["primaryMetric"]["score"]
        unit = entry["primaryMetric"]["scoreUnit"]
        results[name] = (score, unit)
    return results

def main():
    if len(sys.argv) < 3:
        print("Usage: compare-results.py <java17.json> <java25.json>")
        sys.exit(1)

    try:
        r17 = load_results(sys.argv[1])
        r25 = load_results(sys.argv[2])
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading results: {e}")
        sys.exit(1)

    all_benchmarks = sorted(set(list(r17.keys()) + list(r25.keys())))

    print(f"\n{'Benchmark':<35} {'Java 17':>12} {'Java 25':>12} {'Improvement':>12} {'Unit'}")
    print("─" * 80)

    for name in all_benchmarks:
        s17, unit = r17.get(name, (None, ""))
        s25, _ = r25.get(name, (None, ""))

        s17_str = f"{s17:.2f}" if s17 is not None else "N/A"
        s25_str = f"{s25:.2f}" if s25 is not None else "N/A"

        if s17 is not None and s25 is not None and s17 > 0:
            if "ops" in unit.lower():
                # Higher is better for throughput
                pct = ((s25 - s17) / s17) * 100
                improvement = f"+{pct:.1f}%" if pct > 0 else f"{pct:.1f}%"
            else:
                # Lower is better for latency
                pct = ((s17 - s25) / s17) * 100
                improvement = f"+{pct:.1f}%" if pct > 0 else f"{pct:.1f}%"
        else:
            improvement = "—"

        print(f"{name:<35} {s17_str:>12} {s25_str:>12} {improvement:>12} {unit}")

    print()

if __name__ == "__main__":
    main()

