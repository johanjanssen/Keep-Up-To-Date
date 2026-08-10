#!/usr/bin/env python3
"""
Generate presentation-ready charts from JMH JSON result files.

Modes:
  Speed comparison (default):
    python3 generate-charts.py <a.json> <label_a> <b.json> <label_b> <out_dir> [prefix]

  Memory comparison (reads gc.alloc.rate.norm from secondaryMetrics):
    python3 generate-charts.py --memory <a.json> <label_a> <b.json> <label_b> <out_dir> [prefix]

Produces:
  <prefix>-table.png    — colour-coded comparison table
  <prefix>-barplot.png  — horizontal grouped bar chart, legend below the plot
"""

import json, sys, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
from matplotlib.colors import to_rgba

rcParams['font.family']        = 'DejaVu Sans'
rcParams['figure.dpi']         = 150
rcParams['savefig.dpi']        = 150
rcParams['savefig.bbox']       = 'tight'
rcParams['savefig.pad_inches'] = 0.20

BG_COLOR   = '#F8F9FC'
GRID_COLOR = '#DDE1EA'
TEXT_COLOR = '#1A1D23'
MUTED      = '#6B7280'
HEADER_BG  = '#1A237E'
HEADER_FG  = '#FFFFFF'
ALT_ROW    = '#EEF2FF'
GOOD_COLOR = '#1B5E20'
BAD_COLOR  = '#B71C1C'
VERSION_COLORS = {'17': '#D84315', '25': '#1565C0', '28': '#6A1B9A', '21': '#00695C'}

def _version_color(label):
    for ver, color in VERSION_COLORS.items():
        if ver in label:
            return color
    return '#37474F'

# JMH GC profiler key (contains a middle-dot prefix)
GC_METRIC_KEYS = ['\u00b7gc.alloc.rate.norm', 'gc.alloc.rate.norm',
                  '\u00b7gc.alloc.rate',      'gc.alloc.rate']

def load_results(path, memory=False):
    with open(path, encoding='utf-8-sig') as f:
        data = json.load(f)
    results = {}
    for entry in data:
        method = entry['benchmark'].split('.')[-1]
        params = entry.get('params', {})
        if params:
            parts = [f"{k}={int(v):,}" if str(v).isdigit() else f"{k}={v}"
                     for k, v in sorted(params.items())]
            name = method + '  (' + ', '.join(parts) + ')'
        else:
            name = method
        if memory:
            sec = entry.get('secondaryMetrics', {})
            for key in GC_METRIC_KEYS:
                if key in sec:
                    results[name] = (sec[key]['score'], sec[key].get('scoreUnit', 'B/op'))
                    break
        else:
            results[name] = (entry['primaryMetric']['score'],
                             entry['primaryMetric']['scoreUnit'])
    return results

def improvement(s_a, s_b, unit):
    if not s_a or not s_b or s_a == 0:
        return '—', None
    higher_better = 'ops' in unit.lower()
    pct = (s_b - s_a) / s_a * 100 if higher_better else (s_a - s_b) / s_a * 100
    return (f"+{pct:.1f}%" if pct >= 0 else f"{pct:.1f}%"), pct > 0

def draw_table(r_a, r_b, label_a, label_b, out_path, memory=False):
    benchmarks = sorted(set(r_a) | set(r_b))
    if not benchmarks:
        return
    unit  = next(iter(r_a.values()), (None, 'ms/op'))[1]
    arrow = '↓ lower = better' if ('ms' in unit or 'b/op' in unit.lower()) else '↑ higher = better'
    rows = []
    for name in benchmarks:
        sa = r_a.get(name, (None,))[0]
        sb = r_b.get(name, (None,))[0]
        imp_txt, imp_pos = improvement(sa, sb, unit)
        rows.append((name,
                     f'{sa:,.1f}' if sa is not None else '—',
                     f'{sb:,.1f}' if sb is not None else '—',
                     imp_txt, imp_pos))
    n   = len(rows)
    HDR = ['Benchmark', label_a, label_b, f'{label_b} vs {label_a}', 'Unit']
    C_W = [0.42, 0.13, 0.13, 0.17, 0.10]
    fig_h = max(4.0, 1.4 + n * 0.54)
    fig, ax = plt.subplots(figsize=(15, fig_h), facecolor=BG_COLOR)
    ax.axis('off')
    tbl = ax.table(cellText=[[r[0],r[1],r[2],r[3],unit] for r in rows],
                   colLabels=HDR, loc='center', cellLoc='center', colWidths=C_W)
    tbl.auto_set_font_size(False); tbl.set_fontsize(12); tbl.scale(1, 1.65)
    for j in range(len(HDR)):
        c = tbl[0, j]; c.set_facecolor(HEADER_BG)
        c.set_text_props(color=HEADER_FG, fontweight='bold', fontsize=13)
        c.set_edgecolor('#0D1257')
    for i, (_, _, _, _, imp_pos) in enumerate(rows):
        bg = ALT_ROW if i % 2 == 0 else 'white'
        for j in range(len(HDR)):
            cell = tbl[i+1, j]; cell.set_facecolor(bg)
            cell.set_edgecolor(GRID_COLOR); cell.set_text_props(color=TEXT_COLOR, fontsize=12)
        tbl[i+1, 0].set_text_props(ha='left', fontsize=11); tbl[i+1, 0].PAD = 0.04
        tbl[i+1, 1].set_text_props(fontweight='bold', color=_version_color(label_a))
        tbl[i+1, 2].set_text_props(fontweight='bold', color=_version_color(label_b))
        imp_cell = tbl[i+1, 3]
        if imp_pos is True:   imp_cell.set_text_props(color=GOOD_COLOR, fontweight='bold', fontsize=13)
        elif imp_pos is False: imp_cell.set_text_props(color=BAD_COLOR,  fontweight='bold', fontsize=13)
    mode_label = 'Memory Allocation' if memory else 'JMH Performance'
    ax.set_title(f'{label_a}  vs  {label_b}  —  {mode_label} Comparison\n{unit}   •   {arrow}',
                 fontsize=15, fontweight='bold', color=TEXT_COLOR, pad=16, linespacing=1.6)
    fig.savefig(out_path, facecolor=BG_COLOR); plt.close(fig)
    print(f'  ✓  table  → {out_path}')

def _val_label(score, memory):
    if memory:
        if score >= 1_000_000: return f'{score/1_000_000:,.1f} MB'
        if score >= 1_000:     return f'{score/1_000:,.1f} KB'
    return f'{score:,.1f}'

def draw_barplot(r_a, r_b, label_a, label_b, out_path, memory=False):
    benchmarks = sorted(set(r_a) | set(r_b))
    if not benchmarks:
        return
    unit     = next(iter(r_a.values()), (None, 'ms/op'))[1]
    arrow    = '↓ lower = better' if ('ms' in unit or 'b/op' in unit.lower()) else '↑ higher = better'
    col_a    = _version_color(label_a)
    col_b    = _version_color(label_b)
    n        = len(benchmarks)
    scores_a = [r_a.get(b, (0,))[0] or 0.0 for b in benchmarks]
    scores_b = [r_b.get(b, (0,))[0] or 0.0 for b in benchmarks]
    tick_labels = [b.replace('  (', '\n(') for b in benchmarks]

    fig_h = max(8, n * 1.05 + 3.5)
    fig, ax = plt.subplots(figsize=(16, fig_h), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    fig.subplots_adjust(bottom=0.13)   # room for legend below

    y = np.arange(n); bar_h = 0.35
    # No error bars
    bars_a = ax.barh(y + bar_h/2, scores_a, bar_h, label=label_a, color=col_a, alpha=0.88)
    bars_b = ax.barh(y - bar_h/2, scores_b, bar_h, label=label_b, color=col_b, alpha=0.88)

    all_scores = [s for s in scores_a + scores_b if s > 0]
    x_max      = max(all_scores) if all_scores else 1.0
    lspc       = x_max * 0.012

    for bar, score in zip(bars_a, scores_a):
        if score > 0:
            ax.text(score + lspc, bar.get_y() + bar.get_height()/2,
                    _val_label(score, memory), va='center', ha='left',
                    fontsize=10.5, color=TEXT_COLOR, fontweight='bold')
    for bar, score in zip(bars_b, scores_b):
        if score > 0:
            ax.text(score + lspc, bar.get_y() + bar.get_height()/2,
                    _val_label(score, memory), va='center', ha='left',
                    fontsize=10.5, color=TEXT_COLOR, fontweight='bold')

    # Improvement badges (right side)
    higher_better = 'ops' in unit.lower()
    badge_x = x_max * 1.19
    ax.set_xlim(0, x_max * 1.26)
    for i, (sa, sb) in enumerate(zip(scores_a, scores_b)):
        if sa > 0 and sb > 0:
            pct = (sa - sb) / sa * 100 if not higher_better else (sb - sa) / sa * 100
            color = GOOD_COLOR if pct > 0 else BAD_COLOR
            sign  = '+' if pct > 0 else ''
            rect  = mpatches.FancyBboxPatch(
                (badge_x - x_max*0.055, y[i] - 0.30), x_max*0.11, 0.60,
                boxstyle='round,pad=0.01',
                facecolor=to_rgba(color, 0.10), edgecolor=to_rgba(color, 0.50),
                linewidth=1.2, clip_on=False)
            ax.add_patch(rect)
            ax.text(badge_x, y[i], f'{sign}{pct:.1f}%',
                    va='center', ha='center', fontsize=11,
                    fontweight='bold', color=color, clip_on=False)

    ax.set_yticks(y); ax.set_yticklabels(tick_labels, fontsize=11); ax.invert_yaxis()
    ax.set_xlabel(unit, fontsize=13, labelpad=8, color=MUTED)
    ax.tick_params(axis='x', labelsize=11, colors=MUTED)
    ax.tick_params(axis='y', colors=TEXT_COLOR)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.9, linestyle='--', alpha=0.9)
    ax.set_axisbelow(True)
    for sp in ('top','right'):   ax.spines[sp].set_visible(False)
    for sp in ('bottom','left'): ax.spines[sp].set_edgecolor(GRID_COLOR)

    # Legend BELOW the axes
    ax.legend(fontsize=13, framealpha=0.95, loc='upper center',
              bbox_to_anchor=(0.45, -0.07), ncol=2,
              edgecolor=GRID_COLOR, handlelength=1.6, handleheight=1.4)

    mode_label = 'Memory Allocation' if memory else 'JMH Performance'
    ax.set_title(f'{label_a}  vs  {label_b}  —  {mode_label} Benchmark\n{unit}   •   {arrow}',
                 fontsize=15, fontweight='bold', color=TEXT_COLOR, pad=16, linespacing=1.6)
    fig.savefig(out_path, facecolor=BG_COLOR); plt.close(fig)
    print(f'  ✓  barplot → {out_path}')


def main():
    args   = sys.argv[1:]
    memory = False
    if args and args[0] == '--memory':
        memory = True; args = args[1:]
    if len(args) < 5:
        print(__doc__); sys.exit(1)
    file_a, label_a, file_b, label_b, out_dir = args[:5]
    prefix = args[5] if len(args) > 5 else 'comparison'
    os.makedirs(out_dir, exist_ok=True)
    mode = 'memory' if memory else 'speed'
    print(f'\nGenerating {mode} charts: {label_a} vs {label_b}')
    r_a = load_results(file_a, memory=memory)
    r_b = load_results(file_b, memory=memory)
    if not r_a and not r_b:
        print(f'  ⚠  No {"memory" if memory else "primary"} metrics found.')
        if memory:
            print('     Re-run benchmarks with -prof gc to collect GC allocation data.')
        sys.exit(0)
    unit = next(iter(r_a.values()), (None, 'ms/op'))[1]
    print(f'  {len(r_a)} ({label_a}), {len(r_b)} ({label_b}), unit: {unit}')
    draw_table(r_a, r_b, label_a, label_b,
               os.path.join(out_dir, f'{prefix}-table.png'), memory=memory)
    draw_barplot(r_a, r_b, label_a, label_b,
                 os.path.join(out_dir, f'{prefix}-barplot.png'), memory=memory)
    print()

if __name__ == '__main__':
    main()

