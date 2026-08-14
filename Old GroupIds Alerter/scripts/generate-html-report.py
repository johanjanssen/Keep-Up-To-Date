#!/usr/bin/env python3
"""
Generate a single self-contained static HTML report showing exactly what the
Old GroupIds Alerter (OGA) Maven plugin found in the demo project's real
pom.xml — the old <groupId>/<artifactId> next to the replacement it should
become, each pulled straight from the actual pom.xml text and the plugin's
actual console output.

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Usage:
  python3 generate-html-report.py <oga_output_log> <pom_xml> <output_html> \\
      --title "Old GroupIds Alerter — groupIds that moved"
"""
import argparse
import html
import os
import re
import sys
from datetime import datetime, timezone

# Matches both message shapes oga-maven-plugin's check goal logs:
#   'groupId:artifactId' should be replaced by 'newGroupId:newArtifactId' (context: ...)
#   'groupId' groupId should be replaced by newGroupId (context: ...)
FINDING_RE = re.compile(
    r"'(?P<old>[^']+)'\s+(?:groupId\s+)?should be replaced by\s+"
    r"'?(?P<new>[^'()\s][^'()]*?)'?\s*(?:\(context:\s*(?P<context>.*?)\))?\s*$"
)

DEP_BLOCK_RE = re.compile(r"<dependency>.*?</dependency>", re.DOTALL)
GROUP_RE = re.compile(r"<groupId>\s*([^<]+?)\s*</groupId>")
ARTIFACT_RE = re.compile(r"<artifactId>\s*([^<]+?)\s*</artifactId>")
VERSION_RE = re.compile(r"<version>\s*([^<]+?)\s*</version>")


def parse_findings(text):
    """Extract unique (old, new, context) findings from the plugin's console output."""
    seen = set()
    findings = []
    for line in text.splitlines():
        if "should be replaced by" not in line:
            continue
        m = FINDING_RE.search(line)
        if not m:
            continue
        old, new, context = m.group("old"), m.group("new").strip(), m.group("context")
        key = (old, new)
        if key in seen:
            continue
        seen.add(key)
        findings.append({"old": old, "new": new, "context": context})
    return findings


def index_pom_dependencies(pom_text):
    """Map 'groupId:artifactId' -> raw <dependency>...</dependency> block text."""
    index = {}
    for block in DEP_BLOCK_RE.findall(pom_text):
        gm, am = GROUP_RE.search(block), ARTIFACT_RE.search(block)
        if not gm or not am:
            continue
        index[f"{gm.group(1)}:{am.group(1)}"] = block
    return index


def build_after_block(before_block, old_ga, new_ga):
    """Rewrite a <dependency> block's groupId/artifactId to the proposed coordinate."""
    old_group, _, old_artifact = old_ga.partition(":")
    new_group, _, new_artifact = new_ga.partition(":")
    artifact_changed = bool(new_artifact) and new_artifact != old_artifact

    after = GROUP_RE.sub(f"<groupId>{new_group}</groupId>", before_block, count=1)
    if new_artifact:
        after = ARTIFACT_RE.sub(f"<artifactId>{new_artifact}</artifactId>", after, count=1)

    has_version = bool(VERSION_RE.search(after))
    note = None
    if artifact_changed:
        note = (
            "The artifactId changed too — any inherited/managed version most likely does "
            "NOT exist for the new coordinate. Pin an explicit, current version."
        )
    elif not has_version:
        note = (
            "No explicit &lt;version&gt; here — it was inherited from the parent BOM, which "
            "does not manage the new coordinate. Add an explicit, current version."
        )
    return after, note


def render_finding(f, idx, pom_index):
    old_block = pom_index.get(f["old"])
    anchor = f"finding-{idx}"
    context_html = (
        f'<p class="context">{html.escape(f["context"])}</p>' if f.get("context") else ""
    )

    if old_block is None:
        # Fallback: no matching pom.xml block found (e.g. groupId-only finding) —
        # still show the coordinates the plugin reported.
        body = f"""
      <div class="coord-row">
        <div class="coord before"><span class="tag">before</span><code>{html.escape(f["old"])}</code></div>
        <div class="arrow">→</div>
        <div class="coord after"><span class="tag">after</span><code>{html.escape(f["new"])}</code></div>
      </div>"""
    else:
        after_block, note = build_after_block(old_block, f["old"], f["new"])
        note_html = f'<p class="note">⚠ {note}</p>' if note else ""
        body = f"""
      <div class="pom-row">
        <div class="pom-col">
          <div class="pom-label before-label">pom.xml — before</div>
          <pre class="pom-block before-block">{html.escape(old_block.strip())}</pre>
        </div>
        <div class="pom-col">
          <div class="pom-label after-label">pom.xml — after</div>
          <pre class="pom-block after-block">{html.escape(after_block.strip())}</pre>
          {note_html}
        </div>
      </div>"""

    return f"""
    <section class="finding" id="{anchor}">
      <h3><code>{html.escape(f["old"])}</code> <span class="sep">→</span> <code>{html.escape(f["new"])}</code></h3>
      {context_html}
      {body}
    </section>"""


def render_finding_index(findings):
    rows = []
    for idx, f in enumerate(findings):
        rows.append(
            f'<li><a href="#finding-{idx}">{html.escape(f["old"])}</a>'
            f'<span class="arrow-small">→</span>'
            f'<span class="new-ga">{html.escape(f["new"])}</span></li>'
        )
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
    --add-bg: #E4F5E1; --add-fg: #1C5B26; --del-bg: #FBE7E7; --del-fg: #8C1F1F;
    --header-bg: #1A237E; --header-fg: #FFFFFF; --alt-row: #EEF1FC;
    --focus: #4353C4; --ok: #1C5B26; --ok-bg: #E4F5E1; --warn: #8C5A00; --warn-bg: #FBF0DA;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --add-bg: #123320; --add-fg: #7FD68F; --del-bg: #3A1414; --del-fg: #E68080;
      --alt-row: #1E2130; --focus: #8891E8; --ok: #7FD68F; --ok-bg: #123320;
      --warn: #E0B93D; --warn-bg: #332A10;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --add-bg: #123320; --add-fg: #7FD68F; --del-bg: #3A1414; --del-fg: #E68080;
    --alt-row: #1E2130; --focus: #8891E8; --ok: #7FD68F; --ok-bg: #123320;
    --warn: #E0B93D; --warn-bg: #332A10;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }}
  h1 {{ font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }}
  .subtitle {{ color: var(--muted); margin: 0 0 2rem; font-size: 0.95rem; }}
  a {{ color: var(--focus); }}
  h2 {{ font-size: 1.05rem; margin: 2.5rem 0 0.9rem; }}
  h3 {{ font-size: 1rem; margin: 0 0 0.5rem; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  h3 .sep {{ color: var(--muted); font-family: -apple-system, sans-serif; }}

  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.9rem; }}
  .card {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 0.9rem 1.1rem;
  }}
  .card .label {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
  .card .value {{ font-size: 1.4rem; margin-top: 0.25rem; font-weight: 600; }}
  .badge {{ display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.82rem; font-weight: 600; }}
  .badge.warn {{ background: var(--warn-bg); color: var(--warn); }}

  .finding-index {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 0.3rem; }}
  .finding-index li {{
    display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.45rem 0.8rem; font-size: 0.86rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  }}
  .finding-index a {{ text-decoration: none; color: var(--del-fg); }}
  .finding-index .new-ga {{ color: var(--add-fg); }}
  .finding-index .arrow-small {{ color: var(--muted); font-family: -apple-system, sans-serif; }}

  .finding {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    margin-bottom: 1.2rem; padding: 1rem 1.2rem 1.2rem;
  }}
  .finding code {{ color: var(--del-fg); }}
  .finding h3 code:last-of-type {{ color: var(--add-fg); }}
  .context {{ color: var(--muted); font-size: 0.88rem; margin: 0 0 0.9rem; }}

  .coord-row {{ display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }}
  .coord {{ display: flex; align-items: center; gap: 0.5rem; }}
  .coord .tag {{
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted);
  }}
  .coord code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  .coord.after code {{ color: var(--add-fg); }}
  .arrow {{ color: var(--muted); }}

  .pom-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
  @media (max-width: 800px) {{ .pom-row {{ grid-template-columns: 1fr; }} }}
  .pom-label {{
    font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted);
    margin-bottom: 0.35rem;
  }}
  .pom-block {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.82rem; white-space: pre-wrap; word-break: break-word;
    border-radius: 8px; padding: 0.7rem 0.9rem; margin: 0; overflow-x: auto;
  }}
  .before-block {{ background: var(--del-bg); color: var(--del-fg); }}
  .after-block {{ background: var(--add-bg); color: var(--add-fg); }}
  .note {{ color: var(--warn); background: var(--warn-bg); border-radius: 8px; padding: 0.5rem 0.7rem;
           font-size: 0.82rem; margin: 0.6rem 0 0; }}

  footer {{ margin-top: 3rem; color: var(--muted); font-size: 0.82rem; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">
    Every finding below is real output from
    <code>biz.lermitage.oga:oga-maven-plugin:check</code> run against this demo's
    actual <code>pom.xml</code> — the "before" block is the literal dependency
    declaration; "after" is the same block rewritten to the coordinate the plugin
    recommends. Generated {generated}.
  </p>

  <h2>Summary</h2>
  <div class="cards">
    <div class="card">
      <div class="label">Old groupIds found</div>
      <div class="value">{finding_count}</div>
    </div>
    <div class="card">
      <div class="label">Plugin</div>
      <div class="value" style="font-size: 0.95rem;">oga-maven-plugin:check</div>
    </div>
    <div class="card">
      <div class="label">CI gate</div>
      <div class="value"><span class="badge warn">would fail the build</span></div>
    </div>
  </div>

  <h2>Findings ({finding_count})</h2>
  <ul class="finding-index">
{finding_index_html}
  </ul>

  {finding_sections_html}

  <footer>
    Built by the <a href="https://github.com/johanjanssen/Keep-Up-To-Date/actions/workflows/old-groupids-alerter.yml">Old GroupIds Alerter GitHub Action</a>
    from <a href="https://github.com/johanjanssen/Keep-Up-To-Date/tree/master/Old%20GroupIds%20Alerter">Old GroupIds Alerter/</a>,
    using <a href="https://github.com/jonathanlermitage/oga-maven-plugin">oga-maven-plugin</a>.
    <a href="../">← back to Keep Up To Date</a>
  </footer>
</main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("oga_output_log")
    ap.add_argument("pom_xml")
    ap.add_argument("output_html")
    ap.add_argument("--title", default="Old GroupIds Alerter — groupIds that moved")
    args = ap.parse_args()

    with open(args.oga_output_log, "r", encoding="utf-8", errors="replace") as fh:
        log_text = fh.read()
    with open(args.pom_xml, "r", encoding="utf-8", errors="replace") as fh:
        pom_text = fh.read()

    findings = parse_findings(log_text)
    pom_index = index_pom_dependencies(pom_text)

    if not findings:
        print("WARNING: no findings parsed from oga output — report will be empty.", file=sys.stderr)

    html_out = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        finding_count=len(findings),
        finding_index_html=render_finding_index(findings) or "<li>(none)</li>",
        finding_sections_html="\n".join(
            render_finding(f, i, pom_index) for i, f in enumerate(findings)
        ),
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.output_html)), exist_ok=True)
    with open(args.output_html, "w", encoding="utf-8") as fh:
        fh.write(html_out)

    print(f"Wrote {args.output_html} ({len(findings)} findings)")


if __name__ == "__main__":
    sys.exit(main())
