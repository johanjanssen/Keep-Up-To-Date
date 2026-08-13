#!/usr/bin/env python3
"""
Generate a single self-contained static HTML report from the plain-text output
of measure-images.sh (size/package comparison) and measure-performance.sh
(startup/memory comparison).

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Both tables are parsed by fixed character offsets that mirror the printf
format strings in the two shell scripts (kept in sync in the constants below)
rather than by splitting on whitespace, since several columns can legitimately
be empty (e.g. APP SIZE for non-hello-conference base images) and a
whitespace split would silently swallow those columns.

Usage:
  python3 generate-html-report.py <measure_images_txt> <measure_performance_txt> <output_html> [--title "..."]
"""
import argparse, html, os
from datetime import datetime, timezone

# ── Column layouts (must mirror the printf format strings) ─────────────────
# measure-images.sh:      printf "%-50s  %-12s  %-12s  %-18s  %s\n"
IMAGES_COLS = [("image", 50), ("image_size", 12), ("app_size", 12), ("app_runtime_size", 18), ("packages", None)]
# measure-performance.sh: printf "%-52s  %-20s  %-8s  %-14s  %s\n"
PERF_COLS = [("image", 52), ("memory", 20), ("warmup", 8), ("startup_log", 14), ("startup_wall", None)]
GAP = 2  # spaces between each fixed-width column


def slice_row(line, cols):
    row, pos = {}, 0
    for name, width in cols:
        if width is None:
            row[name] = line[pos:].strip()
        else:
            row[name] = line[pos:pos + width].strip()
            pos += width + GAP
    return row


def is_separator(line):
    stripped = line.strip()
    return bool(stripped) and set(stripped) <= {"-", " "}


def parse_table(text, cols):
    """Find the first `header line` + `dashed separator line` + data-rows block
    and parse it into a list of dicts keyed by cols[*][0]."""
    lines = text.splitlines()
    for i in range(len(lines) - 1):
        if lines[i].lstrip().upper().startswith("IMAGE"):
            if is_separator(lines[i + 1]):
                rows = []
                j = i + 2
                while j < len(lines) and lines[j].strip():
                    rows.append(slice_row(lines[j], cols))
                    j += 1
                return rows
    return []


def cell(value, muted_values=("", "N/A", "-")):
    if value in muted_values:
        return '<td class="muted">–</td>'
    return f"<td>{html.escape(value)}</td>"


def images_rows_html(rows):
    out = []
    for r in rows:
        built = r["image_size"] not in ("NOT BUILT", "")
        css = "" if built else ' class="not-built"'
        out.append(f"""
        <tr{css}>
          <td class="image-name">{html.escape(r['image'])}</td>
          {cell(r['image_size'])}
          {cell(r['app_size'])}
          {cell(r['app_runtime_size'])}
          {cell(r['packages'])}
        </tr>""")
    return "\n".join(out)


def perf_rows_html(rows):
    def warmup_cell(status):
        if status == "OK":
            return '<td class="warmup-ok">OK</td>'
        if not status or status in ("-", "N/A"):
            return '<td class="muted">–</td>'
        return f'<td class="warmup-timeout">{html.escape(status)}</td>'

    out = []
    for r in rows:
        out.append(f"""
        <tr>
          <td class="image-name">{html.escape(r['image'])}</td>
          {cell(r['memory'])}
          {warmup_cell(r['warmup'])}
          {cell(r['startup_log'])}
          {cell(r['startup_wall'])}
        </tr>""")
    return "\n".join(out)


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #F7F8FC; --surface: #FFFFFF; --border: #DBDFEA; --text: #1A1D2B; --muted: #656F91;
    --accent: #1565C0; --ok: #2E7D32; --warn: #B71C1C;
    --header-bg: #1A237E; --header-fg: #FFFFFF; --alt-row: #EEF1FC;
    --focus: #4353C4;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --alt-row: #1E2130; --ok: #7FB855; --warn: #E0554A; --focus: #8891E8;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --alt-row: #1E2130; --ok: #7FB855; --warn: #E0554A; --focus: #8891E8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  main {{ max-width: 1200px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }}
  h1 {{ font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }}
  .subtitle {{ color: var(--muted); margin: 0 0 2rem; font-size: 0.95rem; }}
  section {{ margin-bottom: 3rem; }}
  h2 {{ font-size: 1.15rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
  p.hint {{ color: var(--muted); font-size: 0.85rem; margin: 0.5rem 0 1rem; }}
  .table-scroll {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }}
  table {{ border-collapse: collapse; width: 100%; min-width: 640px; background: var(--surface); font-variant-numeric: tabular-nums; }}
  th, td {{ padding: 0.55rem 0.7rem; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  th.image-col, td.image-name {{ text-align: left; white-space: normal; font-variant-numeric: normal; }}
  thead th {{ position: sticky; top: 0; background: var(--header-bg); color: var(--header-fg); font-weight: 600; }}
  tbody tr:nth-child(even) {{ background: var(--alt-row); }}
  tbody tr.not-built {{ opacity: 0.55; font-style: italic; }}
  td.muted {{ color: var(--muted); }}
  td.warmup-ok {{ color: var(--ok); font-weight: 700; }}
  td.warmup-timeout {{ color: var(--warn); font-weight: 700; }}
  a {{ color: var(--accent); }}
  a:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
  footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 3rem; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">Generated {generated} &middot; images built and measured from <strong>Build Docker Images</strong></p>

  <section>
    <h2>Image Size &amp; Package Comparison</h2>
    <p class="hint">APP SIZE / APP+RUNTIME SIZE = overhead over the runtime base image. Packages = installed OS packages inside the image.</p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th class="image-col">Image</th>
            <th>Image Size</th><th>App Size</th><th>App+Runtime Size</th><th>Packages</th>
          </tr>
        </thead>
        <tbody>
          {images_rows}
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Startup &amp; Memory Performance</h2>
    <p class="hint">STARTUP(log) = Spring Boot's own "Started in X seconds" measurement. STARTUP(wall) = wall-clock time from "docker run" to the first healthy HTTP response.</p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th class="image-col">Image</th>
            <th>Memory</th><th>Warmup</th><th>Startup (log)</th><th>Startup (wall)</th>
          </tr>
        </thead>
        <tbody>
          {perf_rows}
        </tbody>
      </table>
    </div>
  </section>

  <footer>Build Docker Images &middot; <a href="https://github.com/johanjanssen/Keep-Up-To-Date">Keep-Up-To-Date</a></footer>
</main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("measure_images_txt")
    parser.add_argument("measure_performance_txt")
    parser.add_argument("output_html")
    parser.add_argument("--title", default="Docker Image Size &amp; Performance Comparison")
    args = parser.parse_args()

    images_text, perf_text = "", ""
    if os.path.isfile(args.measure_images_txt):
        with open(args.measure_images_txt, encoding="utf-8", errors="replace") as f:
            images_text = f.read()
    if os.path.isfile(args.measure_performance_txt):
        with open(args.measure_performance_txt, encoding="utf-8", errors="replace") as f:
            perf_text = f.read()

    images_rows = parse_table(images_text, IMAGES_COLS)
    perf_rows = parse_table(perf_text, PERF_COLS)
    print(f"  images: {len(images_rows)} rows   performance: {len(perf_rows)} rows")

    out = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        images_rows=images_rows_html(images_rows) if images_rows else '<tr><td colspan="5">No results.</td></tr>',
        perf_rows=perf_rows_html(perf_rows) if perf_rows else '<tr><td colspan="5">No results.</td></tr>',
    )

    os.makedirs(os.path.dirname(args.output_html) or ".", exist_ok=True)
    with open(args.output_html, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"  OK  html -> {args.output_html}")


if __name__ == "__main__":
    main()
