#!/usr/bin/env python3
"""
Generate a single self-contained static HTML report from the plain-text output
of measure-images.sh (size/package comparison) and measure-performance.sh
(startup/memory comparison).

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Both tables are parsed by splitting each row on " | ", which the printf format
strings in the two shell scripts use as an explicit field separator (kept in
sync with the field-name lists below) — not by fixed character offsets and
not by splitting on arbitrary whitespace. Fixed-width offsets silently
mis-parse the moment any field's content is longer than the assumed column
width (e.g. "registry.access.redhat.com/ubi9/openjdk-25-runtime:latest" or
"bellsoft/liberica-runtime-container:jre-25-slim-musl" both overflow the
image-name column) — %-Ns in the shell scripts never truncates, it just stops
padding, so every later column silently shifts and gets sliced at the wrong
offset. A plain whitespace split has its own problem: several columns can
legitimately be empty (e.g. APP SIZE for non-hello-conference base images),
and that would silently swallow them. The "|" delimiter has neither problem:
it marks each field boundary explicitly regardless of content length, and an
empty field between two delimiters parses as "" rather than disappearing.

Usage:
  python3 generate-html-report.py <measure_images_txt> <measure_performance_txt> <output_html> [--title "..."]
"""
import argparse, html, os, re
from datetime import datetime, timezone

# ── Field layouts (must mirror the printf field ORDER in the two shell
# scripts — widths don't need to match since fields are "|"-delimited, not
# sliced by position) ────────────────────────────────────────────────────
# measure-images.sh:      printf "%-50s | %-12s | %-12s | %-18s | %s\n"
IMAGES_FIELDS = ["image", "image_size", "app_size", "app_runtime_size", "packages"]
# measure-performance.sh: printf "%-52s | %-20s | %-8s | %-14s | %s\n"
PERF_FIELDS = ["image", "memory", "warmup", "startup_log", "startup_wall"]


def split_row(line, fields):
    parts = [p.strip() for p in line.split(" | ")]
    if len(parts) < len(fields):
        # A row genuinely shorter than expected — pad rather than crash;
        # missing trailing fields just render as muted "–" cells.
        parts += [""] * (len(fields) - len(parts))
    elif len(parts) > len(fields):
        # More delimiters than expected (a field's own content contained
        # " | ", which none of ours currently do) — fold the overflow into
        # the last field instead of silently dropping it.
        parts = parts[:len(fields) - 1] + [" | ".join(parts[len(fields) - 1:])]
    return dict(zip(fields, parts))


def is_separator(line):
    stripped = line.strip()
    return bool(stripped) and set(stripped) <= {"-", " ", "|"}


def parse_table(text, fields):
    """Find the first `header line` + `dashed separator line` + data-rows block
    and parse it into a list of dicts keyed by `fields`."""
    lines = text.splitlines()
    for i in range(len(lines) - 1):
        if lines[i].lstrip().upper().startswith("IMAGE"):
            if is_separator(lines[i + 1]):
                rows = []
                j = i + 2
                while j < len(lines) and lines[j].strip():
                    rows.append(split_row(lines[j], fields))
                    j += 1
                return rows
    return []


def cell(value, muted_values=("", "N/A", "-")):
    if value in muted_values:
        return '<td class="muted">–</td>'
    return f"<td>{html.escape(value)}</td>"


# docker images --format "{{.Size}}" prints decimal (SI, 1000-based) units,
# e.g. "45.2MB", "1.19GB", "512kB" — mirror that base here rather than 1024.
SIZE_MULTIPLIERS_TO_MB = {"b": 1e-6, "kb": 1e-3, "mb": 1, "gb": 1e3, "tb": 1e6}


def size_to_mb(size_str):
    """Parse a docker image-size string into a value in MB, or None if unparseable."""
    m = re.match(r"^([\d.]+)\s*([a-zA-Z]+)$", size_str.strip())
    if not m:
        return None
    value, unit = float(m.group(1)), m.group(2).lower()
    multiplier = SIZE_MULTIPLIERS_TO_MB.get(unit)
    return value * multiplier if multiplier is not None else None


def split_base_app(rows):
    """hello-conference:* rows are app images built FROM the other (base) rows;
    they're the only ones with app_size/app_runtime_size populated (see
    BASE_FOR in measure-images.sh), so splitting on that prefix keeps each
    table's columns meaningful instead of mixing base and app concerns."""
    base_rows = [r for r in rows if not r["image"].startswith("hello-conference:")]
    app_rows = [r for r in rows if r["image"].startswith("hello-conference:")]
    return base_rows, app_rows


# Keyword match (case-insensitive substring) rather than an explicit image
# allowlist, so a new Java base image added to images.conf lands in the right
# table without this file needing a matching update. "java" itself catches
# gcr.io/distroless/java25-debian13, which carries none of the other keywords.
JAVA_IMAGE_KEYWORDS = ("jdk", "jre", "graalvm", "openjdk", "corretto", "liberica", "semeru", "zulu", "temurin", "java")


def is_java_image(image_name):
    lower = image_name.lower()
    return any(keyword in lower for keyword in JAVA_IMAGE_KEYWORDS)


def split_generic_java(base_rows):
    """Split base images into 'normal' OS images (debian, alpine, ubuntu, …)
    and Java-runtime images (anything bundling a JDK, JRE, or GraalVM) so the
    size/package comparison stays meaningful for each audience instead of
    mixing e.g. alpine:3 in with eclipse-temurin:25-jdk."""
    java_rows = [r for r in base_rows if is_java_image(r["image"])]
    generic_rows = [r for r in base_rows if not is_java_image(r["image"])]
    return generic_rows, java_rows


def row_classes(r):
    built = r["image_size"] not in ("NOT BUILT", "")
    classes = [] if built else ["not-built"]
    if built:
        size_mb = size_to_mb(r["image_size"])
        if size_mb is not None and size_mb < 100:
            classes.append("size-under-100")
    return f' class="{" ".join(classes)}"' if classes else ""


def base_rows_html(rows):
    out = []
    for r in rows:
        out.append(f"""
        <tr{row_classes(r)}>
          <td class="image-name">{html.escape(r['image'])}</td>
          {cell(r['image_size'])}
          {cell(r['packages'])}
        </tr>""")
    return "\n".join(out)


def app_rows_html(rows):
    out = []
    for r in rows:
        out.append(f"""
        <tr{row_classes(r)}>
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
    --focus: #4353C4; --highlight-bg: #DCF3DE; --highlight-border: #2E7D32;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --alt-row: #1E2130; --ok: #7FB855; --warn: #E0554A; --focus: #8891E8;
      --highlight-bg: #1E3320; --highlight-border: #7FB855;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --alt-row: #1E2130; --ok: #7FB855; --warn: #E0554A; --focus: #8891E8;
    --highlight-bg: #1E3320; --highlight-border: #7FB855;
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
  h3 {{ font-size: 0.95rem; color: var(--muted); margin: 1.75rem 0 0; text-transform: uppercase; letter-spacing: 0.04em; }}
  p.hint {{ color: var(--muted); font-size: 0.85rem; margin: 0.5rem 0 1rem; }}
  .table-scroll {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }}
  table {{ border-collapse: collapse; width: 100%; min-width: 640px; background: var(--surface); font-variant-numeric: tabular-nums; }}
  th, td {{ padding: 0.55rem 0.7rem; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  th.image-col, td.image-name {{ text-align: left; white-space: normal; font-variant-numeric: normal; }}
  thead th {{ position: sticky; top: 0; background: var(--header-bg); color: var(--header-fg); font-weight: 600; }}
  tbody tr:nth-child(even) {{ background: var(--alt-row); }}
  tbody tr.not-built {{ opacity: 0.55; font-style: italic; }}
  tbody tr.size-under-100 {{ background: var(--highlight-bg); box-shadow: inset 3px 0 var(--highlight-border); }}
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

    <h3>Base Images</h3>
    <p class="hint">Packages = installed OS packages inside the image. Rows are highlighted when the image size is under 100 MB.</p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th class="image-col">Image</th>
            <th>Image Size</th><th>Packages</th>
          </tr>
        </thead>
        <tbody>
          {generic_base_rows}
        </tbody>
      </table>
    </div>

    <h3>Java Runtime Images (JDK / JRE / GraalVM)</h3>
    <p class="hint">Packages = installed OS packages inside the image. Rows are highlighted when the image size is under 100 MB.</p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th class="image-col">Image</th>
            <th>Image Size</th><th>Packages</th>
          </tr>
        </thead>
        <tbody>
          {java_base_rows}
        </tbody>
      </table>
    </div>

    <h3>hello-conference Images</h3>
    <p class="hint">APP SIZE / APP+RUNTIME SIZE = overhead over the runtime base image. Packages = installed OS packages inside the image. Rows are highlighted when the image size is under 100 MB.</p>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th class="image-col">Image</th>
            <th>Image Size</th><th>App Size</th><th>App+Runtime Size</th><th>Packages</th>
          </tr>
        </thead>
        <tbody>
          {app_rows}
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

    images_rows = parse_table(images_text, IMAGES_FIELDS)
    perf_rows = parse_table(perf_text, PERF_FIELDS)
    base_rows, app_rows = split_base_app(images_rows)
    generic_base_rows, java_base_rows = split_generic_java(base_rows)
    print(f"  images: {len(generic_base_rows)} generic base + {len(java_base_rows)} java base + "
          f"{len(app_rows)} app rows   performance: {len(perf_rows)} rows")

    out = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        generic_base_rows=base_rows_html(generic_base_rows) if generic_base_rows else '<tr><td colspan="3">No results.</td></tr>',
        java_base_rows=base_rows_html(java_base_rows) if java_base_rows else '<tr><td colspan="3">No results.</td></tr>',
        app_rows=app_rows_html(app_rows) if app_rows else '<tr><td colspan="5">No results.</td></tr>',
        perf_rows=perf_rows_html(perf_rows) if perf_rows else '<tr><td colspan="5">No results.</td></tr>',
    )

    os.makedirs(os.path.dirname(args.output_html) or ".", exist_ok=True)
    with open(args.output_html, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"  OK  html -> {args.output_html}")


if __name__ == "__main__":
    main()
