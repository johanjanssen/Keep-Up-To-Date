#!/usr/bin/env python3
"""
Compares JMH JSON results from two Java versions and prints a formatted table.

Usage:
  python3 compare-results.py <a.json> <label_a> <b.json> <label_b>
  python3 compare-results.py <a.json> <b.json>          # legacy: labels auto-derived
"""
import json, sys

def load_results(path):
    with open(path, encoding='utf-8-sig') as f:
        data = json.load(f)
    results = {}
    for entry in data:
        name  = entry['benchmark'].split('.')[-1]
        score = entry['primaryMetric']['score']
        unit  = entry['primaryMetric']['scoreUnit']
        results[name] = (score, unit)
    return results

def derive_label(path):
    """Guess a friendly label from the filename, e.g. java17.json → Java 17."""
    base = path.split('/')[-1].split('\\')[-1].replace('.json', '')
    for ver in ('17', '21', '25', '28'):
        if ver in base:
            return f'Java {ver}'
    return base

def improvement(s_a, s_b, unit):
    if s_a is None or s_b is None or s_a == 0:
        return '—'
    higher_better = 'ops' in unit.lower()
    pct = (s_b - s_a) / s_a * 100 if higher_better else (s_a - s_b) / s_a * 100
    sign = '+' if pct > 0 else ''
    return f'{sign}{pct:.1f}%'

def main():
    args = sys.argv[1:]
    if len(args) == 4:
        file_a, label_a, file_b, label_b = args
    elif len(args) == 2:
        file_a, file_b = args
        label_a = derive_label(file_a)
        label_b = derive_label(file_b)
    else:
        print(__doc__); sys.exit(1)

    try:
        r_a = load_results(file_a)
        r_b = load_results(file_b)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f'Error loading results: {e}'); sys.exit(1)

    all_benchmarks = sorted(set(r_a) | set(r_b))
    col_w = max(len(b) for b in all_benchmarks) + 2
    # Truncate labels if too wide for table
    la = label_a[:12]
    lb = label_b[:12]

    # ── Plain-text table ──────────────────────────────────────────────────────
    header = f"\n{'Benchmark':<{col_w}} {la:>12} {lb:>12} {'Δ':>8}  Unit"
    print(header)
    print('─' * len(header))

    regressions = []
    for name in all_benchmarks:
        sa, unit = r_a.get(name, (None, ''))
        sb, _    = r_b.get(name, (None, ''))
        sa_str   = f'{sa:.2f}' if sa is not None else 'N/A'
        sb_str   = f'{sb:.2f}' if sb is not None else 'N/A'
        imp      = improvement(sa, sb, unit)
        print(f'{name:<{col_w}} {sa_str:>12} {sb_str:>12} {imp:>8}  {unit}')

        # Flag regressions
        if sa and sb and sa > 0:
            higher_better = 'ops' in unit.lower()
            pct = (sb - sa) / sa * 100 if higher_better else (sa - sb) / sa * 100
            if pct < -2:          # >2% slower: flag it
                regressions.append((name, pct, unit))

    print()

    # ── Investigation ─────────────────────────────────────────────────────────
    if regressions:
        print('─' * 60)
        print(f'NOTE: {label_b} appears slower in {len(regressions)} benchmark(s):')
        print('─' * 60)
        for name, pct, unit in regressions:
            print(f'  ⚠  {name}  ({pct:.1f}%)')
        print()
    else:
        print(f'  ✓  {label_b} is equal or faster in all measured benchmarks.')
        print()

if __name__ == '__main__':
    main()
