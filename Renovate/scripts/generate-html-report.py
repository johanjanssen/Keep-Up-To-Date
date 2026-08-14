#!/usr/bin/env python3
"""
Generate a single self-contained static HTML report showing the real pull
requests Renovate opened against an ephemeral Gitea instance (created by
Renovate/scripts/06-export-prs.sh) — real titles, real labels, real diffs.

The Gitea instance is torn down at the end of the CI run, so this report is
the only durable record of what Renovate did; every diff below was actually
applied by the bot, not hand-written for the demo.

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Usage:
  python3 generate-html-report.py <prs.json> <output_html> \\
      --title "Renovate demo — live dependency-update PRs" \\
      --rule "Group all Spring Boot updates into one PR" \\
      --rule "Pin all Docker base image digests and auto-update them"
"""
import argparse
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

CATEGORY_ORDER = ["security", "major", "docker", "spring", "update"]
CATEGORY_META = {
    "security": {"label": "Security", "emoji": "🔴"},
    "major": {"label": "Major — review required", "emoji": "🟡"},
    "docker": {"label": "Docker digest", "emoji": "🟢"},
    "spring": {"label": "Spring Boot", "emoji": "🔵"},
    "update": {"label": "Dependency update", "emoji": "⚪"},
}


def categorize(labels):
    labels = set(labels or [])
    if "security" in labels:
        return "security"
    if "major-upgrade" in labels:
        return "major"
    if "docker" in labels:
        return "docker"
    if "spring" in labels:
        return "spring"
    return "update"


def parse_diff(text):
    """Split a unified-diff text into per-file records."""
    files = []
    current = None
    for line in (text or "").splitlines():
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


def render_diff_file(f, anchor):
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
    stat = f'<span class="stat-add">+{f["added"]}</span> <span class="stat-del">-{f["removed"]}</span>'
    return f"""
      <details class="file" id="{anchor}">
        <summary><span class="path">{html.escape(f["path"])}</span><span class="stats">{stat}</span></summary>
        <div class="diff">{body}</div>
      </details>"""


def render_pr(pr, idx):
    category = categorize(pr.get("labels"))
    meta = CATEGORY_META[category]
    files = parse_diff(pr.get("diff", ""))
    total_add = sum(f["added"] for f in files)
    total_del = sum(f["removed"] for f in files)

    labels_html = "".join(
        f'<span class="tag">{html.escape(l)}</span>' for l in pr.get("labels", [])
    )
    files_html = "\n".join(render_diff_file(f, f"pr-{idx}-file-{i}") for i, f in enumerate(files))
    if not files:
        files_html = '<p class="note">No file diff was returned for this PR.</p>'

    body = (pr.get("body") or "").strip()
    body_section = ""
    if body:
        body_section = f"""
        <details class="body">
          <summary>Renovate's PR description (raw)</summary>
          <pre class="raw-body">{html.escape(body)}</pre>
        </details>"""

    created = pr.get("created_at", "")
    try:
        created_fmt = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        created_fmt = created

    return f"""
    <article class="pr cat-{category}" id="pr-{pr.get('number')}">
      <header class="pr-header">
        <span class="cat-chip">{meta['emoji']} {meta['label']}</span>
        <span class="pr-number">#{pr.get('number')}</span>
        <h3 class="pr-title">{html.escape(pr.get('title', ''))}</h3>
      </header>
      <div class="pr-meta">
        <span class="branch"><code>{html.escape(pr.get('head', ''))}</code> → <code>{html.escape(pr.get('base', ''))}</code></span>
        <span class="created">opened {html.escape(created_fmt)}</span>
        <span class="stats"><span class="stat-add">+{total_add}</span> <span class="stat-del">-{total_del}</span> · {len(files)} file(s)</span>
        {labels_html}
      </div>
      {body_section}
      <div class="files">{files_html}</div>
    </article>"""


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
    --header-bg: #1A237E; --header-fg: #FFFFFF; --alt-row: #EEF1FC;
    --focus: #4353C4; --ok: #1C5B26; --ok-bg: #E4F5E1; --warn: #8C5A00; --warn-bg: #FBF0DA;
    --chip-bg: #EEF1FC; --chip-fg: #4353C4;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --add-bg: #123320; --add-fg: #7FD68F; --del-bg: #3A1414; --del-fg: #E68080;
      --hunk-bg: #1E2130; --hunk-fg: #8891E8;
      --alt-row: #1E2130; --focus: #8891E8; --ok: #7FD68F; --ok-bg: #123320;
      --warn: #E0B93D; --warn-bg: #332A10;
      --chip-bg: #1E2130; --chip-fg: #8891E8;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --add-bg: #123320; --add-fg: #7FD68F; --del-bg: #3A1414; --del-fg: #E68080;
    --hunk-bg: #1E2130; --hunk-fg: #8891E8;
    --alt-row: #1E2130; --focus: #8891E8; --ok: #7FD68F; --ok-bg: #123320;
    --warn: #E0B93D; --warn-bg: #332A10;
    --chip-bg: #1E2130; --chip-fg: #8891E8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }}
  h1 {{ font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }}
  .subtitle {{ color: var(--muted); margin: 0 0 2rem; font-size: 0.95rem; max-width: 70ch; }}
  a {{ color: var(--focus); }}
  h2 {{ font-size: 1.05rem; margin: 2.5rem 0 0.9rem; }}

  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.9rem; }}
  .card {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 0.9rem 1.1rem;
  }}
  .card .label {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
  .card .value {{ font-size: 1.6rem; margin-top: 0.25rem; font-weight: 600; }}

  .rules {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 0.5rem; }}
  .rules li {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.6rem 0.9rem; font-size: 0.9rem;
  }}

  .empty {{
    background: var(--surface); border: 1px dashed var(--border); border-radius: 10px;
    padding: 1.5rem; color: var(--muted);
  }}

  .pr {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 1.1rem 1.2rem; margin-bottom: 1.1rem;
  }}
  .pr-header {{ display: flex; align-items: baseline; gap: 0.6rem; flex-wrap: wrap; }}
  .cat-chip {{
    background: var(--chip-bg); color: var(--chip-fg); border-radius: 999px;
    padding: 0.15rem 0.65rem; font-size: 0.78rem; font-weight: 600; white-space: nowrap;
  }}
  .pr-number {{ color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.9rem; }}
  .pr-title {{ font-size: 1.05rem; margin: 0; }}
  .pr-meta {{
    display: flex; gap: 0.9rem; flex-wrap: wrap; align-items: center;
    color: var(--muted); font-size: 0.82rem; margin: 0.5rem 0 0.8rem;
  }}
  .pr-meta code {{ font-size: 0.8rem; }}
  .tag {{
    background: var(--alt-row); border-radius: 999px; padding: 0.1rem 0.55rem;
    font-size: 0.75rem;
  }}
  .stat-add {{ color: var(--add-fg); }}
  .stat-del {{ color: var(--del-fg); }}

  details.body {{ margin: 0 0 0.8rem; }}
  details.body summary {{ cursor: pointer; color: var(--muted); font-size: 0.85rem; }}
  .raw-body {{
    white-space: pre-wrap; font-size: 0.78rem; background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 0.7rem 0.9rem; max-height: 260px; overflow: auto; margin-top: 0.5rem;
    color: var(--muted);
  }}

  details.file {{
    background: var(--bg); border: 1px solid var(--border); border-radius: 8px;
    margin-bottom: 0.6rem; overflow: hidden;
  }}
  details.file summary {{
    cursor: pointer; list-style: none; padding: 0.5rem 0.8rem; display: flex;
    justify-content: space-between; gap: 1rem; background: var(--header-bg); color: var(--header-fg);
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.84rem;
  }}
  details.file summary::-webkit-details-marker {{ display: none; }}
  details.file summary .stats {{ color: var(--header-fg); opacity: 0.85; }}
  .diff {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.8rem; overflow-x: auto;
  }}
  .diff .line {{ display: flex; padding: 0 0.6rem; white-space: pre; }}
  .diff .sign {{ width: 1.2rem; flex: none; color: var(--muted); user-select: none; }}
  .diff .code {{ white-space: pre; }}
  .diff .add {{ background: var(--add-bg); color: var(--add-fg); }}
  .diff .del {{ background: var(--del-bg); color: var(--del-fg); }}
  .diff .ctx {{ color: var(--text); }}
  .diff .hunk {{ background: var(--hunk-bg); color: var(--hunk-fg); padding: 0.25rem 0.6rem; font-weight: 600; }}

  .note {{ color: var(--muted); font-size: 0.85rem; }}
  footer {{ margin-top: 3rem; color: var(--muted); font-size: 0.82rem; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">
    A fresh Gitea instance and Renovate bot ran in GitHub Actions
    (<code>bash Renovate/scripts/demo.sh</code>, minus the Jenkins step) against this
    repository's actual dependencies. Every pull request, label, and diff below is real
    output from that run — not a mock-up — captured before the ephemeral Gitea instance
    was torn down. Generated {generated}.
  </p>

  <h2>Pull requests opened</h2>
  <div class="cards">
    <div class="card"><div class="label">Total</div><div class="value">{total}</div></div>
    <div class="card"><div class="label">🔴 Security</div><div class="value">{count_security}</div></div>
    <div class="card"><div class="label">🟡 Major</div><div class="value">{count_major}</div></div>
    <div class="card"><div class="label">🟢 Docker digest</div><div class="value">{count_docker}</div></div>
    <div class="card"><div class="label">🔵 Spring Boot</div><div class="value">{count_spring}</div></div>
  </div>

  <h2>How Renovate is configured</h2>
  <ul class="rules">{rules_html}</ul>

  <h2>Pull requests</h2>
  {prs_html}

  <footer>
    Built by the <a href="https://github.com/johanjanssen/Keep-Up-To-Date/actions/workflows/renovate.yml">Renovate GitHub Action</a>
    from <a href="https://github.com/johanjanssen/Keep-Up-To-Date/tree/master/Renovate">Renovate/</a>.
    Run it yourself locally with real Jenkins builds: <code>bash Renovate/scripts/demo.sh</code>.
    <a href="../">← back to Keep Up To Date</a>
  </footer>
</main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prs_json")
    ap.add_argument("output_html")
    ap.add_argument("--title", default="Renovate demo — live dependency-update PRs")
    ap.add_argument(
        "--rule",
        action="append",
        default=[],
        help="one bullet under 'How Renovate is configured' — may be repeated",
    )
    args = ap.parse_args()

    with open(args.prs_json, "r", encoding="utf-8") as fh:
        prs = json.load(fh)

    # Security first, then major/review, then everything else, newest within each group last.
    order = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    prs_sorted = sorted(prs, key=lambda p: order.get(categorize(p.get("labels")), 99))

    counts = {c: 0 for c in CATEGORY_ORDER}
    for p in prs:
        counts[categorize(p.get("labels"))] += 1

    if prs_sorted:
        prs_html = "\n".join(render_pr(p, i) for i, p in enumerate(prs_sorted))
    else:
        prs_html = (
            '<div class="empty">No open pull requests were found when this report ran — '
            "either every tracked dependency was already up to date, or Renovate hadn't "
            "finished its scan yet. Re-run the workflow to refresh this report.</div>"
        )

    rules_html = "\n".join(f"<li>{html.escape(r)}</li>" for r in args.rule)
    rules_html += "\n<li>Security PRs (CVE alerts) are created immediately, outside the normal schedule, and auto-merge once CI passes.</li>"

    html_out = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        total=len(prs),
        count_security=counts["security"],
        count_major=counts["major"],
        count_docker=counts["docker"],
        count_spring=counts["spring"],
        rules_html=rules_html or "<li>(none)</li>",
        prs_html=prs_html,
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.output_html)), exist_ok=True)
    with open(args.output_html, "w", encoding="utf-8") as fh:
        fh.write(html_out)

    print(f"Wrote {args.output_html} ({len(prs)} PRs)")


if __name__ == "__main__":
    sys.exit(main())
