#!/usr/bin/env python3
"""
Generate a single self-contained static HTML comparison report
(Grype vs Trivy, with the OS/App + OWASP breakdown from compare.sh).

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Usage:
  python3 generate-html-report.py <trivy_dir> <grype_dir> <charts_dir> <compare_text_file> <output_html> [--title "..."]
"""
import argparse, base64, html, importlib.util, os, sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Reuse the (already-fixed) JSON loading/aggregation logic from generate-charts.py
# instead of re-deriving image names / severity counts a second time.
spec = importlib.util.spec_from_file_location("generate_charts", os.path.join(SCRIPT_DIR, "generate-charts.py"))
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)


def b64_file(path):
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def summary_rows_html(items):
    def sev_cell(count, sev_class):
        return f'<td class="num {sev_class}">{count if count else "–"}</td>' if count else '<td class="num muted">–</td>'

    def unique_cell(count, tool_class):
        return f'<td class="num total {tool_class}">{count}</td>' if count else '<td class="num muted">–</td>'

    rows = []
    for img, g, t, unique_grype, unique_trivy in items:
        rows.append(f"""
        <tr>
          <td class="image-name">{html.escape(img)}</td>
          <td class="num total grype">{g['_total']}</td>
          {sev_cell(g['CRITICAL'], 'crit')}
          {sev_cell(g['HIGH'], 'high')}
          {sev_cell(g['MEDIUM'], 'med')}
          {sev_cell(g['LOW'], 'low')}
          <td class="num total trivy">{t['_total']}</td>
          {sev_cell(t['CRITICAL'], 'crit')}
          {sev_cell(t['HIGH'], 'high')}
          {sev_cell(t['MEDIUM'], 'med')}
          {sev_cell(t['LOW'], 'low')}
          {unique_cell(unique_grype, 'grype')}
          {unique_cell(unique_trivy, 'trivy')}
        </tr>""")
    return "\n".join(rows)


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #F7F8FC; --surface: #FFFFFF; --border: #DBDFEA; --text: #1A1D2B; --muted: #656F91;
    --grype: #E65100; --trivy: #1565C0;
    --crit: #B71C1C; --high: #E65100; --med: #B8860B; --low: #4C7A2C;
    --header-bg: #1A237E; --header-fg: #FFFFFF; --alt-row: #EEF1FC;
    --focus: #4353C4;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --alt-row: #1E2130; --med: #E0B93D; --low: #7FB855; --focus: #8891E8;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --alt-row: #1E2130; --med: #E0B93D; --low: #7FB855; --focus: #8891E8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  main {{ max-width: 1400px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }}
  h1 {{ font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }}
  .subtitle {{ color: var(--muted); margin: 0 0 2rem; font-size: 0.95rem; }}
  .legend {{ color: var(--muted); font-size: 0.85rem; margin: 0.75rem 0 2rem; }}
  .legend span {{ display: inline-block; margin-right: 1.25rem; }}
  .dot {{ display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 50%; margin-right: 0.35rem; }}
  section {{ margin-bottom: 3rem; }}
  h2 {{ font-size: 1.15rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
  .charts {{ display: grid; grid-template-columns: 1fr; gap: 1.5rem; }}
  .charts img {{ display: block; width: 100%; height: auto; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); }}
  .table-scroll {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }}
  table {{ border-collapse: collapse; width: 100%; min-width: 920px; background: var(--surface); font-variant-numeric: tabular-nums; }}
  th, td {{ padding: 0.55rem 0.7rem; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  th.image-col, td.image-name {{ text-align: left; white-space: normal; font-variant-numeric: normal; }}
  thead th {{ position: sticky; top: 0; background: var(--header-bg); color: var(--header-fg); font-weight: 600; }}
  thead tr.group th {{ font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase; }}
  th.grype-hdr {{ background: #BF360C; color: #fff; }}
  th.trivy-hdr {{ background: #0D47A1; color: #fff; }}
  th.unique-hdr {{ background: #37474F; color: #fff; }}
  tbody tr:nth-child(even) {{ background: var(--alt-row); }}
  td.total.grype {{ font-weight: 700; color: var(--grype); }}
  td.total.trivy {{ font-weight: 700; color: var(--trivy); }}
  td.crit {{ color: var(--crit); font-weight: 600; }}
  td.high {{ color: var(--high); font-weight: 600; }}
  td.med  {{ color: var(--med); font-weight: 600; }}
  td.low  {{ color: var(--low); font-weight: 600; }}
  td.muted {{ color: var(--muted); }}
  details {{ border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }}
  details summary {{ cursor: pointer; padding: 0.85rem 1rem; font-weight: 600; }}
  pre {{
    margin: 0; padding: 1rem; overflow-x: auto; font: 12.5px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
    border-top: 1px solid var(--border); font-variant-numeric: tabular-nums;
  }}
  a {{ color: var(--trivy); }}
  a:focus-visible, summary:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
  footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 3rem; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">Generated {generated} &middot; images scanned with <strong>Grype</strong> and <strong>Trivy</strong> &middot; counts are unique CVEs (deduplicated by CVE ID)</p>

  <section>
    <h2>Severity Comparison — Grype vs Trivy</h2>
    <p class="legend">
      <span><span class="dot" style="background:var(--crit)"></span>Critical</span>
      <span><span class="dot" style="background:var(--high)"></span>High</span>
      <span><span class="dot" style="background:var(--med)"></span>Medium</span>
      <span><span class="dot" style="background:var(--low)"></span>Low</span>
    </p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr class="group">
            <th class="image-col"></th>
            <th colspan="5" class="grype-hdr">Grype</th>
            <th colspan="5" class="trivy-hdr">Trivy</th>
            <th colspan="2" class="unique-hdr">Unique</th>
          </tr>
          <tr>
            <th class="image-col">Image</th>
            <th>Total</th><th>Crit</th><th>High</th><th>Med</th><th>Low</th>
            <th>Total</th><th>Crit</th><th>High</th><th>Med</th><th>Low</th>
            <th>Unique in Grype</th><th>Unique in Trivy</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Charts</h2>
    <div class="charts">
      {chart_barplot_img}
    </div>
  </section>

  <section>
    <h2>Full Report</h2>
    <details {open_attr}>
      <summary>OS-level vs application-level breakdown, coverage diff, OWASP Dependency-Check &mdash; click to expand</summary>
      <pre>{compare_text}</pre>
    </details>
  </section>

  <footer>Compare Security Scans &middot; <a href="https://github.com/johanjanssen/Keep-Up-To-Date">Keep-Up-To-Date</a></footer>
</main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("trivy_dir")
    parser.add_argument("grype_dir")
    parser.add_argument("charts_dir")
    parser.add_argument("compare_text_file")
    parser.add_argument("output_html")
    parser.add_argument("--title", default="Container Image CVE Comparison — Trivy vs Grype")
    args = parser.parse_args()

    items = gc.load_all(args.trivy_dir, args.grype_dir)
    if not items:
        print("  No JSON results found — writing a placeholder page.")

    barplot_b64 = b64_file(os.path.join(args.charts_dir, "scan-barplot.png"))
    chart_barplot_img = f'<img src="data:image/png;base64,{barplot_b64}" alt="Grype vs Trivy total CVEs barplot">' if barplot_b64 else "<p><em>Barplot not available.</em></p>"

    compare_text = ""
    if os.path.isfile(args.compare_text_file):
        with open(args.compare_text_file, encoding="utf-8", errors="replace") as f:
            compare_text = f.read()
    compare_text = compare_text or "(no compare.sh output found)"

    out = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        chart_barplot_img=chart_barplot_img,
        rows=summary_rows_html(items) if items else '<tr><td colspan="13">No results.</td></tr>',
        compare_text=html.escape(compare_text),
        open_attr="open",
    )

    os.makedirs(os.path.dirname(args.output_html) or ".", exist_ok=True)
    with open(args.output_html, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"  OK  html -> {args.output_html}")


if __name__ == "__main__":
    main()