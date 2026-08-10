#!/usr/bin/env python3
"""
Generate presentation-ready comparison charts from two JMH JSON result files.

Produces (in <output_dir>/):
  <prefix>-table.png    – colour-coded comparison table
  <prefix>-barplot.png  – horizontal grouped bar chart with improvement badges

Usage:
  python3 generate-charts.py <a.json> <label_a> <b.json> <label_b> <output_dir> [prefix]

Example:
  python3 generate-charts.py results/java17.json "Java 17" \
      results/java25.json "Java 25" results/ java17-vs-java25
"""

import json, sys, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
from matplotlib.colors import to_rgba

# ── Presentation defaults ─────────────────────────────────────────────────────
rcParams['font.family']        = 'DejaVu Sans'
rcParams['figure.dpi']         = 150
rcParams['savefig.dpi']        = 150
rcParams['savefig.bbox']       = 'tight'
rcParams['savefig.pad_inches'] = 0.20

# ── Palette ───────────────────────────────────────────────────────────────────
BG_COLOR   = '#F8F9FC'
GRID_COLOR = '#DDE1EA'
TEXT_COLOR = '#1A1D23'
MUTED      = '#6B7280'

HEADER_BG    = '#1A237E'   # deep indigo
HEADER_FG    = '#FFFFFF'
ALT_ROW      = '#EEF2FF'   # soft indigo tint
GOOD_COLOR   = '#1B5E20'   # dark green
BAD_COLOR    = '#B71C1C'   # dark red
NEUTRAL      = '#37474F'

VERSION_PALETTES = {
    '17': '#D84315',   # deep orange-red
    '25': '#1565C0',   # deep blue
    '28': '#6A1B9A',   # deep purple
    '21': '#00695C',   # teal
}

def _version_color(label: str) -> str:
    for ver, color in VERSION_PALETTES.items():
        if ver in label:
            return color
    return '#37474F'


# ── Data loading ──────────────────────────────────────────────────────────────

def load_results(path: str) -> dict:
    """
    Returns {display_name: (score, error, unit)}.
    Benchmark names are shortened to the method part; params appended if present.
    """
    with open(path, encoding='utf-8-sig') as f:
        data = json.load(f)

    results = {}
    for entry in data:
        method = entry['benchmark'].split('.')[-1]
        params = entry.get('params', {})
        # Build a compact param suffix, e.g.  "size=1 000 000"
        if params:
            parts = [f"{k}={int(v):,}" if v.isdigit() else f"{k}={v}"
                     for k, v in sorted(params.items())]
            suffix = '  (' + ', '.join(parts) + ')'
        else:
            suffix = ''
        name = method + suffix
        score = entry['primaryMetric']['score']
        error = entry['primaryMetric'].get('scoreError', 0.0) or 0.0
        unit  = entry['primaryMetric']['scoreUnit']
        results[name] = (score, error, unit)
    return results


def improvement(s_a: float, s_b: float, unit: str):
    """
    Return (text, is_positive).
    is_positive = True  means B is *better* than A.
    """
    if not s_a or not s_b:
        return '—', None
    higher_better = 'ops' in unit.lower()
    if higher_better:
        pct = (s_b - s_a) / s_a * 100
    else:
        pct = (s_a - s_b) / s_a * 100          # latency: lower is better
    sign = '+' if pct > 0 else ''
    return f'{sign}{pct:.1f}%', pct > 0


# ── Table image ───────────────────────────────────────────────────────────────

def draw_table(r_a, r_b, label_a, label_b, out_path: str):
    benchmarks = sorted(set(r_a) | set(r_b))
    if not benchmarks:
        print("  ⚠  No benchmark data found – skipping table.")
        return

    unit = next(iter(r_a.values()), (None, None, 'ms/op'))[2]
    arrow = '↓ lower = faster' if 'ms' in unit else '↑ higher = faster'

    # Build row data
    rows = []
    for name in benchmarks:
        sa, _, _ = r_a.get(name, (None, 0, unit))
        sb, _, _ = r_b.get(name, (None, 0, unit))
        sa_str = f'{sa:,.2f}' if sa is not None else '—'
        sb_str = f'{sb:,.2f}' if sb is not None else '—'
        imp_txt, imp_pos = improvement(sa, sb, unit)
        rows.append((name, sa_str, sb_str, imp_txt, imp_pos))

    n = len(rows)
    COL_W  = [0.42, 0.13, 0.13, 0.17, 0.10]
    HDR    = ['Benchmark', label_a, label_b, f'{label_b} vs {label_a}', 'Unit']

    fig_h = max(4.0, 1.4 + n * 0.54)
    fig, ax = plt.subplots(figsize=(15, fig_h), facecolor=BG_COLOR)
    ax.axis('off')
    ax.set_facecolor(BG_COLOR)

    cell_text = [[r[0], r[1], r[2], r[3], unit] for r in rows]

    tbl = ax.table(
        cellText=cell_text,
        colLabels=HDR,
        loc='center',
        cellLoc='center',
        colWidths=COL_W,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    tbl.scale(1, 1.65)

    # Header row
    for j in range(len(HDR)):
        cell = tbl[0, j]
        cell.set_facecolor(HEADER_BG)
        cell.set_text_props(color=HEADER_FG, fontweight='bold', fontsize=13)
        cell.set_edgecolor('#0D1257')

    # Data rows
    for i, (_, _, _, _, imp_pos) in enumerate(rows):
        row_bg = ALT_ROW if i % 2 == 0 else 'white'
        for j in range(len(HDR)):
            cell = tbl[i + 1, j]
            cell.set_facecolor(row_bg)
            cell.set_edgecolor(GRID_COLOR)
            cell.set_text_props(color=TEXT_COLOR, fontsize=12)

        # Benchmark name – left-align
        tbl[i + 1, 0].set_text_props(ha='left', fontsize=11)
        tbl[i + 1, 0].PAD = 0.04

        # Improvement column – colour-coded
        imp_cell = tbl[i + 1, 3]
        if imp_pos is True:
            imp_cell.set_text_props(color=GOOD_COLOR, fontweight='bold', fontsize=13)
        elif imp_pos is False:
            imp_cell.set_text_props(color=BAD_COLOR, fontweight='bold', fontsize=13)
        else:
            imp_cell.set_text_props(color=MUTED, fontsize=12)

        # Score columns – bold
        tbl[i + 1, 1].set_text_props(fontweight='bold', color=_version_color(label_a))
        tbl[i + 1, 2].set_text_props(fontweight='bold', color=_version_color(label_b))

    title = (f'{label_a}  vs  {label_b}  —  JMH Benchmark Comparison\n'
             f'{unit}   •   {arrow}')
    ax.set_title(title, fontsize=15, fontweight='bold',
                 color=TEXT_COLOR, pad=16, linespacing=1.6)

    fig.savefig(out_path, facecolor=BG_COLOR)
    plt.close(fig)
    print(f'  ✓  table  → {out_path}')


# ── Bar-plot image ─────────────────────────────────────────────────────────────

def draw_barplot(r_a, r_b, label_a, label_b, out_path: str):
    benchmarks = sorted(set(r_a) | set(r_b))
    if not benchmarks:
        print("  ⚠  No benchmark data found – skipping barplot.")
        return

    unit = next(iter(r_a.values()), (None, None, 'ms/op'))[2]
    arrow = '↓ lower = faster' if 'ms' in unit else '↑ higher = faster'

    col_a = _version_color(label_a)
    col_b = _version_color(label_b)

    n          = len(benchmarks)
    scores_a   = [r_a.get(b, (0, 0, unit))[0] or 0.0 for b in benchmarks]
    errors_a   = [r_a.get(b, (0, 0, unit))[1] or 0.0 for b in benchmarks]
    scores_b   = [r_b.get(b, (0, 0, unit))[0] or 0.0 for b in benchmarks]
    errors_b   = [r_b.get(b, (0, 0, unit))[1] or 0.0 for b in benchmarks]

    # Shorten tick labels for display
    tick_labels = [b.replace('  (', '\n(') for b in benchmarks]

    fig_h = max(7, n * 1.05 + 2.8)
    fig, ax = plt.subplots(figsize=(16, fig_h), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    y      = np.arange(n)
    bar_h  = 0.35

    bars_a = ax.barh(y + bar_h / 2, scores_a, bar_h,
                     xerr=errors_a, label=label_a,
                     color=col_a, alpha=0.88,
                     error_kw=dict(ecolor='#9E9E9E', capsize=5, lw=1.4, capthick=1.4))
    bars_b = ax.barh(y - bar_h / 2, scores_b, bar_h,
                     xerr=errors_b, label=label_b,
                     color=col_b, alpha=0.88,
                     error_kw=dict(ecolor='#9E9E9E', capsize=5, lw=1.4, capthick=1.4))

    all_scores  = [s for s in scores_a + scores_b if s > 0]
    x_max       = max(all_scores) if all_scores else 1.0
    label_space = x_max * 0.012

    # Inline value labels
    for bar, score in zip(bars_a, scores_a):
        if score > 0:
            ax.text(score + label_space,
                    bar.get_y() + bar.get_height() / 2,
                    f'{score:,.1f}',
                    va='center', ha='left', fontsize=10.5,
                    color=TEXT_COLOR, fontweight='bold')

    for bar, score in zip(bars_b, scores_b):
        if score > 0:
            ax.text(score + label_space,
                    bar.get_y() + bar.get_height() / 2,
                    f'{score:,.1f}',
                    va='center', ha='left', fontsize=10.5,
                    color=TEXT_COLOR, fontweight='bold')

    # Improvement badges on the right edge
    higher_better = 'ops' in unit.lower()
    badge_x = x_max * 1.19
    ax.set_xlim(0, x_max * 1.26)

    for i, (sa, sb) in enumerate(zip(scores_a, scores_b)):
        if sa > 0 and sb > 0:
            pct = (sa - sb) / sa * 100 if not higher_better else (sb - sa) / sa * 100
            color  = GOOD_COLOR if pct > 0 else BAD_COLOR
            prefix = '+' if pct > 0 else ''
            # Draw a subtle badge rectangle
            badge_y = y[i] - 0.30
            rect = mpatches.FancyBboxPatch(
                (badge_x - x_max * 0.055, badge_y),
                x_max * 0.11, 0.60,
                boxstyle='round,pad=0.01',
                facecolor=to_rgba(color, 0.10),
                edgecolor=to_rgba(color, 0.50),
                linewidth=1.2,
                clip_on=False,
            )
            ax.add_patch(rect)
            ax.text(badge_x, y[i], f'{prefix}{pct:.1f}%',
                    va='center', ha='center', fontsize=11,
                    fontweight='bold', color=color, clip_on=False)

    ax.set_yticks(y)
    ax.set_yticklabels(tick_labels, fontsize=11)
    ax.invert_yaxis()

    ax.set_xlabel(unit, fontsize=13, labelpad=8, color=MUTED)
    ax.tick_params(axis='x', labelsize=11, colors=MUTED)
    ax.tick_params(axis='y', colors=TEXT_COLOR)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.9, linestyle='--', alpha=0.9)
    ax.set_axisbelow(True)

    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    for spine in ('bottom', 'left'):
        ax.spines[spine].set_edgecolor(GRID_COLOR)

    # Legend
    legend = ax.legend(
        fontsize=13, framealpha=0.95,
        loc='lower right',
        edgecolor=GRID_COLOR,
        handlelength=1.4,
        handleheight=1.4,
    )
    for text in legend.get_texts():
        text.set_color(TEXT_COLOR)

    title = (f'{label_a}  vs  {label_b}  —  JMH Performance Benchmark\n'
             f'{unit}   •   {arrow}')
    ax.set_title(title, fontsize=15, fontweight='bold',
                 color=TEXT_COLOR, pad=16, linespacing=1.6)

    fig.tight_layout(rect=[0, 0, 0.98, 1])
    fig.savefig(out_path, facecolor=BG_COLOR)
    plt.close(fig)
    print(f'  ✓  barplot → {out_path}')


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)

    file_a, label_a, file_b, label_b, out_dir = sys.argv[1:6]
    prefix = sys.argv[6] if len(sys.argv) > 6 else 'comparison'

    os.makedirs(out_dir, exist_ok=True)

    print(f'\nGenerating charts: {label_a} vs {label_b}')
    r_a = load_results(file_a)
    r_b = load_results(file_b)

    unit = next(iter(r_a.values()), (None, None, 'ms/op'))[2]
    print(f'  Benchmarks loaded: {len(r_a)} ({label_a}), {len(r_b)} ({label_b}), unit: {unit}')

    draw_table(r_a, r_b, label_a, label_b,
               os.path.join(out_dir, f'{prefix}-table.png'))
    draw_barplot(r_a, r_b, label_a, label_b,
                 os.path.join(out_dir, f'{prefix}-barplot.png'))
    print()


if __name__ == '__main__':
    main()


