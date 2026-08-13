#!/usr/bin/env python3
"""
Generate a single self-contained static HTML page showing the result of
running the Testcontainers integration tests via Maven
(`./mvnw -f Testcontainers/pom.xml test`).

Combines:
  - A pass/fail summary parsed from the Surefire XML reports
    (target/surefire-reports/TEST-*.xml)
  - The full raw console output of the Maven command

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Usage:
  python3 generate-html-report.py \
      --log <maven_console_log> \
      --surefire-dir <target/surefire-reports> \
      --output <output_html> \
      [--title "..."] [--command "..."]
"""
import argparse
import glob
import html
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

REPO_URL = "https://github.com/johanjanssen/Keep-Up-To-Date"


def parse_surefire_reports(surefire_dir):
    """Return (suites, totals) parsed from TEST-*.xml files, oldest style Surefire XML."""
    suites = []
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}

    if not surefire_dir or not os.path.isdir(surefire_dir):
        return suites, totals

    for path in sorted(glob.glob(os.path.join(surefire_dir, "TEST-*.xml"))):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue

        def num(attr, cast=int, default=0):
            try:
                return cast(root.get(attr, default))
            except (TypeError, ValueError):
                return default

        suite = {
            "name": root.get("name", os.path.basename(path)),
            "tests": num("tests"),
            "failures": num("failures"),
            "errors": num("errors"),
            "skipped": num("skipped"),
            "time": num("time", float, 0.0),
            "failed_cases": [],
        }

        for testcase in root.findall("testcase"):
            for tag in ("failure", "error"):
                node = testcase.find(tag)
                if node is not None:
                    suite["failed_cases"].append({
                        "name": testcase.get("name", "?"),
                        "kind": tag,
                        "message": node.get("message", "") or "",
                    })

        suites.append(suite)
        totals["tests"] += suite["tests"]
        totals["failures"] += suite["failures"]
        totals["errors"] += suite["errors"]
        totals["skipped"] += suite["skipped"]
        totals["time"] += suite["time"]

    return suites, totals


def suite_rows_html(suites):
    rows = []
    for s in suites:
        status_class = "status-fail" if (s["failures"] or s["errors"]) else "status-pass"
        status_text = "FAILED" if (s["failures"] or s["errors"]) else "PASSED"
        rows.append(f"""
        <tr>
          <td class="class-name">{html.escape(s['name'])}</td>
          <td class="num">{s['tests']}</td>
          <td class="num {'crit' if s['failures'] else 'muted'}">{s['failures']}</td>
          <td class="num {'crit' if s['errors'] else 'muted'}">{s['errors']}</td>
          <td class="num {'warn' if s['skipped'] else 'muted'}">{s['skipped']}</td>
          <td class="num">{s['time']:.2f}s</td>
          <td class="{status_class}">{status_text}</td>
        </tr>""")
        for fc in s["failed_cases"]:
            rows.append(f"""
        <tr class="failure-detail">
          <td colspan="7">
            <span class="tag-{'crit' if fc['kind'] == 'failure' else 'warn'}">{fc['kind'].upper()}</span>
            <code>{html.escape(s['name'])}.{html.escape(fc['name'])}</code>
            {'&mdash; ' + html.escape(fc['message']) if fc['message'] else ''}
          </td>
        </tr>""")
    return "\n".join(rows) if rows else '<tr><td colspan="7" class="muted">No Surefire XML reports found.</td></tr>'


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #F7F8FC; --surface: #FFFFFF; --border: #DBDFEA; --text: #1A1D2B; --muted: #656F91;
    --pass: #2E7D32; --fail: #C62828;
    --crit: #B71C1C; --warn: #B8860B;
    --header-bg: #1A237E; --header-fg: #FFFFFF; --alt-row: #EEF1FC;
    --focus: #4353C4;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --pass: #66BB6A; --fail: #EF5350; --warn: #E0B93D;
      --alt-row: #1E2130; --focus: #8891E8;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --pass: #66BB6A; --fail: #EF5350; --warn: #E0B93D;
    --alt-row: #1E2130; --focus: #8891E8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }}
  h1 {{ font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }}
  .subtitle {{ color: var(--muted); margin: 0 0 2rem; font-size: 0.95rem; }}
  .subtitle code {{ font-size: 0.9em; }}
  section {{ margin-bottom: 3rem; }}
  h2 {{ font-size: 1.15rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 1rem; margin-top: 1rem; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 1rem 1.1rem; }}
  .card .label {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
  .card .value {{ font-size: 1.7rem; font-weight: 700; margin-top: 0.2rem; }}
  .card.overall .value.status-pass {{ color: var(--pass); }}
  .card.overall .value.status-fail {{ color: var(--fail); }}
  .table-scroll {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }}
  table {{ border-collapse: collapse; width: 100%; min-width: 640px; background: var(--surface); font-variant-numeric: tabular-nums; }}
  th, td {{ padding: 0.55rem 0.7rem; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  th.class-col, td.class-name {{ text-align: left; white-space: normal; font-variant-numeric: normal; }}
  thead th {{ position: sticky; top: 0; background: var(--header-bg); color: var(--header-fg); font-weight: 600; text-align: right; }}
  thead th.class-col {{ text-align: left; }}
  tbody tr:nth-child(even) {{ background: var(--alt-row); }}
  tr.failure-detail td {{ text-align: left; white-space: normal; background: transparent; border-bottom: 1px solid var(--border); font-size: 0.85rem; color: var(--muted); }}
  .status-pass {{ color: var(--pass); font-weight: 700; }}
  .status-fail {{ color: var(--fail); font-weight: 700; }}
  .crit {{ color: var(--crit); font-weight: 600; }}
  .warn {{ color: var(--warn); font-weight: 600; }}
  .muted {{ color: var(--muted); }}
  .tag-crit, .tag-warn {{ display: inline-block; padding: 0.05rem 0.4rem; border-radius: 4px; font-size: 0.72rem; font-weight: 700; margin-right: 0.4rem; }}
  .tag-crit {{ background: var(--crit); color: #fff; }}
  .tag-warn {{ background: var(--warn); color: #1A1D2B; }}
  details {{ border: 1px solid var(--border); border-radius: 8px; background: var(--surface); }}
  details summary {{ cursor: pointer; padding: 0.85rem 1rem; font-weight: 600; }}
  pre {{
    margin: 0; padding: 1rem; overflow-x: auto; font: 12.5px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
    border-top: 1px solid var(--border); white-space: pre-wrap; word-break: break-word;
  }}
  a {{ color: var(--focus); }}
  a:focus-visible, summary:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
  footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 3rem; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">Generated {generated} &middot; command: <code>{command}</code></p>

  <section>
    <h2>Summary</h2>
    <div class="cards">
      <div class="card overall">
        <div class="label">Result</div>
        <div class="value {overall_class}">{overall_text}</div>
      </div>
      <div class="card"><div class="label">Tests run</div><div class="value">{tests}</div></div>
      <div class="card"><div class="label">Failures</div><div class="value">{failures}</div></div>
      <div class="card"><div class="label">Errors</div><div class="value">{errors}</div></div>
      <div class="card"><div class="label">Skipped</div><div class="value">{skipped}</div></div>
      <div class="card"><div class="label">Duration</div><div class="value">{duration}</div></div>
    </div>
  </section>

  <section>
    <h2>Test Classes</h2>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th class="class-col">Class</th>
            <th>Tests</th><th>Failures</th><th>Errors</th><th>Skipped</th><th>Time</th><th>Status</th>
          </tr>
        </thead>
        <tbody>
          {suite_rows}
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Maven Console Output</h2>
    <details {open_attr}>
      <summary>{log_summary}</summary>
      <pre>{log_text}</pre>
    </details>
  </section>

  <footer>
    Source: <a href="{repo_url}" target="_blank">{repo_url}</a> &middot;
    Test source: <a href="{test_source_url}" target="_blank">UserRepositoryIntegrationTest.java</a>
  </footer>
</main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, help="Path to the captured Maven console output")
    parser.add_argument("--surefire-dir", required=True, help="Path to target/surefire-reports")
    parser.add_argument("--output", required=True, help="Path to write the generated HTML report")
    parser.add_argument("--title", default="Testcontainers Integration Tests — Maven Result")
    parser.add_argument("--command", default="./mvnw -f Testcontainers/pom.xml test")
    args = parser.parse_args()

    suites, totals = parse_surefire_reports(args.surefire_dir)
    overall_fail = bool(totals["failures"] or totals["errors"]) or (not suites)
    overall_class = "status-fail" if overall_fail else "status-pass"
    overall_text = "FAILED" if overall_fail else "PASSED"

    if os.path.isfile(args.log):
        with open(args.log, "r", errors="replace") as f:
            log_text = f.read()
    else:
        log_text = "(no console output captured)"

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    page = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=generated,
        command=html.escape(args.command),
        overall_class=overall_class,
        overall_text=overall_text,
        tests=totals["tests"],
        failures=totals["failures"],
        errors=totals["errors"],
        skipped=totals["skipped"],
        duration=f"{totals['time']:.2f}s",
        suite_rows=suite_rows_html(suites),
        open_attr="" if not overall_fail else "open",
        log_summary="Show raw output" if not overall_fail else "Show raw output (build failed)",
        log_text=html.escape(log_text),
        repo_url=REPO_URL,
        test_source_url=f"{REPO_URL}/blob/master/Testcontainers/src/test/java/com/example/testcontainers/UserRepositoryIntegrationTest.java",
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(page)

    print(f"Wrote report to {args.output} ({overall_text}, {totals['tests']} tests)")
    if overall_fail and suites:
        # Don't mask a real test failure — the workflow step that ran `mvn test`
        # already reflects it via its own exit code, so no need to sys.exit here.
        pass


if __name__ == "__main__":
    sys.exit(main())
