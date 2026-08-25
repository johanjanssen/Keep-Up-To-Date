#!/usr/bin/env python3
"""
Generate two self-contained static HTML severity-comparison reports
(Grype vs Trivy vs OSV-Scanner, plus OWASP Dependency Check on the app page)
from Trivy/Grype/OSV-Scanner/OWASP-DC JSON scan results:

  - a "base images" report (generic OS images + Java runtime images) — the
    general-purpose comparison, published at /image-scans
  - a "custom images" report (hello-conference app images only) — the
    app-specific comparison, published at /custom-image-scans, with an added
    one-row OWASP Dependency Check table (see --owasp-json) since OWASP DC
    scans the app's dependency tree once, not per Docker image

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Usage:
  python3 generate-html-report.py <trivy_dir> <grype_dir> <osv_dir> \\
      <base_output_html> <custom_output_html> [--title "..."] [--custom-title "..."] \\
      [--owasp-json "..."]
"""
import argparse, html, importlib.util, json, os, subprocess
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

# Reuse the (already-fixed) JSON loading/aggregation logic from generate-charts.py
# instead of re-deriving image names / severity counts a second time.
spec = importlib.util.spec_from_file_location("generate_charts", os.path.join(SCRIPT_DIR, "generate-charts.py"))
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)


# images.conf (bash) is the single source of truth for which base images are
# "generic OS" vs "Java runtime" — this mirrors the identical helper in
# Build Docker Images/scripts/generate-html-report.py, kept as a plain
# duplicate (not a shared import) since each report script is meant to stay
# self-contained. Both scripts read BASE_IMAGES_JAVA directly from
# images.conf by asking bash to source it, rather than guessing from the
# image name — add a new Java base image there and every report picks it up.
def load_java_base_image_names(repo_root=REPO_ROOT):
    images_conf = os.path.join(repo_root, "images.conf")
    script = 'source "$1"; printf "%s\\n" "${BASE_IMAGES_JAVA[@]}"'
    try:
        result = subprocess.run(
            ["bash", "-c", script, "bash", images_conf],
            capture_output=True, text=True, check=True,
        )
        return set(line for line in result.stdout.splitlines() if line)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        # A wrong-but-safe fallback: nothing gets misplaced into the Java
        # table, it all just lands in the plainer "Base Images" one instead.
        print(f"  WARN could not read BASE_IMAGES_JAVA from {images_conf}: {e}")
        return set()


def split_three(items, java_image_names):
    """Split scan results into base/generic, base/Java, and hello-conference
    app images — see load_java_base_image_names() above for how "Java" is
    decided. Keeps the severity comparison meaningful for each audience
    instead of mixing e.g. alpine:3 in with eclipse-temurin:25-jdk, or a
    base image in with the app images built from it."""
    app_items = [it for it in items if it[0].startswith("hello-conference:")]
    base_items = [it for it in items if not it[0].startswith("hello-conference:")]
    java_items = [it for it in base_items if it[0] in java_image_names]
    generic_items = [it for it in base_items if it[0] not in java_image_names]
    return generic_items, java_items, app_items


def summary_rows_html(items):
    def sev_cell(count, sev_class):
        return f'<td class="num {sev_class}">{count if count else "–"}</td>' if count else '<td class="num muted">–</td>'

    def unique_cell(count, tool_class):
        return f'<td class="num total {tool_class}">{count}</td>' if count else '<td class="num muted">–</td>'

    rows = []
    for img, g, t, o, unique_grype, unique_trivy, unique_osv in items:
        rows.append(f"""
        <tr>
          <td class="image-name">{html.escape(img)}</td>
          <td class="num total grype">{g['_total']}</td>
          {sev_cell(g['CRITICAL'], 'crit')}
          {sev_cell(g['HIGH'], 'high')}
          {sev_cell(g['MEDIUM'], 'med')}
          {sev_cell(g['LOW'], 'low')}
          {sev_cell(g['UNKNOWN'], 'unk')}
          <td class="num total trivy">{t['_total']}</td>
          {sev_cell(t['CRITICAL'], 'crit')}
          {sev_cell(t['HIGH'], 'high')}
          {sev_cell(t['MEDIUM'], 'med')}
          {sev_cell(t['LOW'], 'low')}
          {sev_cell(t['UNKNOWN'], 'unk')}
          <td class="num total osv">{o['_total']}</td>
          {sev_cell(o['CRITICAL'], 'crit')}
          {sev_cell(o['HIGH'], 'high')}
          {sev_cell(o['MEDIUM'], 'med')}
          {sev_cell(o['LOW'], 'low')}
          {sev_cell(o['UNKNOWN'], 'unk')}
          {unique_cell(unique_grype, 'grype')}
          {unique_cell(unique_trivy, 'trivy')}
          {unique_cell(unique_osv, 'osv')}
        </tr>""")
    return "\n".join(rows)


def severity_table_html(subtitle, rows_html):
    return f"""
    <h3>{subtitle}</h3>
    <div class="table-scroll">
      <table>
        <thead>
          <tr class="group">
            <th class="image-col"></th>
            <th colspan="6" class="grype-hdr">Grype</th>
            <th colspan="6" class="trivy-hdr">Trivy</th>
            <th colspan="6" class="osv-hdr">OSV-Scanner</th>
            <th colspan="3" class="unique-hdr">Unique</th>
          </tr>
          <tr>
            <th class="image-col">Image</th>
            <th>Total</th><th>Crit</th><th>High</th><th>Med</th><th>Low</th><th>Unk</th>
            <th>Total</th><th>Crit</th><th>High</th><th>Med</th><th>Low</th><th>Unk</th>
            <th>Total</th><th>Crit</th><th>High</th><th>Med</th><th>Low</th><th>Unk</th>
            <th>Unique in Grype</th><th>Unique in Trivy</th><th>Unique in OSV</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>"""


def barchart_html(items):
    """Grouped horizontal bar chart — total vulnerabilities per image, Grype
    vs Trivy vs OSV-Scanner — rendered directly under its matching severity
    table so the totals are readable at a glance without scanning across the
    Total columns of three grouped headers. Plain HTML/CSS (bar width as a
    %), no SVG/JS/build step, consistent with the rest of this report."""
    if not items:
        return ""
    chart_max = max((v["_total"] for _, g, t, o, *_ in items for v in (g, t, o)), default=0) or 1

    def bar(tool_class, tool_label, val):
        pct = (val / chart_max) * 100
        return (
            f'<div class="bar-track" title="{tool_label}: {val}">'
            f'<div class="bar-outer"><div class="bar {tool_class}" style="width:{pct:.1f}%"></div></div>'
            f'<span class="bar-val">{val}</span></div>'
        )

    rows = []
    for img, g, t, o, *_ in items:
        esc = html.escape(img)
        rows.append(f"""
        <div class="barchart-row">
          <div class="barchart-label" title="{esc}">{esc}</div>
          <div class="barchart-bars">
            {bar('grype', 'Grype', g['_total'])}
            {bar('trivy', 'Trivy', t['_total'])}
            {bar('osv', 'OSV-Scanner', o['_total'])}
          </div>
        </div>""")

    return f"""
    <div class="barchart" role="img" aria-label="Total vulnerabilities per image — Grype vs Trivy vs OSV-Scanner">
      <div class="barchart-legend">
        <span><i class="swatch grype"></i>Grype</span>
        <span><i class="swatch trivy"></i>Trivy</span>
        <span><i class="swatch osv"></i>OSV-Scanner</span>
      </div>
      <div class="barchart-rows">
        {"".join(rows)}
      </div>
    </div>"""


# OWASP Dependency Check scans the hello-conference app's dependency tree
# (Vulnerable Application/pom.xml) once — not per Docker image, since every
# hello-conference:* image embeds the same built jar. So this renders a
# single-row table, using the same Total/Crit/High/Med/Low columns as the
# Grype/Trivy/OSV table above, plus a "Unique in OWASP" column (CVEs OWASP DC
# found that neither Grype, Trivy, nor OSV found in any scanned image — see
# generate-charts.py::load_all's owasp_ids handling).
def owasp_table_html(owasp_counts, owasp_unique):
    if owasp_counts is None:
        rows_html = '<tr><td colspan="8" class="muted">No OWASP Dependency Check report found — run "OWASP Dependency Check/scripts/run-check.sh" first.</td></tr>'
    else:
        c = owasp_counts

        def sev_cell(count, sev_class):
            return f'<td class="num {sev_class}">{count}</td>' if count else '<td class="num muted">–</td>'

        rows_html = f"""
        <tr>
          <td class="image-name">HelloConference (application dependencies)</td>
          <td class="num total owasp">{c['_total']}</td>
          {sev_cell(c['CRITICAL'], 'crit')}
          {sev_cell(c['HIGH'], 'high')}
          {sev_cell(c['MEDIUM'], 'med')}
          {sev_cell(c['LOW'], 'low')}
          {sev_cell(c['UNKNOWN'], 'unk')}
          <td class="num total owasp">{owasp_unique if owasp_unique else "–"}</td>
        </tr>"""
    return f"""
    <h3>OWASP Dependency Check</h3>
    <div class="table-scroll">
      <table>
        <thead>
          <tr class="group">
            <th class="image-col"></th>
            <th colspan="6" class="owasp-hdr">OWASP Dependency Check</th>
            <th class="unique-hdr">Unique</th>
          </tr>
          <tr>
            <th class="image-col">Application</th>
            <th>Total</th><th>Crit</th><th>High</th><th>Med</th><th>Low</th><th>Unk</th>
            <th>Unique in OWASP</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
    <p class="legend" style="margin-top:0.5rem">Same jar is embedded in every hello-conference image, so this single row applies to all of them &middot; "Unique in OWASP" = found by OWASP DC but by none of Grype/Trivy/OSV in any scanned image.</p>"""


# Shared verbatim (not passed through .format — its literal "{" / "}" pairs
# are CSS rules, not placeholders) so both reports render identically.
PAGE_STYLE = """
  :root {
    --bg: #F7F8FC; --surface: #FFFFFF; --border: #DBDFEA; --text: #1A1D2B; --muted: #656F91;
    --grype: #E65100; --trivy: #1565C0; --osv: #00796B; --owasp: #6A1B9A;
    --crit: #B71C1C; --high: #E65100; --med: #B8860B; --low: #4C7A2C; --unknown: #6B7280;
    --header-bg: #1A237E; --header-fg: #FFFFFF; --alt-row: #EEF1FC;
    --focus: #4353C4;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --alt-row: #1E2130; --med: #E0B93D; --low: #7FB855; --focus: #8891E8; --unknown: #9CA3AF;
    }
  }
  :root[data-theme="dark"] {
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --alt-row: #1E2130; --med: #E0B93D; --low: #7FB855; --focus: #8891E8; --unknown: #9CA3AF;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  main { max-width: 1400px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }
  h1 { font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }
  .subtitle { color: var(--muted); margin: 0 0 2rem; font-size: 0.95rem; }
  .legend { color: var(--muted); font-size: 0.85rem; margin: 0.75rem 0 2rem; }
  .legend span { display: inline-block; margin-right: 1.25rem; }
  .dot { display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 50%; margin-right: 0.35rem; }
  section { margin-bottom: 3rem; }
  h2 { font-size: 1.15rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
  h3 { font-size: 0.95rem; color: var(--muted); margin: 1.75rem 0 0; text-transform: uppercase; letter-spacing: 0.04em; }
  .table-scroll { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }
  table { border-collapse: collapse; width: 100%; min-width: 920px; background: var(--surface); font-variant-numeric: tabular-nums; }
  th, td { padding: 0.55rem 0.7rem; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }
  th.image-col, td.image-name { text-align: left; white-space: normal; font-variant-numeric: normal; }
  thead th { position: sticky; top: 0; background: var(--header-bg); color: var(--header-fg); font-weight: 600; }
  thead tr.group th { font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase; }
  th.grype-hdr { background: #BF360C; color: #fff; }
  th.trivy-hdr { background: #0D47A1; color: #fff; }
  th.osv-hdr   { background: #00695C; color: #fff; }
  th.owasp-hdr { background: #4A148C; color: #fff; }
  th.unique-hdr { background: #37474F; color: #fff; }
  tbody tr:nth-child(even) { background: var(--alt-row); }
  td.total.grype { font-weight: 700; color: var(--grype); }
  td.total.trivy { font-weight: 700; color: var(--trivy); }
  td.total.osv   { font-weight: 700; color: var(--osv); }
  td.total.owasp { font-weight: 700; color: var(--owasp); }
  td.crit { color: var(--crit); font-weight: 600; }
  td.high { color: var(--high); font-weight: 600; }
  td.med  { color: var(--med); font-weight: 600; }
  td.low  { color: var(--low); font-weight: 600; }
  td.unk  { color: var(--unknown); font-weight: 600; }
  td.muted { color: var(--muted); }
  a { color: var(--trivy); }
  a:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
  footer { color: var(--muted); font-size: 0.8rem; margin-top: 3rem; }
  .barchart { margin: 0.9rem 0 0; padding: 1rem 1.1rem 1.15rem; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }
  .barchart-legend { display: flex; gap: 1.25rem; font-size: 0.8rem; color: var(--muted); margin: 0 0 0.9rem; }
  .barchart-legend .swatch { display: inline-block; width: 0.65rem; height: 0.65rem; border-radius: 2px; margin-right: 0.35rem; vertical-align: middle; }
  .swatch.grype, .bar.grype { background: var(--grype); }
  .swatch.trivy, .bar.trivy { background: var(--trivy); }
  .swatch.osv,   .bar.osv   { background: var(--osv); }
  .barchart-row { display: grid; grid-template-columns: minmax(140px, 240px) 1fr; gap: 0.9rem; align-items: center; padding: 0.4rem 0; }
  .barchart-row + .barchart-row { border-top: 1px solid var(--border); }
  .barchart-label { font-size: 0.82rem; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .barchart-bars { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
  .bar-track { display: flex; align-items: center; gap: 0.5rem; }
  .bar-outer { flex: 1 1 auto; min-width: 0; height: 11px; background: var(--alt-row); border-radius: 3px; overflow: hidden; }
  .bar { height: 100%; border-radius: 0 3px 3px 0; }
  .bar-val { flex: 0 0 auto; width: 2.4rem; text-align: right; font-variant-numeric: tabular-nums; font-size: 0.78rem; color: var(--muted); }
"""

PAGE_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{style}</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">{subtitle}</p>
  <p class="legend">
    <span><span class="dot" style="background:var(--crit)"></span>Critical</span>
    <span><span class="dot" style="background:var(--high)"></span>High</span>
    <span><span class="dot" style="background:var(--med)"></span>Medium</span>
    <span><span class="dot" style="background:var(--low)"></span>Low</span>
    <span><span class="dot" style="background:var(--unknown)"></span>Unknown</span>
  </p>
"""

PAGE_FOOT = """
  <footer>Compare Security Scans &middot; <a href="https://github.com/johanjanssen/Keep-Up-To-Date">Keep-Up-To-Date</a></footer>
</main>
</body>
</html>
"""


def render_page(title, subtitle, section):
    return PAGE_HEAD.format(title=title, style=PAGE_STYLE, subtitle=subtitle) + section + PAGE_FOOT


def write_html(output_html, content):
    os.makedirs(os.path.dirname(output_html) or ".", exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  OK  html -> {output_html}")


# Feeds the presentation's live "Image Size vs CVE Count" charts (see
# Presentation/index.html) — Grype's total is used (not Trivy's) to match the
# "CVEs (Grype)" figure already quoted elsewhere in the deck.
def chart_rows(items):
    return [{"name": img, "cves": g["_total"]} for img, g, *_ in items]


def write_json(output_json, generic_items, java_items, app_items):
    os.makedirs(os.path.dirname(output_json) or ".", exist_ok=True)
    payload = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generic": chart_rows(generic_items),
        "java": chart_rows(java_items),
        "app": chart_rows(app_items),
    }
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print(f"  OK  json -> {output_json}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trivy_dir")
    parser.add_argument("grype_dir")
    parser.add_argument("osv_dir", help="OSV-Scanner JSON results dir")
    parser.add_argument("base_output_html", help="Output path for the base-images report (published at /image-scans)")
    parser.add_argument("custom_output_html", help="Output path for the hello-conference report (published at /custom-image-scans)")
    parser.add_argument("--title", default="Container Image CVE Comparison — Trivy vs Grype vs OSV-Scanner")
    parser.add_argument("--custom-title", default="hello-conference Image CVE Comparison — Trivy vs Grype vs OSV-Scanner")
    parser.add_argument("--json-out", default=None,
                         help="Optional path to also write a JSON summary (image name + Grype CVE "
                              "count, grouped generic/java/app) for the presentation's live charts")
    parser.add_argument("--owasp-json",
                         default=os.path.join(REPO_ROOT, "Vulnerable Application", "target", "dependency-check-report.json"),
                         help="Path to OWASP Dependency Check's JSON report for the hello-conference app "
                              "(Vulnerable Application/pom.xml — the same source every hello-conference:* "
                              "image is built from). Rendered as a one-row table on the custom-images "
                              "report and folded into the Grype/Trivy/OSV 'Unique' columns there. Missing "
                              "file is not an error — the table just shows a placeholder.")
    args = parser.parse_args()

    owasp_counts, owasp_ids = None, set()
    if args.owasp_json and os.path.isfile(args.owasp_json):
        try:
            owasp_counts, owasp_ids = gc.load_owasp(args.owasp_json)
        except Exception as e:
            print(f"  WARN could not read OWASP report {args.owasp_json}: {e}")
    else:
        print(f"  No OWASP Dependency Check report at {args.owasp_json} — OWASP table will show a placeholder.")

    items, owasp_unique = gc.load_all(args.trivy_dir, args.grype_dir, args.osv_dir, owasp_ids)
    if not items:
        print("  No JSON results found — writing placeholder pages.")

    generic_items, java_items, app_items = split_three(items, load_java_base_image_names())
    print(f"  images: {len(generic_items)} generic base + {len(java_items)} java base + {len(app_items)} app rows")

    no_results = '<tr><td colspan="22">No results.</td></tr>'
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    subtitle_common = (
        f"Generated {generated} &middot; images scanned with <strong>Grype</strong>, <strong>Trivy</strong>, and "
        f'<strong>OSV-Scanner</strong> (Google, matched against OSV.dev) &middot; '
        f'counts are unique CVEs (deduplicated by CVE ID) &middot; '
        f'"Unk" = no severity rating available from that scanner (Total = Crit+High+Med+Low+Unk) &middot; '
        f'"Unique in X" = found by X but by none of the other scanners &middot; '
    )

    base_section = "\n  <section>\n    <h2>Severity Comparison — Grype vs Trivy vs OSV-Scanner</h2>" + \
        severity_table_html("Base Images", summary_rows_html(generic_items) if generic_items else no_results) + \
        barchart_html(generic_items) + \
        severity_table_html("Java Runtime Images (JDK / JRE / GraalVM)", summary_rows_html(java_items) if java_items else no_results) + \
        barchart_html(java_items) + \
        "\n  </section>\n"
    base_page = render_page(
        title=html.escape(args.title),
        subtitle=subtitle_common + 'see also <a href="../custom-image-scans/">hello-conference image CVE comparison</a>',
        section=base_section,
    )
    write_html(args.base_output_html, base_page)

    custom_section = "\n  <section>\n    <h2>Severity Comparison — Grype vs Trivy vs OSV-Scanner vs OWASP Dependency Check</h2>" + \
        severity_table_html("hello-conference Images", summary_rows_html(app_items) if app_items else no_results) + \
        barchart_html(app_items) + \
        owasp_table_html(owasp_counts, owasp_unique) + \
        "\n  </section>\n"
    custom_page = render_page(
        title=html.escape(args.custom_title),
        subtitle=subtitle_common + 'see also <a href="../image-scans/">base image CVE comparison</a>',
        section=custom_section,
    )
    write_html(args.custom_output_html, custom_page)

    if args.json_out:
        write_json(args.json_out, generic_items, java_items, app_items)


if __name__ == "__main__":
    main()
