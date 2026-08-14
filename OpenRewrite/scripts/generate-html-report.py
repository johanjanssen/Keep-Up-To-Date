#!/usr/bin/env python3
"""
Generate a single self-contained static HTML report showing the changes
OpenRewrite made to the demo project (a real unified diff, syntax-colored,
plus a before/after summary).

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Usage:
  python3 generate-html-report.py <diff_file> <output_html> \\
      --before-tests "Tests run: 18, Failures: 0, Errors: 0, Skipped: 0" \\
      --after-tests  "Tests run: 18, Failures: 1, Errors: 0, Skipped: 0" \\
      --title "OpenRewrite: Spring Boot 2 -> 4, Java 17 -> 25, JUnit 4 -> 5"
"""
import argparse
import html
import os
import re
import sys
from datetime import datetime, timezone


def parse_diff(text):
    """Split a `git diff` unified-diff text into per-file records."""
    files = []
    current = None
    for line in text.splitlines():
        m = re.match(r"^diff --git a/(.+?) b/(.+)$", line)
        if m:
            if current:
                files.append(current)
            current = {"path": m.group(2), "lines": [], "added": 0, "removed": 0}
            continue
        if current is None:
            continue
        if line.startswith("index ") or line.startswith("--- ") or line.startswith("+++ "):
            continue
        if line.startswith("@@"):
            current["lines"].append(("hunk", line))
            continue
        if line.startswith("+"):
            current["added"] += 1
            current["lines"].append(("add", line[1:]))
        elif line.startswith("-"):
            current["removed"] += 1
            current["lines"].append(("del", line[1:]))
        elif line.startswith("\\"):
            continue
        else:
            current["lines"].append(("ctx", line[1:] if line.startswith(" ") else line))
    if current:
        files.append(current)
    return files


def render_file_section(f, idx):
    rows = []
    for kind, content in f["lines"]:
        if kind == "hunk":
            rows.append(f'<div class="hunk">{html.escape(content)}</div>')
        else:
            cls = {"add": "add", "del": "del", "ctx": "ctx"}[kind]
            sign = {"add": "+", "del": "-", "ctx": " "}[kind]
            rows.append(
                f'<div class="line {cls}"><span class="sign">{sign}</span>'
                f'<span class="code">{html.escape(content)}</span></div>'
            )
    body = "\n".join(rows)
    anchor = f"file-{idx}"
    stat = f'<span class="stat-add">+{f["added"]}</span> <span class="stat-del">-{f["removed"]}</span>'
    return f"""
    <details class="file" id="{anchor}" open>
      <summary><span class="path">{html.escape(f["path"])}</span><span class="stats">{stat}</span></summary>
      <div class="diff">{body}</div>
    </details>"""


def parse_test_summary(s):
    """'Tests run: 18, Failures: 1, Errors: 0, Skipped: 0' -> dict, or None."""
    if not s:
        return None
    m = re.search(
        r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)", s
    )
    if not m:
        return None
    run, fail, err, skip = (int(x) for x in m.groups())
    return {"run": run, "fail": fail, "err": err, "skip": skip, "passed": run - fail - err - skip}


def test_badge(summary):
    if summary is None:
        return '<span class="badge muted">not run</span>'
    if summary["fail"] == 0 and summary["err"] == 0:
        return f'<span class="badge ok">{summary["passed"]}/{summary["run"]} passed</span>'
    return (
        f'<span class="badge warn">{summary["passed"]}/{summary["run"]} passed, '
        f'{summary["fail"] + summary["err"]} failing</span>'
    )


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #F7F8FC; --surface: #FFFFFF; --border: #DBDFEA; --text: #1A1D2B; --muted: #656F91;
    --add-bg: #E4F5E1; --add-fg: #1C5B26; --del-bg: #FBE7E7; --del-fg: #8C1F1F;
    --hunk-bg: #EEF1FC; --hunk-fg: #4353C4;
    --alt-row: #EEF1FC;
    --focus: #4353C4; --ok: #1C5B26; --ok-bg: #E4F5E1; --warn: #8C5A00; --warn-bg: #FBF0DA;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --add-bg: #123320; --add-fg: #7FD68F; --del-bg: #3A1414; --del-fg: #E68080;
      --hunk-bg: #1E2130; --hunk-fg: #8891E8;
      --alt-row: #1E2130; --focus: #8891E8; --ok: #7FD68F; --ok-bg: #123320;
      --warn: #E0B93D; --warn-bg: #332A10;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --add-bg: #123320; --add-fg: #7FD68F; --del-bg: #3A1414; --del-fg: #E68080;
    --hunk-bg: #1E2130; --hunk-fg: #8891E8;
    --alt-row: #1E2130; --focus: #8891E8; --ok: #7FD68F; --ok-bg: #123320;
    --warn: #E0B93D; --warn-bg: #332A10;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  main {{ max-width: 1200px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }}
  h1 {{ font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }}
  .subtitle {{ color: var(--muted); margin: 0 0 2rem; font-size: 0.95rem; }}
  a {{ color: var(--focus); }}
  h2 {{ font-size: 1.05rem; margin: 2.5rem 0 0.9rem; }}

  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.9rem; }}
  .card {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 0.9rem 1.1rem;
  }}
  .card .label {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
  .card .value {{ font-size: 1.05rem; margin-top: 0.25rem; }}
  .card .value .arrow {{ color: var(--muted); margin: 0 0.3rem; }}
  .card .before {{ color: var(--del-fg); }}
  .card .after {{ color: var(--ok); font-weight: 600; }}

  .recipes {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }}
  .recipes li {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.6rem 0.9rem; font-size: 0.9rem;
  }}
  .recipes code {{ font-size: 0.85rem; }}

  .test-row {{ display: flex; gap: 1.5rem; flex-wrap: wrap; align-items: center; }}
  .badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.82rem; font-weight: 600; }}
  .badge.ok {{ background: var(--ok-bg); color: var(--ok); }}
  .badge.warn {{ background: var(--warn-bg); color: var(--warn); }}
  .badge.muted {{ background: var(--alt-row); color: var(--muted); }}
  .note {{ color: var(--muted); font-size: 0.88rem; margin-top: 0.6rem; }}

  .stats {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.82rem; white-space: nowrap; }}
  .stat-add {{ color: var(--add-fg); }}
  .stat-del {{ color: var(--del-fg); }}

  details.file {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    margin-bottom: 1rem; overflow: hidden;
  }}
  details.file summary {{
    cursor: pointer; list-style: none; padding: 0.7rem 1rem; display: flex;
    justify-content: space-between; gap: 1rem; background: var(--surface); color: var(--text);
    border-bottom: 1px solid var(--border);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.88rem;
  }}
  details.file summary::-webkit-details-marker {{ display: none; }}
  .diff {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.82rem; overflow-x: auto;
  }}
  .diff .line {{ display: flex; padding: 0 0.6rem; white-space: pre; }}
  .diff .sign {{ width: 1.2rem; flex: none; color: var(--muted); user-select: none; }}
  .diff .code {{ white-space: pre; }}
  .diff .add {{ background: var(--add-bg); color: var(--add-fg); }}
  .diff .del {{ background: var(--del-bg); color: var(--del-fg); }}
  .diff .ctx {{ color: var(--text); }}
  .diff .hunk {{ background: var(--hunk-bg); color: var(--hunk-fg); padding: 0.25rem 0.6rem; font-weight: 600; }}

  footer {{ margin-top: 3rem; color: var(--muted); font-size: 0.82rem; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">
    Recipes run by OpenRewrite against the demo project's actual source — every line below is a
    real change the recipes made, not a mock-up.
    Generated {generated}.
  </p>

  <h2>Before → after</h2>
  <div class="cards">
    <div class="card">
      <div class="label">Spring Boot</div>
      <div class="value"><span class="before">{sb_before}</span><span class="arrow">→</span><span class="after">{sb_after}</span></div>
    </div>
    <div class="card">
      <div class="label">Java</div>
      <div class="value"><span class="before">{java_before}</span><span class="arrow">→</span><span class="after">{java_after}</span></div>
    </div>
    <div class="card">
      <div class="label">Test framework</div>
      <div class="value"><span class="before">{junit_before}</span><span class="arrow">→</span><span class="after">{junit_after}</span></div>
    </div>
    <div class="card">
      <div class="label">Files changed</div>
      <div class="value">{file_count} files, <span class="stat-add">+{total_add}</span> <span class="stat-del">-{total_del}</span></div>
    </div>
  </div>

  <h2>Recipes applied</h2>
  <ul class="recipes">{recipes_html}</ul>

  <h2>Tests</h2>
  <div class="test-row">
    <div>Before migration: {before_badge}</div>
    <div>After migration: {after_badge}</div>
  </div>
  <p class="note">{test_note}</p>

  <h2>Files changed ({file_count})</h2>
  {file_sections_html}

  <footer>
    Built by the <a href="https://github.com/johanjanssen/Keep-Up-To-Date/actions/workflows/openrewrite.yml">OpenRewrite GitHub Action</a>
    from <a href="https://github.com/johanjanssen/Keep-Up-To-Date/tree/master/OpenRewrite">OpenRewrite/</a>.
    <a href="../">← back to Keep Up To Date</a>
  </footer>
</main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("diff_file")
    ap.add_argument("output_html")
    ap.add_argument("--title", default="OpenRewrite demo — changes applied")
    ap.add_argument("--sb-before", default="2.7.18")
    ap.add_argument("--sb-after", default="4.0.x")
    ap.add_argument("--java-before", default="17")
    ap.add_argument("--java-after", default="25")
    ap.add_argument("--junit-before", default="JUnit 4")
    ap.add_argument("--junit-after", default="JUnit 5")
    ap.add_argument("--before-tests", default="")
    ap.add_argument("--after-tests", default="")
    ap.add_argument(
        "--recipe",
        action="append",
        default=[],
        help="recipe:short description — may be repeated",
    )
    args = ap.parse_args()

    with open(args.diff_file, "r", encoding="utf-8", errors="replace") as fh:
        diff_text = fh.read()

    files = parse_diff(diff_text)
    total_add = sum(f["added"] for f in files)
    total_del = sum(f["removed"] for f in files)

    recipes_html = "\n".join(
        f'<li><code>{html.escape(r.split(":", 1)[0])}</code> — {html.escape(r.split(":", 1)[1]) if ":" in r else ""}</li>'
        for r in args.recipe
    )

    before_summary = parse_test_summary(args.before_tests)
    after_summary = parse_test_summary(args.after_tests)
    test_note = ""
    if after_summary and (after_summary["fail"] or after_summary["err"]):
        test_note = (
            "One pre-existing test intentionally asserted the OLD buggy behaviour "
            "(a NullPointerException on a null role) — EqualsAvoidsNull just fixed that bug, "
            "so the test now fails and needs updating. That's expected: automated codemods "
            "still need a human to review tests that encoded the bug they fix."
        )

    html_out = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        sb_before=html.escape(args.sb_before),
        sb_after=html.escape(args.sb_after),
        java_before=html.escape(args.java_before),
        java_after=html.escape(args.java_after),
        junit_before=html.escape(args.junit_before),
        junit_after=html.escape(args.junit_after),
        file_count=len(files),
        total_add=total_add,
        total_del=total_del,
        recipes_html=recipes_html or "<li>(none)</li>",
        before_badge=test_badge(before_summary),
        after_badge=test_badge(after_summary),
        test_note=test_note,
        file_sections_html="\n".join(render_file_section(f, i) for i, f in enumerate(files)),
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.output_html)), exist_ok=True)
    with open(args.output_html, "w", encoding="utf-8") as fh:
        fh.write(html_out)

    print(f"Wrote {args.output_html} ({len(files)} files, +{total_add}/-{total_del})")


if __name__ == "__main__":
    sys.exit(main())
