#!/usr/bin/env python3
"""
Generate a single self-contained static HTML report showing exactly what
`mvn dependency:analyze` found in the demo project's real pom.xml — the actual
"Unused declared dependencies" list from the plugin's own console output, each
one matched back to its real <dependency> block in pom.xml, with a real
before/after edit shown for it.

Two of the three findings (commons-lang3, guava) are genuinely dead weight —
never imported anywhere — and the "after" is simply deleting the block. The
third (h2) is a deliberate false positive: DatabaseController needs it at
runtime through java.sql.DriverManager + the JDBC 4 ServiceLoader mechanism,
never a direct org.h2.* reference, so the plugin's bytecode scan can't see it.
Its "after" keeps the dependency and instead adds a <usedDependencies> entry
that tells the plugin to stop flagging it — the real-world fix for any
reflection/SPI-loaded dependency (JDBC drivers, most of them).

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Usage:
  python3 generate-html-report.py <analyze_output_log> <pom_xml> <output_html> \\
      --title "Maven Dependency Plugin demo — dependency:analyze"
"""
import argparse
import html
import os
import re
import sys
from datetime import datetime, timezone

DEP_BLOCK_RE = re.compile(r"<dependency>.*?</dependency>", re.DOTALL)
GROUP_RE = re.compile(r"<groupId>\s*([^<]+?)\s*</groupId>")
ARTIFACT_RE = re.compile(r"<artifactId>\s*([^<]+?)\s*</artifactId>")

# Coordinate -> how this demo classifies and explains the finding. Only entries
# that also show up in the plugin's real "Unused declared dependencies" output
# make it into the report — see main().
FINDINGS_META = {
    "org.apache.commons:commons-lang3": {
        "category": "unused",
        "reason": "Declared in pom.xml, but no class under org.apache.commons.lang3.* is "
                  "imported anywhere in src/. Nothing in the compiled bytecode references it.",
        "fix": "Delete the &lt;dependency&gt; block. There is no runtime path that needs it.",
    },
    "com.google.guava:guava": {
        "category": "unused",
        "reason": "Same story as commons-lang3: declared, never imported, nothing in the "
                  "compiled bytecode references com.google.common.*.",
        "fix": "Delete the &lt;dependency&gt; block. There is no runtime path that needs it.",
    },
    "com.h2database:h2": {
        "category": "false-positive",
        "reason": "DatabaseController opens a JDBC connection via java.sql.DriverManager and "
                  "queries it (see /db-check) — h2 IS used, but only through the JDBC 4 "
                  "ServiceLoader mechanism (h2's jar ships META-INF/services/java.sql.Driver, "
                  "so the driver self-registers). No class from org.h2.* ever appears in this "
                  "project's own bytecode, which is all dependency:analyze can see.",
        "fix": "Keep the &lt;dependency&gt;. Instead, tell the plugin explicitly that it's used "
               "by adding a &lt;usedDependencies&gt; entry to maven-dependency-plugin's "
               "&lt;configuration&gt; — the supported way to suppress a bytecode-analysis false "
               "positive without deleting a dependency the app actually needs.",
    },
}

USED_DEPENDENCIES_SNIPPET = """<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-dependency-plugin</artifactId>
    <configuration>
        <usedDependencies>
            <usedDependency>com.h2database:h2</usedDependency>
        </usedDependencies>
    </configuration>
</plugin>"""


def parse_unused_findings(text):
    """Extract 'groupId:artifactId' from the plugin's 'Unused declared dependencies found:' block."""
    lines = text.splitlines()
    findings = []
    in_block = False
    for line in lines:
        if "Unused declared dependencies found:" in line:
            in_block = True
            continue
        if in_block:
            # Lines look like: [WARNING]    org.apache.commons:commons-lang3:jar:3.20.0:compile
            m = re.search(r"([\w.\-]+:[\w.\-]+):jar:", line)
            if m:
                findings.append(m.group(1))
                continue
            # Any other content ends the block (next section header, blank INFO line, etc.)
            if findings:
                break
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


def render_finding(ga, idx, before_block, meta):
    anchor = f"finding-{idx}"
    category = meta["category"]
    badge = (
        '<span class="badge unused">unused — safe to delete</span>'
        if category == "unused"
        else '<span class="badge falsepos">false positive — needed at runtime</span>'
    )

    if category == "unused":
        after_col = f"""
        <div class="pom-col">
          <div class="pom-label after-label">pom.xml — after</div>
          <pre class="pom-block removed-block">— &lt;dependency&gt; block deleted —</pre>
        </div>"""
    else:
        after_col = f"""
        <div class="pom-col">
          <div class="pom-label after-label">pom.xml — after (dependency unchanged)</div>
          <pre class="pom-block after-block">{html.escape(before_block.strip())}</pre>
          <div class="pom-label after-label" style="margin-top:0.8rem;">pom.xml — add to &lt;build&gt;&lt;plugins&gt;</div>
          <pre class="pom-block after-block">{html.escape(USED_DEPENDENCIES_SNIPPET)}</pre>
        </div>"""

    return f"""
    <section class="finding" id="{anchor}">
      <h3><code>{html.escape(ga)}</code> {badge}</h3>
      <p class="context">{meta["reason"]}</p>
      <div class="pom-row">
        <div class="pom-col">
          <div class="pom-label before-label">pom.xml — before</div>
          <pre class="pom-block before-block">{html.escape(before_block.strip())}</pre>
        </div>
        {after_col}
      </div>
      <p class="note">→ {meta["fix"]}</p>
    </section>"""


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
  h3 {{ font-size: 1rem; margin: 0 0 0.5rem; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }}

  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.9rem; }}
  .card {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 0.9rem 1.1rem;
  }}
  .card .label {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
  .card .value {{ font-size: 1.4rem; margin-top: 0.25rem; font-weight: 600; }}
  .badge {{
    display: inline-block; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.72rem;
    font-weight: 600; font-family: -apple-system, sans-serif; letter-spacing: 0.01em;
  }}
  .badge.warn {{ background: var(--warn-bg); color: var(--warn); }}
  .badge.unused {{ background: var(--del-bg); color: var(--del-fg); }}
  .badge.falsepos {{ background: var(--warn-bg); color: var(--warn); }}

  .finding {{
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    margin-bottom: 1.2rem; padding: 1rem 1.2rem 1.2rem;
  }}
  .finding h3 code {{ color: var(--text); }}
  .context {{ color: var(--muted); font-size: 0.88rem; margin: 0 0 0.9rem; }}

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
  .removed-block {{ background: var(--del-bg); color: var(--del-fg); font-style: italic; }}
  .note {{ color: var(--warn); background: var(--warn-bg); border-radius: 8px; padding: 0.5rem 0.7rem;
           font-size: 0.85rem; margin: 0.9rem 0 0; }}

  footer {{ margin-top: 3rem; color: var(--muted); font-size: 0.82rem; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">
    Every finding below is real output from
    <code>org.apache.maven.plugins:maven-dependency-plugin:analyze</code> run against this
    demo's actual <code>pom.xml</code> — the "before" block is the literal dependency
    declaration; "after" is the real-world fix for that specific finding. Two of the three
    are genuinely dead weight; one is a JDBC-driver false positive that needs a different
    fix entirely. Generated {generated}.
  </p>

  <h2>Summary</h2>
  <div class="cards">
    <div class="card">
      <div class="label">Unused declared dependencies</div>
      <div class="value">{finding_count}</div>
    </div>
    <div class="card">
      <div class="label">Genuinely unused</div>
      <div class="value">{unused_count}</div>
    </div>
    <div class="card">
      <div class="label">False positives</div>
      <div class="value">{falsepos_count}</div>
    </div>
    <div class="card">
      <div class="label">CI gate</div>
      <div class="value"><span class="badge warn">opt-in, off by default</span></div>
    </div>
  </div>

  <h2>Findings ({finding_count})</h2>

  {finding_sections_html}

  <h2>Why this matters</h2>
  <p class="context" style="max-width:70ch;">
    <code>dependency:analyze</code> compares declared dependencies against compiled bytecode —
    it can only see direct class references. Reflection, SPI/ServiceLoader lookups (JDBC
    drivers, logging bridges, most annotation processors), and dependencies pulled in purely
    for their <code>META-INF</code> contents are all invisible to it. Treat every finding as a
    starting point for a human decision, not an automatic deletion: real dead weight should go,
    but a dependency the app genuinely needs at runtime should be kept and the warning
    suppressed explicitly via <code>&lt;usedDependencies&gt;</code> instead.
  </p>

  <footer>
    Built by the <a href="https://github.com/johanjanssen/Keep-Up-To-Date/actions/workflows/maven-dependency-plugin.yml">Maven Dependency Plugin GitHub Action</a>
    from <a href="https://github.com/johanjanssen/Keep-Up-To-Date/tree/master/Maven%20Dependency%20Plugin">Maven Dependency Plugin/</a>,
    using the <a href="https://maven.apache.org/plugins/maven-dependency-plugin/analyze-mojo.html">Maven Dependency Plugin</a>'s <code>analyze</code> goal.
    <a href="../">← back to Keep Up To Date</a>
  </footer>
</main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("analyze_output_log")
    ap.add_argument("pom_xml")
    ap.add_argument("output_html")
    ap.add_argument("--title", default="Maven Dependency Plugin demo — dependency:analyze")
    args = ap.parse_args()

    with open(args.analyze_output_log, "r", encoding="utf-8", errors="replace") as fh:
        log_text = fh.read()
    with open(args.pom_xml, "r", encoding="utf-8", errors="replace") as fh:
        pom_text = fh.read()

    found_gas = parse_unused_findings(log_text)
    pom_index = index_pom_dependencies(pom_text)

    # Only keep findings that: (a) the plugin actually reported, (b) match a real
    # <dependency> block in pom.xml, and (c) this script has an explanation for.
    # That keeps the report real (driven by actual plugin output) while still
    # being able to explain *why* each one is unused vs. a false positive.
    findings = [ga for ga in found_gas if ga in pom_index and ga in FINDINGS_META]

    if not findings:
        print("WARNING: no findings parsed from analyze output — report will be empty.", file=sys.stderr)

    unused_count = sum(1 for ga in findings if FINDINGS_META[ga]["category"] == "unused")
    falsepos_count = sum(1 for ga in findings if FINDINGS_META[ga]["category"] == "false-positive")

    html_out = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        finding_count=len(findings),
        unused_count=unused_count,
        falsepos_count=falsepos_count,
        finding_sections_html="\n".join(
            render_finding(ga, i, pom_index[ga], FINDINGS_META[ga]) for i, ga in enumerate(findings)
        ),
    )

    os.makedirs(os.path.dirname(os.path.abspath(args.output_html)), exist_ok=True)
    with open(args.output_html, "w", encoding="utf-8") as fh:
        fh.write(html_out)

    print(f"Wrote {args.output_html} ({len(findings)} findings: {unused_count} unused, {falsepos_count} false positive)")


if __name__ == "__main__":
    sys.exit(main())
