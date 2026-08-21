#!/usr/bin/env python3
"""
Stitch the per-job GitHub Step Summary markdown files produced by
demo-vulnerable-app.yml into one static HTML page for GitHub Pages.

Each demo-* job in the workflow builds its own $GITHUB_STEP_SUMMARY (a live
"command -> result" transcript of the exploit it ran) and uploads it as a
"demo-summary-NN-slug" artifact. This script downloads-artifact has already put
all of those .md files in one directory; it renders each with Python-Markdown
(fenced code + tables) and wraps them in one navigable page — no external
assets, no build step, meant to be published as-is.

Usage:
  python3 generate-vulnerable-report.py <summaries_dir> <output_html> [--title "..."] [--run-url "..."]
"""
import argparse, glob, html, os, re
from datetime import datetime, timezone

import markdown

# Section icon/name looked up by the numeric filename prefix (01-log4shell.md, ...)
# so the nav reads as a short label even though the source .md's own first heading
# is longer prose.
NAV_LABELS = {
    "01": "💀 Demo 1 — Log4Shell",
    "02": "💀 Demo 2 — Jackson",
    "03": "💀 Demo 3 — Full Chain",
    "04": "💀 Demo 4 — Privilege Escalation",
    "05": "📊 CVE Scan Comparison",
}


def slug_and_label(path):
    base = os.path.splitext(os.path.basename(path))[0]  # "01-log4shell"
    prefix = base.split("-", 1)[0]
    label = NAV_LABELS.get(prefix, base)
    return base, label


def render_section(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    body = markdown.markdown(text, extensions=["fenced_code", "tables", "nl2br"])
    slug, label = slug_and_label(path)
    return slug, label, body


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --bg: #F7F8FC; --surface: #FFFFFF; --border: #DBDFEA; --text: #1A1D2B; --muted: #656F91;
    --accent: #1565C0; --code-bg: #F0F2FA; --header-bg: #1A237E; --header-fg: #FFFFFF;
    --focus: #4353C4; --danger: #B71C1C; --nav-active: #EEF1FC;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --code-bg: #1E2130; --focus: #8891E8; --danger: #E0554A; --nav-active: #1E2130;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --code-bg: #1E2130; --focus: #8891E8; --danger: #E0554A; --nav-active: #1E2130;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  .layout {{ display: flex; max-width: 1200px; margin: 0 auto; align-items: flex-start; }}
  nav {{
    position: sticky; top: 0; flex: 0 0 220px; padding: 2rem 1rem; height: 100vh;
    overflow-y: auto; border-right: 1px solid var(--border);
  }}
  nav a {{
    display: block; padding: 0.5rem 0.75rem; border-radius: 6px; color: var(--text);
    text-decoration: none; font-size: 0.9rem; margin-bottom: 0.15rem;
  }}
  nav a:hover, nav a:focus-visible {{ background: var(--nav-active); }}
  main {{ flex: 1 1 auto; min-width: 0; padding: 2.5rem 2rem 4rem; }}
  h1 {{ font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }}
  .subtitle {{ color: var(--muted); margin: 0 0 1rem; font-size: 0.95rem; }}
  .subtitle a {{ color: var(--accent); }}
  .warn {{
    border: 1px solid var(--danger); border-radius: 8px; padding: 0.85rem 1.1rem;
    margin: 0 0 2.5rem; font-size: 0.9rem; color: var(--danger);
  }}
  section {{
    margin-bottom: 3.5rem; padding-top: 1rem; border-top: 1px solid var(--border);
  }}
  section:first-of-type {{ border-top: none; padding-top: 0; }}
  section h2 {{ font-size: 1.4rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }}
  section h3 {{ font-size: 1.1rem; margin-top: 2rem; }}
  section h4 {{ font-size: 0.95rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em; }}
  section blockquote {{
    margin: 1rem 0; padding: 0.75rem 1rem; border-left: 3px solid var(--accent);
    background: var(--code-bg); border-radius: 0 6px 6px 0;
  }}
  section blockquote p {{ margin: 0.3rem 0; }}
  pre {{
    background: var(--code-bg); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.9rem 1rem; overflow-x: auto; font: 12.5px/1.55 ui-monospace, SFMono-Regular, Menlo, monospace;
  }}
  code {{ font: inherit; }}
  :not(pre) > code {{
    background: var(--code-bg); border-radius: 4px; padding: 0.1em 0.35em;
    font-size: 0.9em;
  }}
  .table-scroll {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; background: var(--surface); margin: 1rem 0; }}
  th, td {{ padding: 0.5rem 0.7rem; text-align: left; border: 1px solid var(--border); }}
  thead th {{ background: var(--header-bg); color: var(--header-fg); font-weight: 600; }}
  a {{ color: var(--accent); }}
  a:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
  footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 3rem; }}
  @media (max-width: 820px) {{
    .layout {{ flex-direction: column; }}
    nav {{ position: static; height: auto; width: 100%; border-right: none; border-bottom: 1px solid var(--border); }}
  }}
</style>
</head>
<body>
<div class="layout">
  <nav>
    <strong style="display:block; margin: 0 0 0.75rem 0.75rem;">On this page</strong>
    {nav_links}
  </nav>
  <main>
    <h1>{title}</h1>
    <p class="subtitle">Generated {generated} from a real run of the exploit demos below —
      not a scripted transcript. {run_link}</p>
    <p class="warn">⚠️ Every exploit here runs against a deliberately vulnerable app, in
      throwaway containers, on a GitHub Actions runner that's destroyed right after the job
      finishes. Nothing shown targets, or is safe to point at, a real system.</p>
    {sections}
    <footer>Vulnerable App demos &middot; <a href="https://github.com/johanjanssen/Keep-Up-To-Date">Keep-Up-To-Date</a></footer>
  </main>
</div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("summaries_dir")
    parser.add_argument("output_html")
    parser.add_argument("--title", default="Vulnerable App — Live Exploit Demos")
    parser.add_argument("--run-url", default="")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.summaries_dir, "*.md")))
    print(f"  found {len(files)} summary file(s) in {args.summaries_dir}")

    nav_links, sections = [], []
    if files:
        for path in files:
            slug, label, body = render_section(path)
            nav_links.append(f'<a href="#{slug}">{html.escape(label)}</a>')
            sections.append(f'<section id="{slug}">\n{body}\n</section>')
    else:
        sections.append('<section><p>No demo summaries were found for this run.</p></section>')

    run_link = f'<a href="{html.escape(args.run_url)}">View the workflow run &rarr;</a>' if args.run_url else ""

    out = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        run_link=run_link,
        nav_links="\n    ".join(nav_links),
        sections="\n\n    ".join(sections),
    )

    os.makedirs(os.path.dirname(args.output_html) or ".", exist_ok=True)
    with open(args.output_html, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"  OK  html -> {args.output_html}")


if __name__ == "__main__":
    main()
