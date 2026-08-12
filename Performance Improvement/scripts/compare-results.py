#!/usr/bin/env python3
"""
Compares JMH JSON results from two Java versions and prints a formatted table.

Usage:
  python3 compare-results.py <a.json> <label_a> <b.json> <label_b>
  python3 compare-results.py <a.json> <b.json>          # legacy: labels auto-derived
"""
import json, sys

REGRESSION_HINTS = {
    'platformThreadPool': (
        "Platform-thread pool is intentionally capped — this measures queueing overhead, "
        "not raw throughput. Improvement shows with larger taskCounts."),
    'virtualThreads': (
        "On Java 17 this falls back to a cached thread pool; on Java 21+ real virtual "
        "threads are used. With small taskCounts overhead dominates; try taskCount=100000."),
    'allocateSmallObjects': (
        "GC improvements in Java 21+ (ZGC/G1 tuning) may reduce allocation throughput "
        "slightly while improving pause times — a different trade-off, not a regression."),
    'recordStyleAllocation': (
        "Record allocation cost is similar across versions; improvement appears at scale."),
}

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

    # ── Plain-text table ──────────────────────────────────────────────────────
    header = (f"\n{'Benchmark':<{col_w}} {label_a:>12} {label_b:>12} "
              f"{'Improvement':>13}  Unit")
    print(header)
    print('─' * len(header))

    regressions = []
    for name in all_benchmarks:
        sa, unit = r_a.get(name, (None, ''))
        sb, _    = r_b.get(name, (None, ''))
        sa_str   = f'{sa:.2f}' if sa is not None else 'N/A'
        sb_str   = f'{sb:.2f}' if sb is not None else 'N/A'
        imp      = improvement(sa, sb, unit)
        print(f'{name:<{col_w}} {sa_str:>12} {sb_str:>12} {imp:>13}  {unit}')

        # Flag regressions
        if sa and sb and sa > 0:
            higher_better = 'ops' in unit.lower()
            pct = (sb - sa) / sa * 100 if higher_better else (sa - sb) / sa * 100
            if pct < -2:          # >2% slower: flag it
                regressions.append((name, pct, unit))

    print()

    # ── Investigation ─────────────────────────────────────────────────────────
    if regressions:
        print('─' * 72)
        print(f'INVESTIGATION  {label_b} appears slower in {len(regressions)} benchmark(s):')
        print('─' * 72)
        for name, pct, unit in regressions:
            print(f'\n  ⚠  {name}  ({pct:.1f}%)')
            hint = next((v for k, v in REGRESSION_HINTS.items()
                         if k.lower() in name.lower()), None)
            if hint:
                # wrap hint at 70 chars
                words, line = hint.split(), ''
                for w in words:
                    if len(line) + len(w) + 1 > 70:
                        print(f'     {line}'); line = w
                    else:
                        line = f'{line} {w}' if line else w
                if line:
                    print(f'     {line}')
            else:
                print(f'     Possible causes: measurement noise (few iterations),')
                print(f'     JVM startup differences, or genuine trade-off in this JVM version.')
        print()
        print('  TIP: increase iterations (-wi 5 -i 5) and forks (-f 3) for stable numbers.')
        print('  TIP: add -prof gc to also compare memory allocation per operation.')
        print()
    else:
        print(f'  ✓  {label_b} is equal or faster in all measured benchmarks.')
        print()

if __name__ == '__main__':
    main()
