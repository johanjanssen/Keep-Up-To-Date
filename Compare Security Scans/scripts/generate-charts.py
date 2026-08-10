#!/usr/bin/env python3
"""
Generate presentation-ready security scan comparison charts from Trivy JSON results.
Produces (in <output_dir>/):
  <prefix>-table.png    - colour-coded CVE comparison table
  <prefix>-barplot.png  - horizontal stacked-severity bar chart
Usage:
  python3 generate-charts.py <trivy_results_dir> <output_dir> [--title "..."] [--prefix scan]
"""
import json, sys, os, glob, argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
SEV_COLORS = {
    'CRITICAL': '#B71C1C',
    'HIGH':     '#E65100',
    'MEDIUM':   '#F9A825',
    'LOW':      '#558B2F',
    'UNKNOWN':  '#90A4AE',
}
SEV_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']
def filename_to_image(fname):
    base = os.path.splitext(os.path.basename(fname))[0]
    return base.replace('__', ':', 1)
def load_trivy_json(path):
    with open(path, encoding='utf-8-sig') as f:
        data = json.load(f)
    seen   = set()
    counts = {s: 0 for s in SEV_ORDER}
    for result in data.get('Results', []):
        for vuln in result.get('Vulnerabilities') or []:
            vid = vuln.get('VulnerabilityID', '')
            sev = vuln.get('Severity', 'UNKNOWN').upper()
            if vid not in seen:
                seen.add(vid)
                counts[sev if sev in counts else 'UNKNOWN'] += 1
    counts['_total'] = sum(counts[s] for s in SEV_ORDER)
    return counts
def load_all_results(trivy_dir):
    results = []
    for path in sorted(glob.glob(os.path.join(trivy_dir, '*.json'))):
        try:
            results.append((filename_to_image(path), load_trivy_json(path)))
        except Exception as e:
            print(f'  WARNING: skipping {path}: {e}')
    results.sort(key=lambda x: x[1]['_total'], reverse=True)
    return results
def draw_table(results, title, out_path):
    if not results:
        return
    HDR = ['Image', 'Total', 'Critical', 'High', 'Medium', 'Low', 'Unknown']
    C_W = [0.38, 0.08, 0.10, 0.08, 0.10, 0.08, 0.10]
    rows = [[r[0], str(r[1]['_total']), str(r[1]['CRITICAL']), str(r[1]['HIGH']),
             str(r[1]['MEDIUM']), str(r[1]['LOW']), str(r[1]['UNKNOWN'])]
            for r in results]
    n = len(rows)
    fig_h = max(4.0, 1.4 + n * 0.52)
    fig, ax = plt.subplots(figsize=(15, fig_h), facecolor=BG_COLOR)
    ax.axis('off')
    tbl = ax.table(cellText=rows, colLabels=HDR, loc='center',
                   cellLoc='center', colWidths=C_W)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    tbl.scale(1, 1.65)
    for j in range(len(HDR)):
        c = tbl[0, j]
        c.set_facecolor(HEADER_BG)
        c.set_text_props(color=HEADER_FG, fontweight='bold', fontsize=13)
        c.set_edgecolor('#0D1257')
    sev_col_map = [(2,'CRITICAL'),(3,'HIGH'),(4,'MEDIUM'),(5,'LOW'),(6,'UNKNOWN')]
    for i, (label, counts) in enumerate(results):
        bg = ALT_ROW if i % 2 == 0 else 'white'
        for j in range(len(HDR)):
            cell = tbl[i+1, j]
            cell.set_facecolor(bg)
            cell.set_edgecolor(GRID_COLOR)
            cell.set_text_props(color=TEXT_COLOR, fontsize=12)
        tbl[i+1, 0].set_text_props(ha='left', fontsize=10.5)
        tbl[i+1, 0].PAD = 0.03
        tbl[i+1, 1].set_text_props(fontweight='bold', fontsize=13)
        for ci, sev in sev_col_map:
            cell = tbl[i+1, ci]
            if counts[sev] > 0:
                cell.set_text_props(fontweight='bold', color=SEV_COLORS[sev])
            else:
                cell.set_text_props(color=MUTED)
    ax.set_title(title, fontsize=15, fontweight='bold', color=TEXT_COLOR, pad=16)
    fig.savefig(out_path, facecolor=BG_COLOR)
    plt.close(fig)
    print(f'  OK  table  -> {out_path}')
def draw_barplot(results, title, out_path):
    if not results:
        return
    labels = [r[0] for r in results]
    n = len(labels)
    fig_h = max(6, n * 0.72 + 3.0)
    fig, ax = plt.subplots(figsize=(16, fig_h), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    y = np.arange(n)
    bar_h = 0.55
    lefts = np.zeros(n)
    for sev in SEV_ORDER:
        vals = np.array([r[1][sev] for r in results], dtype=float)
        if vals.sum() == 0:
            continue
        bars = ax.barh(y, vals, bar_h, left=lefts, label=sev.capitalize(),
                       color=SEV_COLORS[sev], alpha=0.90)
        x_range = lefts.max() + vals.max()
        for bar, val, left in zip(bars, vals, lefts):
            if val > 0 and bar.get_width() > x_range * 0.035:
                ax.text(left + bar.get_width()/2,
                        bar.get_y() + bar.get_height()/2,
                        str(int(val)), va='center', ha='center',
                        fontsize=9.5, fontweight='bold', color='white')
        lefts += vals
    x_max = lefts.max() if lefts.max() > 0 else 1.0
    for i, total_x in enumerate(lefts):
        t = results[i][1]['_total']
        if t > 0:
            ax.text(total_x + x_max*0.013, y[i], f'  {t}',
                    va='center', ha='left', fontsize=12,
                    fontweight='bold', color=TEXT_COLOR)
    ax.set_xlim(0, x_max * 1.18)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel('Unique CVEs (deduplicated by CVE ID)', fontsize=13, labelpad=8, color=MUTED)
    ax.tick_params(axis='x', labelsize=11, colors=MUTED)
    ax.tick_params(axis='y', colors=TEXT_COLOR)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.9, linestyle='--', alpha=0.9)
    ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    for sp in ('bottom','left'): ax.spines[sp].set_edgecolor(GRID_COLOR)
    ax.legend(title='Severity', title_fontsize=12, fontsize=12, framealpha=0.95,
              loc='lower right', edgecolor=GRID_COLOR, ncol=5)
    ax.set_title(title, fontsize=15, fontweight='bold', color=TEXT_COLOR, pad=16)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=BG_COLOR)
    plt.close(fig)
    print(f'  OK  barplot -> {out_path}')
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('trivy_dir')
    parser.add_argument('output_dir')
    parser.add_argument('--title', default='Container Image CVE Comparison — Trivy')
    parser.add_argument('--prefix', default='scan')
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    print(f'\nLoading Trivy results from: {args.trivy_dir}')
    results = load_all_results(args.trivy_dir)
    if not results:
        print('  No JSON files found.')
        sys.exit(0)
    print(f'  Images: {len(results)}')
    draw_table(results, args.title, os.path.join(args.output_dir, f'{args.prefix}-table.png'))
    draw_barplot(results, args.title, os.path.join(args.output_dir, f'{args.prefix}-barplot.png'))
    print()
if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Generate presentation-ready security scan comparison charts from Trivy JSON results.
Produces (in <output_dir>/):
  <prefix>-table.png    - colour-coded CVE comparison table
  <prefix>-barplot.png  - horizontal stacked-severity bar chart
Usage:
  python3 generate-charts.py <trivy_results_dir> <output_dir> [--title "..."] [--prefix scan]
"""
import json, sys, os, glob, argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
SEV_COLORS = {
    'CRITICAL': '#B71C1C',
    'HIGH':     '#E65100',
    'MEDIUM':   '#F9A825',
    'LOW':      '#558B2F',
    'UNKNOWN':  '#90A4AE',
}
SEV_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']
def filename_to_image(fname):
    base = os.path.splitext(os.path.basename(fname))[0]
    return base.replace('__', ':', 1)
def load_trivy_json(path):
    with open(path) as f:
        data = json.load(f)
    seen   = set()
    counts = {s: 0 for s in SEV_ORDER}
    for result in data.get('Results', []):
        for vuln in result.get('Vulnerabilities') or []:
            vid = vuln.get('VulnerabilityID', '')
            sev = vuln.get('Severity', 'UNKNOWN').upper()
            if vid not in seen:
                seen.add(vid)
                counts[sev if sev in counts else 'UNKNOWN'] += 1
    counts['_total'] = sum(counts[s] for s in SEV_ORDER)
    return counts
def load_all_results(trivy_dir):
    results = []
    for path in sorted(glob.glob(os.path.join(trivy_dir, '*.json'))):
        try:
            results.append((filename_to_image(path), load_trivy_json(path)))
        except Exception as e:
            print(f'  WARNING: skipping {path}: {e}')
    results.sort(key=lambda x: x[1]['_total'], reverse=True)
    return results
def draw_table(results, title, out_path):
    if not results:
        return
    HDR = ['Image', 'Total', 'Critical', 'High', 'Medium', 'Low', 'Unknown']
    C_W = [0.38, 0.08, 0.10, 0.08, 0.10, 0.08, 0.10]
    rows = [[r[0], str(r[1]['_total']), str(r[1]['CRITICAL']), str(r[1]['HIGH']),
             str(r[1]['MEDIUM']), str(r[1]['LOW']), str(r[1]['UNKNOWN'])]
            for r in results]
    n = len(rows)
    fig_h = max(4.0, 1.4 + n * 0.52)
    fig, ax = plt.subplots(figsize=(15, fig_h), facecolor=BG_COLOR)
    ax.axis('off')
    tbl = ax.table(cellText=rows, colLabels=HDR, loc='center',
                   cellLoc='center', colWidths=C_W)
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(12)
    tbl.scale(1, 1.65)
    for j in range(len(HDR)):
        c = tbl[0, j]
        c.set_facecolor(HEADER_BG)
        c.set_text_props(color=HEADER_FG, fontweight='bold', fontsize=13)
        c.set_edgecolor('#0D1257')
    sev_col_map = [(2,'CRITICAL'),(3,'HIGH'),(4,'MEDIUM'),(5,'LOW'),(6,'UNKNOWN')]
    for i, (label, counts) in enumerate(results):
        bg = ALT_ROW if i % 2 == 0 else 'white'
        for j in range(len(HDR)):
            cell = tbl[i+1, j]
            cell.set_facecolor(bg)
            cell.set_edgecolor(GRID_COLOR)
            cell.set_text_props(color=TEXT_COLOR, fontsize=12)
        tbl[i+1, 0].set_text_props(ha='left', fontsize=10.5)
        tbl[i+1, 0].PAD = 0.03
        tbl[i+1, 1].set_text_props(fontweight='bold', fontsize=13)
        for ci, sev in sev_col_map:
            cell = tbl[i+1, ci]
            if counts[sev] > 0:
                cell.set_text_props(fontweight='bold', color=SEV_COLORS[sev])
            else:
                cell.set_text_props(color=MUTED)
    ax.set_title(title, fontsize=15, fontweight='bold', color=TEXT_COLOR, pad=16)
    fig.savefig(out_path, facecolor=BG_COLOR)
    plt.close(fig)
    print(f'  OK  table  -> {out_path}')
def draw_barplot(results, title, out_path):
    if not results:
        return
    labels = [r[0] for r in results]
    n = len(labels)
    fig_h = max(6, n * 0.72 + 3.0)
    fig, ax = plt.subplots(figsize=(16, fig_h), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    y = np.arange(n)
    bar_h = 0.55
    lefts = np.zeros(n)
    for sev in SEV_ORDER:
        vals = np.array([r[1][sev] for r in results], dtype=float)
        if vals.sum() == 0:
            continue
        bars = ax.barh(y, vals, bar_h, left=lefts, label=sev.capitalize(),
                       color=SEV_COLORS[sev], alpha=0.90)
        x_range = lefts.max() + vals.max()
        for bar, val, left in zip(bars, vals, lefts):
            if val > 0 and bar.get_width() > x_range * 0.035:
                ax.text(left + bar.get_width()/2,
                        bar.get_y() + bar.get_height()/2,
                        str(int(val)), va='center', ha='center',
                        fontsize=9.5, fontweight='bold', color='white')
        lefts += vals
    x_max = lefts.max() if lefts.max() > 0 else 1.0
    for i, total_x in enumerate(lefts):
        t = results[i][1]['_total']
        if t > 0:
            ax.text(total_x + x_max*0.013, y[i], f'  {t}',
                    va='center', ha='left', fontsize=12,
                    fontweight='bold', color=TEXT_COLOR)
    ax.set_xlim(0, x_max * 1.18)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel('Unique CVEs (deduplicated by CVE ID)', fontsize=13, labelpad=8, color=MUTED)
    ax.tick_params(axis='x', labelsize=11, colors=MUTED)
    ax.tick_params(axis='y', colors=TEXT_COLOR)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.9, linestyle='--', alpha=0.9)
    ax.set_axisbelow(True)
    for sp in ('top','right'): ax.spines[sp].set_visible(False)
    for sp in ('bottom','left'): ax.spines[sp].set_edgecolor(GRID_COLOR)
    ax.legend(title='Severity', title_fontsize=12, fontsize=12, framealpha=0.95,
              loc='lower right', edgecolor=GRID_COLOR, ncol=5)
    ax.set_title(title, fontsize=15, fontweight='bold', color=TEXT_COLOR, pad=16)
    fig.tight_layout()
    fig.savefig(out_path, facecolor=BG_COLOR)
    plt.close(fig)
    print(f'  OK  barplot -> {out_path}')
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('trivy_dir')
    parser.add_argument('output_dir')
    parser.add_argument('--title', default='Container Image CVE Comparison — Trivy')
    parser.add_argument('--prefix', default='scan')
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    print(f'\nLoading Trivy results from: {args.trivy_dir}')
    results = load_all_results(args.trivy_dir)
    if not results:
        print('  No JSON files found.')
        sys.exit(0)
    print(f'  Images: {len(results)}')
    draw_table(results, args.title, os.path.join(args.output_dir, f'{args.prefix}-table.png'))
    draw_barplot(results, args.title, os.path.join(args.output_dir, f'{args.prefix}-barplot.png'))
    print()
if __name__ == '__main__':
    main()
