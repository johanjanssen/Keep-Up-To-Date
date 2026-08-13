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
SEV_ORDER  = ["CRITICAL","HIGH","MEDIUM","LOW","UNKNOWN"]
TOOL_COLORS = {"Grype":"#E65100","Trivy":"#1565C0"}
def filename_to_image(fname):
    # Fallback only: images.conf's image_to_filename maps BOTH '/' and ':' to '_'
    # (tr '/:' '__'), so this reverse mapping is lossy/ambiguous (e.g.
    # "gcr.io/distroless/base-debian12" and a hypothetical "gcr.io:distroless:..."
    # would collide). Prefer the real name embedded in the JSON (ArtifactName /
    # source.target.userInput) — see load_trivy/load_grype below.
    base = os.path.splitext(os.path.basename(fname))[0]
    return base.replace("_", ":", 1)
def load_trivy(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    name = data.get("ArtifactName") or filename_to_image(path)
    seen, counts = set(), {s:0 for s in SEV_ORDER}
    for result in data.get("Results",[]):
        for vuln in result.get("Vulnerabilities") or []:
            vid = vuln.get("VulnerabilityID","")
            sev = vuln.get("Severity","UNKNOWN").upper()
            if vid not in seen:
                seen.add(vid)
                counts[sev if sev in counts else "UNKNOWN"] += 1
    counts["_total"] = sum(counts[s] for s in SEV_ORDER)
    return name, counts, seen
def load_grype(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    name = data.get("source",{}).get("target",{}).get("userInput") or filename_to_image(path)
    seen, counts = set(), {s:0 for s in SEV_ORDER}
    for match in data.get("matches",[]):
        vid = match.get("vulnerability",{}).get("id","")
        sev = match.get("vulnerability",{}).get("severity","UNKNOWN").upper()
        if vid not in seen:
            seen.add(vid)
            counts[sev if sev in counts else "UNKNOWN"] += 1
    counts["_total"] = sum(counts[s] for s in SEV_ORDER)
    return name, counts, seen
def load_all(trivy_dir, grype_dir):
    # Keyed by filename stem (stable join key — identical between the trivy/grype
    # dirs since both are produced by the same images.conf#image_to_filename).
    # The display name comes from inside the JSON, not from reversing that key.
    results = {}
    for path in sorted(glob.glob(os.path.join(trivy_dir,"*.json"))):
        key = os.path.splitext(os.path.basename(path))[0]
        try:
            name, counts, ids = load_trivy(path)
            entry = results.setdefault(key, {})
            entry["name"] = name
            entry["trivy"] = counts
            entry["trivy_ids"] = ids
        except Exception as e: print(f"  WARN trivy {path}: {e}")
    for path in sorted(glob.glob(os.path.join(grype_dir,"*.json"))):
        key = os.path.splitext(os.path.basename(path))[0]
        try:
            name, counts, ids = load_grype(path)
            entry = results.setdefault(key, {})
            entry.setdefault("name", name)
            entry["grype"] = counts
            entry["grype_ids"] = ids
        except Exception as e: print(f"  WARN grype {path}: {e}")
    # Sort by Trivy total desc
    empty = {"_total":0,"CRITICAL":0,"HIGH":0,"MEDIUM":0,"LOW":0,"UNKNOWN":0}
    items = []
    for key, data in results.items():
        grype_ids = data.get("grype_ids", set())
        trivy_ids = data.get("trivy_ids", set())
        items.append((
            data.get("name", filename_to_image(key)),
            data.get("grype", empty),
            data.get("trivy", empty),
            len(grype_ids - trivy_ids),   # unique to Grype: found by Grype, not by Trivy
            len(trivy_ids - grype_ids),   # unique to Trivy: found by Trivy, not by Grype
        ))
    items.sort(key=lambda x: x[2]["_total"], reverse=True)
    return items
def draw_barplot(items, title, out_path):
    if not items:
        return
    labels  = [r[0] for r in items]
    grype_t = np.array([r[1]["_total"] for r in items], dtype=float)
    trivy_t = np.array([r[2]["_total"] for r in items], dtype=float)
    n = len(labels)
    # Enlarged now that this is the only chart on the report (the table chart was removed).
    fig_h = max(7, n*0.95 + 4.5)
    fig, ax = plt.subplots(figsize=(20, fig_h), facecolor=BG_COLOR)
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
                          va="center",ha="left",fontsize=13,fontweight="bold",color=TEXT_COLOR)
    for bar,val in zip(bars_t, trivy_t):
        if val>0: ax.text(val+lspc, bar.get_y()+bar.get_height()/2, str(int(val)),
                          va="center",ha="left",fontsize=13,fontweight="bold",color=TEXT_COLOR)
    ax.set_xlim(0, x_max*1.22)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=12); ax.invert_yaxis()
    ax.set_xlabel("Unique CVEs (deduplicated by CVE ID)", fontsize=15, labelpad=10, color=MUTED)
    ax.tick_params(axis="x",labelsize=13,colors=MUTED)
    ax.tick_params(axis="y",colors=TEXT_COLOR)
    ax.xaxis.grid(True,color=GRID_COLOR,linewidth=0.9,linestyle="--",alpha=0.9)
    ax.set_axisbelow(True)
    for sp in ("top","right"):   ax.spines[sp].set_visible(False)
    for sp in ("bottom","left"): ax.spines[sp].set_edgecolor(GRID_COLOR)
    ax.legend(fontsize=15,framealpha=0.95,loc="upper center",
              bbox_to_anchor=(0.45,-0.06),ncol=2,edgecolor=GRID_COLOR)
    ax.set_title(title, fontsize=18, fontweight="bold", color=TEXT_COLOR, pad=18)
    fig.savefig(out_path, facecolor=BG_COLOR); plt.close(fig)
    print(f"  OK  barplot -> {out_path}")
def print_text_table(items):
    if not items:
        return
    print("\n" + "="*90)
    print(f"  {'IMAGE':<48}  {'GRYPE':>6}  C/H/M/L   {'TRIVY':>6}  C/H/M/L")
    print("="*90)
    for img, g, t, *_ in items:
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
    draw_barplot(items, args.title, os.path.join(args.output_dir, f"{args.prefix}-barplot.png"))
    print()
if __name__ == "__main__":
    main()
