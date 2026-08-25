#!/usr/bin/env python3
"""
Generate two self-contained static HTML reports from the plain-text output
of measure-images.sh (size/package comparison) and measure-performance.sh
(startup/memory comparison):

  - a "base images" report (generic OS images + Java runtime images) — the
    general-purpose comparison, published at /images
  - a "custom images" report (hello-conference app images + their startup/
    memory numbers) — the app-specific comparison, published at /custom-images

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
  python3 generate-html-report.py <measure_images_txt> <measure_performance_txt> \\
      <base_output_html> <custom_output_html> [--title "..."] [--custom-title "..."]
"""
import argparse, html, os, re, subprocess
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

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


# images.conf (bash) is the single source of truth for which base images are
# "generic OS" vs "Java runtime" — both this report and the Compare Security
# Scans report read BASE_IMAGES_JAVA from it directly (by asking bash to
# source the file and print the array) rather than each guessing from the
# image name with its own keyword list. Add a new Java base image to
# BASE_IMAGES_JAVA in images.conf and every report picks it up automatically.
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
        # Report generation shouldn't hard-fail just because the categorisation
        # couldn't be loaded — fall back to treating every base image as
        # "generic" (a wrong-but-safe default: nothing is misplaced into the
        # Java table, everything just lands in the plainer one instead).
        print(f"  WARN could not read BASE_IMAGES_JAVA from {images_conf}: {e}")
        return set()


def split_generic_java(base_rows, java_image_names):
    """Split base images into 'normal' OS images (debian, alpine, ubuntu, …)
    and Java-runtime images (anything bundling a JDK, JRE, or GraalVM) so the
    size/package comparison stays meaningful for each audience instead of
    mixing e.g. alpine:3 in with eclipse-temurin:25-jdk."""
    java_rows = [r for r in base_rows if r["image"] in java_image_names]
    generic_rows = [r for r in base_rows if r["image"] not in java_image_names]
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


# Shared verbatim (not passed through .format — its literal "{" / "}" pairs
# are CSS rules, not placeholders) so both reports render identically.
PAGE_STYLE = """
  :root {
    --bg: #F7F8FC; --surface: #FFFFFF; --border: #DBDFEA; --text: #1A1D2B; --muted: #656F91;
    --accent: #1565C0; --ok: #2E7D32; --warn: #B71C1C;
    --header-bg: #1A237E; --header-fg: #FFFFFF; --alt-row: #EEF1FC;
    --focus: #4353C4; --highlight-bg: #DCF3DE; --highlight-border: #2E7D32;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --alt-row: #1E2130; --ok: #7FB855; --warn: #E0554A; --focus: #8891E8;
      --highlight-bg: #1E3320; --highlight-border: #7FB855;
    }
  }
  :root[data-theme="dark"] {
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --alt-row: #1E2130; --ok: #7FB855; --warn: #E0554A; --focus: #8891E8;
    --highlight-bg: #1E3320; --highlight-border: #7FB855;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }
  main { max-width: 1200px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }
  h1 { font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }
  .subtitle { color: var(--muted); margin: 0 0 2rem; font-size: 0.95rem; }
  section { margin-bottom: 3rem; }
  h2 { font-size: 1.15rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
  h3 { font-size: 0.95rem; color: var(--muted); margin: 1.75rem 0 0; text-transform: uppercase; letter-spacing: 0.04em; }
  p.hint { color: var(--muted); font-size: 0.85rem; margin: 0.5rem 0 1rem; }
  .table-scroll { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }
  table { border-collapse: collapse; width: 100%; min-width: 640px; background: var(--surface); font-variant-numeric: tabular-nums; }
  th, td { padding: 0.55rem 0.7rem; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }
  th.image-col, td.image-name { text-align: left; white-space: normal; font-variant-numeric: normal; }
  thead th { position: sticky; top: 0; background: var(--header-bg); color: var(--header-fg); font-weight: 600; }
  tbody tr:nth-child(even) { background: var(--alt-row); }
  tbody tr.not-built { opacity: 0.55; font-style: italic; }
  tbody tr.size-under-100 { background: var(--highlight-bg); box-shadow: inset 3px 0 var(--highlight-border); }
  td.muted { color: var(--muted); }
  td.warmup-ok { color: var(--ok); font-weight: 700; }
  td.warmup-timeout { color: var(--warn); font-weight: 700; }
  a { color: var(--accent); }
  a:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }
  footer { color: var(--muted); font-size: 0.8rem; margin-top: 3rem; }
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
"""

PAGE_FOOT = """
  <footer>Build Docker Images &middot; <a href="https://github.com/johanjanssen/Keep-Up-To-Date">Keep-Up-To-Date</a></footer>
</main>
</body>
</html>
"""

# Published at /images — the general-purpose comparison: generic OS base
# images and Java runtime base images, with no hello-conference-specific data.
BASE_IMAGES_SECTION = """
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
  </section>
"""

# Published at /custom-images — the hello-conference-specific comparison:
# the app images themselves, plus their startup/memory numbers.
CUSTOM_IMAGES_SECTION = """
  <section>
    <h2>Image Size &amp; Package Comparison</h2>

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
"""


def render_page(title, subtitle, section):
    return PAGE_HEAD.format(title=title, style=PAGE_STYLE, subtitle=subtitle) + section + PAGE_FOOT


def write_html(output_html, content):
    os.makedirs(os.path.dirname(output_html) or ".", exist_ok=True)
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  OK  html -> {output_html}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("measure_images_txt")
    parser.add_argument("measure_performance_txt")
    parser.add_argument("base_output_html", help="Output path for the base-images report (published at /images)")
    parser.add_argument("custom_output_html", help="Output path for the hello-conference report (published at /custom-images)")
    parser.add_argument("--title", default="Docker Image Size &amp; Performance Comparison",
                         help="Title for the base-images report")
    parser.add_argument("--custom-title", default="hello-conference Image &amp; Performance Comparison",
                         help="Title for the hello-conference report")
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
    generic_base_rows, java_base_rows = split_generic_java(base_rows, load_java_base_image_names())
    print(f"  images: {len(generic_base_rows)} generic base + {len(java_base_rows)} java base + "
          f"{len(app_rows)} app rows   performance: {len(perf_rows)} rows")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    base_section = BASE_IMAGES_SECTION.format(
        generic_base_rows=base_rows_html(generic_base_rows) if generic_base_rows else '<tr><td colspan="3">No results.</td></tr>',
        java_base_rows=base_rows_html(java_base_rows) if java_base_rows else '<tr><td colspan="3">No results.</td></tr>',
    )
    base_page = render_page(
        title=html.escape(args.title),
        subtitle=f"Generated {generated} &middot; base images measured from <strong>Build Docker Images</strong> &middot; "
                  f'see also <a href="../custom-images/">hello-conference images &amp; performance</a>',
        section=base_section,
    )
    write_html(args.base_output_html, base_page)

    custom_section = CUSTOM_IMAGES_SECTION.format(
        app_rows=app_rows_html(app_rows) if app_rows else '<tr><td colspan="5">No results.</td></tr>',
        perf_rows=perf_rows_html(perf_rows) if perf_rows else '<tr><td colspan="5">No results.</td></tr>',
    )
    custom_page = render_page(
        title=html.escape(args.custom_title),
        subtitle=f"Generated {generated} &middot; images built and measured from <strong>Build Docker Images</strong> &middot; "
                  f'see also <a href="../images/">base image comparison</a>',
        section=custom_section,
    )
    write_html(args.custom_output_html, custom_page)


if __name__ == "__main__":
    main()
