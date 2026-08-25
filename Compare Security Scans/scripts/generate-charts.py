#!/usr/bin/env python3
"""
Generate presentation-ready Trivy-vs-Grype comparison charts.
Produces:
  <prefix>-table.png    - table: each image with Grype and Trivy counts side by side
  <prefix>-barplot.png  - grouped bar chart: Grype vs Trivy total per image
Usage:
  python3 generate-charts.py <trivy_dir> <grype_dir> <output_dir> [--title "..."] [--prefix scan]
"""
import json, sys, os, glob, argparse, subprocess
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
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BG_COLOR   = "#F8F9FC"
GRID_COLOR = "#DDE1EA"
TEXT_COLOR = "#1A1D23"
MUTED      = "#6B7280"
SEV_ORDER  = ["CRITICAL","HIGH","MEDIUM","LOW","UNKNOWN"]
TOOL_COLORS = {"Grype":"#E65100","Trivy":"#1565C0"}
def filename_to_image(fname):
    # Fallback only: images.conf's image_to_filename maps BOTH '/' and ':' to '_'
    # (tr '/:' '__'), so this reverse mapping is lossy/ambiguous (e.g.
    # "gcr.io/distroless/base-debian13" and a hypothetical "gcr.io:distroless:..."
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
def norm_sev(s):
    # Shared by load_osv() below — mirrors the JQ_SEVERITY bucketing in
    # OSV/scripts/compare-images.sh so the HTML report and the CLI table
    # agree. GHSA-derived advisories use LOW/MODERATE/HIGH/CRITICAL; some
    # vendor feeds (e.g. Ubuntu's OSV data) use low/medium/high/critical or
    # importance words like "important"/"negligible"/"unimportant".
    u = s.upper()
    if u == "CRITICAL": return "CRITICAL"
    if u in ("HIGH", "IMPORTANT"): return "HIGH"
    if u in ("MEDIUM", "MODERATE"): return "MEDIUM"
    if u in ("LOW", "NEGLIGIBLE", "UNIMPORTANT"): return "LOW"
    return "UNKNOWN"
def osv_severity(vuln):
    # See OSV/scripts/compare-images.sh's JQ_SEVERITY for the full rationale.
    ds = (vuln.get("database_specific") or {}).get("severity")
    if isinstance(ds, str) and ds:
        return norm_sev(ds)
    vendor = [s for s in (vuln.get("severity") or []) if s.get("type") not in ("CVSS_V2", "CVSS_V3", "CVSS_V4")]
    if vendor:
        score = vendor[0].get("score")
        if isinstance(score, str) and score:
            return norm_sev(score)
    return "UNKNOWN"  # no rating available (common for Debian OS CVEs, Go stdlib advisories, ...)
def osv_cve_alias(vuln):
    # Mirrors grype_cve_alias() below: prefer a real CVE id so OSV findings
    # line up with Trivy/Grype's CVE-keyed ids in cross-tool comparisons.
    vid = vuln.get("id", "")
    if vid.startswith("CVE-"):
        return vid
    for rid in (vuln.get("aliases") or []) + (vuln.get("upstream") or []):
        if rid.startswith("CVE-"):
            return rid
    return vid  # no CVE alias exists — genuinely OSV-only (e.g. a GO-* or plain UBUNTU-CVE-* id)
def load_osv(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    # OSV's image-scan JSON carries no image name/tag anywhere in it (unlike
    # Trivy's ArtifactName / Grype's source.target.userInput) — fall back to
    # the filename every time; load_all() below only uses this if trivy/grype
    # didn't already supply a nicer name for the same image.
    name = filename_to_image(path)
    seen, cross_ids, counts = set(), set(), {s:0 for s in SEV_ORDER}
    for result in data.get("results") or []:
        for pkg in result.get("packages") or []:
            for vuln in pkg.get("vulnerabilities") or []:
                vid = vuln.get("id","")
                if vid in seen:
                    continue
                seen.add(vid)
                counts[osv_severity(vuln)] += 1
                cross_ids.add(osv_cve_alias(vuln))
    counts["_total"] = sum(counts[s] for s in SEV_ORDER)
    return name, counts, cross_ids
def grype_cve_alias(match):
    # Grype often reports app-layer findings under a GHSA-* id while Trivy reports
    # the exact same vulnerability under its CVE-* id (e.g. GHSA-jjjh-jjxp-wpff is
    # CVE-2022-42003 — confirmed via Grype's own relatedVulnerabilities). Comparing
    # raw ids would then count that single, shared finding as "unique" to BOTH
    # tools at once. Grype's relatedVulnerabilities carries the NVD CVE alias when
    # one exists, so prefer that for any cross-tool (Grype vs Trivy) comparison.
    vid = match.get("vulnerability", {}).get("id", "")
    if vid.startswith("CVE-"):
        return vid
    for related in match.get("relatedVulnerabilities") or []:
        rid = related.get("id", "")
        if rid.startswith("CVE-"):
            return rid
    return vid  # no NVD CVE alias exists (yet) — genuinely Grype-only
def load_grype(path):
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    name = data.get("source",{}).get("target",{}).get("userInput") or filename_to_image(path)
    seen, cross_ids, counts = set(), set(), {s:0 for s in SEV_ORDER}
    for match in data.get("matches",[]):
        vid = match.get("vulnerability",{}).get("id","")
        sev = match.get("vulnerability",{}).get("severity","UNKNOWN").upper()
        cross_ids.add(grype_cve_alias(match))
        if vid not in seen:
            seen.add(vid)
            counts[sev if sev in counts else "UNKNOWN"] += 1
    counts["_total"] = sum(counts[s] for s in SEV_ORDER)
    return name, counts, cross_ids
def load_image_order(repo_root=REPO_ROOT):
    # images.conf (bash) is the single source of truth for image order too —
    # read ALL_IMAGES directly (by asking bash to source it) so every report
    # table/chart lists images in the same order they're pulled/built/scanned
    # in, instead of a sort-by-CVE-count order that reshuffles rows every run.
    # Mirrors load_java_base_image_names() in
    # Compare Security Scans/scripts/generate-html-report.py.
    images_conf = os.path.join(repo_root, "images.conf")
    script = 'source "$1"; printf "%s\\n" "${ALL_IMAGES[@]}"'
    try:
        result = subprocess.run(
            ["bash", "-c", script, "bash", images_conf],
            capture_output=True, text=True, check=True,
        )
        return [line for line in result.stdout.splitlines() if line]
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        # Wrong-but-safe fallback: unlisted images just fall back to sorting
        # by Trivy total, same as before this ordering existed.
        print(f"  WARN could not read ALL_IMAGES from {images_conf}: {e}")
        return []
def load_owasp(path):
    # OWASP Dependency Check's JSON report (Vulnerable Application/target/
    # dependency-check-report.json) — a single flat report for the whole app,
    # not one per Docker image (every hello-conference:* image embeds the same
    # jar, so this same report applies to all of them equally). Mirrors
    # Compare Security Scans/scripts/compare.sh's count_owasp() jq: dedup by
    # vulnerability .name (its CVE/advisory id), severity matched
    # case-insensitively.
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    seen, counts = set(), {s: 0 for s in SEV_ORDER}
    for dep in data.get("dependencies") or []:
        for vuln in dep.get("vulnerabilities") or []:
            vid = vuln.get("name", "")
            if vid in seen:
                continue
            seen.add(vid)
            sev = (vuln.get("severity") or "UNKNOWN").upper()
            counts[sev if sev in counts else "UNKNOWN"] += 1
    counts["_total"] = sum(counts[s] for s in SEV_ORDER)
    return counts, seen
def load_all(trivy_dir, grype_dir, osv_dir=None, owasp_ids=None):
    # owasp_ids: CVE ids from OWASP Dependency Check (see load_owasp() above),
    # folded into the Grype/Trivy/OSV "unique" columns below so e.g. a CVE
    # Grype found that OWASP DC *also* found no longer counts as "unique to
    # Grype". OWASP only scans the app layer (Vulnerable Application/pom.xml),
    # so this only ever changes counts for hello-conference:* images in
    # practice — subtracting it from base-OS images is a harmless no-op since
    # those CVE ids don't overlap.
    owasp_ids = owasp_ids or set()
    # Keyed by filename stem (stable join key — identical across the trivy/grype/osv
    # dirs since all three are produced by the same images.conf#image_to_filename).
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
    for path in sorted(glob.glob(os.path.join(osv_dir, "*.json"))) if osv_dir else []:
        key = os.path.splitext(os.path.basename(path))[0]
        try:
            name, counts, ids = load_osv(path)
            entry = results.setdefault(key, {})
            entry.setdefault("name", name)
            entry["osv"] = counts
            entry["osv_ids"] = ids
        except Exception as e: print(f"  WARN osv {path}: {e}")
    # Sort by Trivy total desc
    empty = {"_total":0,"CRITICAL":0,"HIGH":0,"MEDIUM":0,"LOW":0,"UNKNOWN":0}
    items = []
    all_ids = set()  # every CVE id seen by Grype/Trivy/OSV, across every image — used below for the OWASP "unique" count
    for key, data in results.items():
        grype_ids = data.get("grype_ids", set())
        trivy_ids = data.get("trivy_ids", set())
        osv_ids = data.get("osv_ids", set())
        all_ids |= grype_ids | trivy_ids | osv_ids
        items.append((
            data.get("name", filename_to_image(key)),
            data.get("grype", empty),
            data.get("trivy", empty),
            data.get("osv", empty),
            len(grype_ids - trivy_ids - osv_ids - owasp_ids),   # unique to Grype: found by Grype, not by Trivy, OSV, or OWASP DC
            len(trivy_ids - grype_ids - osv_ids - owasp_ids),   # unique to Trivy: found by Trivy, not by Grype, OSV, or OWASP DC
            len(osv_ids - grype_ids - trivy_ids - owasp_ids),   # unique to OSV: found by OSV, not by Grype, Trivy, or OWASP DC
        ))
    order = load_image_order()
    order_index = {name: i for i, name in enumerate(order)}
    # images.conf order first; images not listed there (shouldn't normally
    # happen) sort after all known ones, by Trivy total desc as before.
    items.sort(key=lambda x: (order_index.get(x[0], len(order)), -x[2]["_total"]))
    # unique to OWASP DC: found by OWASP DC, not by Grype, Trivy, or OSV in any scanned image
    owasp_unique = len(owasp_ids - all_ids)
    return items, owasp_unique
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
    parser.add_argument("--osv-dir", default=None, help="Optional OSV-Scanner JSON results dir (adds it to the unique-CVE comparison)")
    parser.add_argument("--title", default="Container Image CVE Comparison — Trivy vs Grype")
    parser.add_argument("--prefix", default="scan")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"\nLoading results: trivy={args.trivy_dir}  grype={args.grype_dir}  osv={args.osv_dir}")
    items, _owasp_unique = load_all(args.trivy_dir, args.grype_dir, args.osv_dir)
    if not items:
        print("  No JSON files found."); sys.exit(0)
    print(f"  Images: {len(items)}")
    print_text_table(items)
    draw_barplot(items, args.title, os.path.join(args.output_dir, f"{args.prefix}-barplot.png"))
    print()
if __name__ == "__main__":
    main()
