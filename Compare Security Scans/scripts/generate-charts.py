#!/usr/bin/env python3
"""
Generate presentation-ready Trivy-vs-Grype comparison charts.
Produces:
  <prefix>-table.png    - table: each image with Grype and Trivy counts side by side
  <prefix>-barplot.png  - grouped bar chart: Grype vs Trivy total per image
Usage:
  python3 generate-charts.py <trivy_dir> <grype_dir> <output_dir> [--title "..."] [--prefix scan]
"""
import json, sys, os, glob, argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams["font.family"]        = "DejaVu Sans"
rcParams["figure.dpi"]         = 150
rcParams["savefig.dpi"]        = 150
rcParams["savefig.bbox"]       = "tight"
rcParams["savefig.pad_inches"] = 0.20
BG_COLOR   = "#F8F9FC"
GRID_COLOR = "#DDE1EA"
TEXT_COLOR = "#1A1D23"
MUTED      = "#6B7280"
HEADER_BG  = "#1A237E"
HEADER_FG  = "#FFFFFF"
ALT_ROW    = "#EEF2FF"
SEV_COLORS = {"CRITICAL":"#B71C1C","HIGH":"#E65100","MEDIUM":"#F9A825","LOW":"#558B2F","UNKNOWN":"#90A4AE"}
SEV_ORDER  = ["CRITICAL","HIGH","MEDIUM","LOW","UNKNOWN"]
TOOL_COLORS = {"Grype":"#E65100","Trivy":"#1565C0"}
def filename_to_image(fname):
    base = os.path.splitext(os.path.basename(fname))[0]
    return base.replace("__",":",1)
def load_trivy(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    seen, counts = set(), {s:0 for s in SEV_ORDER}
    for result in data.get("Results",[]):
        for vuln in result.get("Vulnerabilities") or []:
            vid = vuln.get("VulnerabilityID","")
            sev = vuln.get("Severity","UNKNOWN").upper()
            if vid not in seen:
                seen.add(vid)
                counts[sev if sev in counts else "UNKNOWN"] += 1
    counts["_total"] = sum(counts[s] for s in SEV_ORDER)
    return counts
def load_grype(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    seen, counts = set(), {s:0 for s in SEV_ORDER}
    for match in data.get("matches",[]):
        vid = match.get("vulnerability",{}).get("id","")
        sev = match.get("vulnerability",{}).get("severity","UNKNOWN").upper()
        if vid not in seen:
            seen.add(vid)
            counts[sev if sev in counts else "UNKNOWN"] += 1
    counts["_total"] = sum(counts[s] for s in SEV_ORDER)
    return counts
def load_all(trivy_dir, grype_dir):
    results = {}
    for path in sorted(glob.glob(os.path.join(trivy_dir,"*.json"))):
        img = filename_to_image(path)
        try: results.setdefault(img,{})["trivy"] = load_trivy(path)
        except Exception as e: print(f"  WARN trivy {path}: {e}")
    for path in sorted(glob.glob(os.path.join(grype_dir,"*.json"))):
        img = filename_to_image(path)
        try: results.setdefault(img,{})["grype"] = load_grype(path)
        except Exception as e: print(f"  WARN grype {path}: {e}")
    # Sort by Trivy total desc
    empty = {"_total":0,"CRITICAL":0,"HIGH":0,"MEDIUM":0,"LOW":0,"UNKNOWN":0}
    items = [(img, data.get("grype",empty), data.get("trivy",empty))
             for img, data in results.items()]
    items.sort(key=lambda x: x[2]["_total"], reverse=True)
    return items
def draw_table(items, title, out_path):
    if not items:
        return
    def c(v): return str(v) if v > 0 else "-"
    rows = []
    for img, g, t in items:
        rows.append([img,
                     str(g["_total"]), c(g["CRITICAL"]), c(g["HIGH"]), c(g["MEDIUM"]), c(g["LOW"]),
                     str(t["_total"]), c(t["CRITICAL"]), c(t["HIGH"]), c(t["MEDIUM"]), c(t["LOW"])])
    HDR = ["Image",
           "Grype\nTotal","Crit","High","Med","Low",
           "Trivy\nTotal","Crit","High","Med","Low"]
    C_W = [0.30, 0.07,0.05,0.05,0.05,0.05, 0.07,0.05,0.05,0.05,0.05]
    n = len(rows)
    fig_h = max(4.0, 1.6 + n*0.52)
    fig, ax = plt.subplots(figsize=(18, fig_h), facecolor=BG_COLOR)
    ax.axis("off")
    tbl = ax.table(cellText=rows, colLabels=HDR, loc="center",
                   cellLoc="center", colWidths=C_W)
    tbl.auto_set_font_size(False); tbl.set_fontsize(11); tbl.scale(1, 1.65)
    # Header
    grype_cols = [1,2,3,4,5]; trivy_cols = [6,7,8,9,10]
    for j in range(len(HDR)):
        cell = tbl[0,j]; cell.set_edgecolor("#0D1257")
        if j == 0:
            cell.set_facecolor(HEADER_BG)
            cell.set_text_props(color=HEADER_FG,fontweight="bold",fontsize=12)
        elif j in grype_cols:
            cell.set_facecolor("#BF360C")   # dark orange for Grype header
            cell.set_text_props(color="white",fontweight="bold",fontsize=11)
        else:
            cell.set_facecolor("#0D47A1")   # dark blue for Trivy header
            cell.set_text_props(color="white",fontweight="bold",fontsize=11)
    # Data rows
    sev_col_grype = [(2,"CRITICAL"),(3,"HIGH"),(4,"MEDIUM"),(5,"LOW")]
    sev_col_trivy = [(7,"CRITICAL"),(8,"HIGH"),(9,"MEDIUM"),(10,"LOW")]
    for i, (img, g, t) in enumerate(items):
        bg = ALT_ROW if i%2==0 else "white"
        for j in range(len(HDR)):
            cell = tbl[i+1,j]; cell.set_facecolor(bg)
            cell.set_edgecolor(GRID_COLOR); cell.set_text_props(color=TEXT_COLOR,fontsize=11)
        tbl[i+1,0].set_text_props(ha="left",fontsize=10); tbl[i+1,0].PAD = 0.03
        tbl[i+1,1].set_text_props(fontweight="bold",color=TOOL_COLORS["Grype"],fontsize=12)
        tbl[i+1,6].set_text_props(fontweight="bold",color=TOOL_COLORS["Trivy"],fontsize=12)
        for ci,sev in sev_col_grype:
            if g[sev]>0: tbl[i+1,ci].set_text_props(fontweight="bold",color=SEV_COLORS[sev])
            else: tbl[i+1,ci].set_text_props(color=MUTED)
        for ci,sev in sev_col_trivy:
            if t[sev]>0: tbl[i+1,ci].set_text_props(fontweight="bold",color=SEV_COLORS[sev])
            else: tbl[i+1,ci].set_text_props(color=MUTED)
    ax.set_title(title, fontsize=15, fontweight="bold", color=TEXT_COLOR, pad=16)
    fig.savefig(out_path, facecolor=BG_COLOR); plt.close(fig)
    print(f"  OK  table  -> {out_path}")
def draw_barplot(items, title, out_path):
    if not items:
        return
    labels  = [r[0] for r in items]
    grype_t = np.array([r[1]["_total"] for r in items], dtype=float)
    trivy_t = np.array([r[2]["_total"] for r in items], dtype=float)
    n = len(labels)
    fig_h = max(6, n*0.80 + 3.5)
    fig, ax = plt.subplots(figsize=(16, fig_h), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    fig.subplots_adjust(bottom=0.13)
    y = np.arange(n); bar_h = 0.35
    bars_g = ax.barh(y+bar_h/2, grype_t, bar_h, label="Grype",
                     color=TOOL_COLORS["Grype"], alpha=0.88)
    bars_t = ax.barh(y-bar_h/2, trivy_t, bar_h, label="Trivy",
                     color=TOOL_COLORS["Trivy"], alpha=0.88)
    x_max  = max(grype_t.max(), trivy_t.max(), 1)
    lspc   = x_max * 0.012
    for bar,val in zip(bars_g, grype_t):
        if val>0: ax.text(val+lspc, bar.get_y()+bar.get_height()/2, str(int(val)),
                          va="center",ha="left",fontsize=11,fontweight="bold",color=TEXT_COLOR)
    for bar,val in zip(bars_t, trivy_t):
        if val>0: ax.text(val+lspc, bar.get_y()+bar.get_height()/2, str(int(val)),
                          va="center",ha="left",fontsize=11,fontweight="bold",color=TEXT_COLOR)
    ax.set_xlim(0, x_max*1.22)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=10); ax.invert_yaxis()
    ax.set_xlabel("Unique CVEs (deduplicated by CVE ID)", fontsize=13, labelpad=8, color=MUTED)
    ax.tick_params(axis="x",labelsize=11,colors=MUTED)
    ax.tick_params(axis="y",colors=TEXT_COLOR)
    ax.xaxis.grid(True,color=GRID_COLOR,linewidth=0.9,linestyle="--",alpha=0.9)
    ax.set_axisbelow(True)
    for sp in ("top","right"):   ax.spines[sp].set_visible(False)
    for sp in ("bottom","left"): ax.spines[sp].set_edgecolor(GRID_COLOR)
    ax.legend(fontsize=13,framealpha=0.95,loc="upper center",
              bbox_to_anchor=(0.45,-0.07),ncol=2,edgecolor=GRID_COLOR)
    ax.set_title(title, fontsize=15, fontweight="bold", color=TEXT_COLOR, pad=16)
    fig.savefig(out_path, facecolor=BG_COLOR); plt.close(fig)
    print(f"  OK  barplot -> {out_path}")
def print_text_table(items):
    if not items:
        return
    print("\n" + "="*90)
    print(f"  {'IMAGE':<48}  {'GRYPE':>6}  C/H/M/L   {'TRIVY':>6}  C/H/M/L")
    print("="*90)
    for img, g, t in items:
        g_sev = f"{g['CRITICAL']}/{g['HIGH']}/{g['MEDIUM']}/{g['LOW']}"
        t_sev = f"{t['CRITICAL']}/{t['HIGH']}/{t['MEDIUM']}/{t['LOW']}"
        print(f"  {img:<48}  {g['_total']:>6}  {g_sev:<10}  {t['_total']:>6}  {t_sev}")
    print("="*90)
    print("  C=Critical  H=High  M=Medium  L=Low  (unique CVEs, deduplicated)\n")
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trivy_dir")
    parser.add_argument("grype_dir")
    parser.add_argument("output_dir")
    parser.add_argument("--title", default="Container Image CVE Comparison — Trivy vs Grype")
    parser.add_argument("--prefix", default="scan")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"\nLoading results: trivy={args.trivy_dir}  grype={args.grype_dir}")
    items = load_all(args.trivy_dir, args.grype_dir)
    if not items:
        print("  No JSON files found."); sys.exit(0)
    print(f"  Images: {len(items)}")
    print_text_table(items)
    draw_table(items, args.title, os.path.join(args.output_dir, f"{args.prefix}-table.png"))
    draw_barplot(items, args.title, os.path.join(args.output_dir, f"{args.prefix}-barplot.png"))
    print()
if __name__ == "__main__":
    main()
