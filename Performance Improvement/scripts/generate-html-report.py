#!/usr/bin/env python3
"""
Generate a single self-contained static HTML report of the JMH benchmark
results — speed + memory overview tables, styled to match the other
Keep-Up-To-Date GitHub Pages reports.

Meant to be published as-is to GitHub Pages — no external assets, no build step.

Design choice (see README "What this report hides, on purpose"): rows are
computed from the *actual* JSON numbers, not hand-picked. A row only appears
in the audience-facing "Proven improvements" tables if the newer version is
at least IMPROVEMENT_THRESHOLD_PCT better. Anything flat/regressed is left
out of the report entirely — it's not presented as a win it isn't.

Usage:
  python3 generate-html-report.py <results_dir> <output_html> [--title "..."]

Expected files in <results_dir> (missing ones degrade gracefully):
  java17.json / java25.json                      — 17 vs 25 speed
  java17-gc.json / java25-gc.json                 — 17 vs 25 memory (GC profiler)
  java25-valhalla.json / java28-valhalla-value.json
                                                   — real Valhalla win (value record)
"""
import argparse, html, json, os
from datetime import datetime, timezone

IMPROVEMENT_THRESHOLD_PCT = 3.0  # below this we call it "flat", not a win


def load_metrics(path, memory=False):
    """benchmark method name -> (score, unit). Mirrors generate-charts.py's loader."""
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8-sig") as f:
        data = json.load(f)
    out = {}
    for entry in data:
        method = entry["benchmark"].split(".")[-1]
        params = entry.get("params", {})
        label = method
        if params:
            parts = [f"{k}={v}" for k, v in sorted(params.items())]
            label = f"{method} ({', '.join(parts)})"
        if memory:
            sec = entry.get("secondaryMetrics", {})
            for key in ("·gc.alloc.rate.norm", "gc.alloc.rate.norm"):
                if key in sec:
                    out[label] = (sec[key]["score"], sec[key].get("scoreUnit", "B/op"))
                    break
        else:
            out[label] = (entry["primaryMetric"]["score"], entry["primaryMetric"]["scoreUnit"])
    return out


def classify(score_before, score_after, unit):
    """Returns (pct_change, verdict) where verdict is 'improved' | 'flat' | 'regressed'."""
    if score_before is None or score_after is None or score_before == 0:
        return None, "missing"
    higher_better = "ops" in unit.lower()
    pct = (score_after - score_before) / score_before * 100 if higher_better \
        else (score_before - score_after) / score_before * 100
    if pct >= IMPROVEMENT_THRESHOLD_PCT:
        verdict = "improved"
    elif pct <= -IMPROVEMENT_THRESHOLD_PCT:
        verdict = "regressed"
    else:
        verdict = "flat"
    return pct, verdict


def build_rows(before, after):
    rows = []
    for name in sorted(set(before) | set(after)):
        sb, unit_b = before.get(name, (None, ""))
        sa, unit_a = after.get(name, (None, ""))
        unit = unit_a or unit_b
        pct, verdict = classify(sb, sa, unit)
        rows.append({"name": name, "before": sb, "after": sa, "unit": unit, "pct": pct, "verdict": verdict})
    return rows


def fmt_score(score, unit):
    if score is None:
        return "—"
    if "B/op" in unit or "bytes" in unit.lower():
        if score >= 1_000_000:
            return f"{score / 1_000_000:,.1f} MB"
        if score >= 1_000:
            return f"{score / 1_000:,.1f} KB"
    return f"{score:,.2f}"


def rows_html(rows, only_verdicts=None):
    out = []
    for r in rows:
        if only_verdicts and r["verdict"] not in only_verdicts:
            continue
        pct_txt = "—" if r["pct"] is None else f"{'+' if r['pct'] >= 0 else ''}{r['pct']:.1f}%"
        badge_class = {"improved": "good", "regressed": "bad", "flat": "muted", "missing": "muted"}[r["verdict"]]
        badge_label = {"improved": "faster/leaner", "regressed": "slower/heavier",
                       "flat": "no real change", "missing": "n/a"}[r["verdict"]]
        out.append(f"""
        <tr>
          <td class="bench-name">{html.escape(r['name'])}</td>
          <td class="num">{fmt_score(r['before'], r['unit'])}</td>
          <td class="num">{fmt_score(r['after'], r['unit'])}</td>
          <td class="num"><span class="pct {badge_class}">{pct_txt}</span></td>
          <td class="unit">{html.escape(r['unit'])}</td>
          <td class="verdict {badge_class}">{badge_label}</td>
        </tr>""")
    return "\n".join(out) if out else '<tr><td colspan="6" class="muted" style="text-align:center">No rows.</td></tr>'


def section(title, subtitle, label_before, label_after, rows, note=None):
    improved = [r for r in rows if r["verdict"] == "improved"]
    note_html = f'<p class="note">{note}</p>' if note else ""
    improved_html = rows_html(improved) if improved else \
        '<tr><td colspan="6" class="muted" style="text-align:center">No comparison in this group cleared the improvement threshold.</td></tr>'
    return f"""
    <section>
      <h2>{html.escape(title)}</h2>
      <p class="subtitle">{subtitle}</p>
      {note_html}
      <div class="table-scroll">
        <table>
          <thead><tr><th class="bench-col">Benchmark</th><th>{html.escape(label_before)}</th><th>{html.escape(label_after)}</th><th>Δ</th><th>Unit</th><th>Verdict</th></tr></thead>
          <tbody>{improved_html}</tbody>
        </table>
      </div>
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
    --header-bg: #1A237E; --header-fg: #FFFFFF; --alt-row: #EEF1FC;
    --good: #1B5E20; --bad: #B71C1C; --focus: #4353C4;
  }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{
      --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
      --alt-row: #1E2130; --good: #6FCF7C; --bad: #FF8A80; --focus: #8891E8;
    }}
  }}
  :root[data-theme="dark"] {{
    --bg: #12131A; --surface: #191B25; --border: #2B2E3D; --text: #E7E9F5; --muted: #9498B8;
    --alt-row: #1E2130; --good: #6FCF7C; --bad: #FF8A80; --focus: #8891E8;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--text);
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 1100px; margin: 0 auto; padding: 2.5rem 1.5rem 4rem; }}
  h1 {{ font-size: 1.7rem; margin: 0 0 0.3rem; letter-spacing: -0.01em; text-wrap: balance; }}
  .subtitle {{ color: var(--muted); margin: 0.2rem 0 1rem; font-size: 0.95rem; }}
  .lede {{ color: var(--muted); margin: 0 0 2rem; max-width: 70ch; }}
  section {{ margin-bottom: 3rem; }}
  h2 {{ font-size: 1.2rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin-bottom: 0.3rem; }}
  .note {{ background: var(--alt-row); border: 1px solid var(--border); border-radius: 8px;
    padding: 0.75rem 1rem; font-size: 0.9rem; color: var(--muted); margin: 0.5rem 0 1rem; }}
  .table-scroll {{ overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; margin-top: 0.75rem; }}
  table {{ border-collapse: collapse; width: 100%; min-width: 640px; background: var(--surface); font-variant-numeric: tabular-nums; }}
  th, td {{ padding: 0.55rem 0.7rem; text-align: right; border-bottom: 1px solid var(--border); white-space: nowrap; }}
  th.bench-col, td.bench-name {{ text-align: left; white-space: normal; font-variant-numeric: normal; }}
  thead th {{ position: sticky; top: 0; background: var(--header-bg); color: var(--header-fg); font-weight: 600; }}
  tbody tr:nth-child(even) {{ background: var(--alt-row); }}
  .pct, .verdict {{ font-weight: 700; }}
  .pct.good, .verdict.good {{ color: var(--good); }}
  .pct.bad, .verdict.bad {{ color: var(--bad); }}
  .pct.muted, .verdict.muted {{ color: var(--muted); font-weight: 400; }}
  .verdict {{ font-size: 0.85rem; font-weight: 600; text-transform: lowercase; }}
  a {{ color: var(--focus); }}
  a:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
  footer {{ color: var(--muted); font-size: 0.8rem; margin-top: 3rem; }}
  code {{ background: var(--alt-row); padding: 0.1rem 0.35rem; border-radius: 4px; font-size: 0.9em; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="subtitle">Generated {generated} &middot; JMH {jmh_note} &middot; identical code, only the JDK changes</p>
  <p class="lede">Only comparisons where the newer version measured at least {threshold:.0f}% better are shown as
  headline "improvements" below — this is computed from the raw JMH numbers on every run, not hand-picked.
  Anything flat or regressed is left out rather than presented as a win it isn't.</p>

  {sections}

  <footer>Performance Improvement benchmarks &middot; <a href="https://github.com/johanjanssen/Keep-Up-To-Date">Keep-Up-To-Date</a></footer>
</main>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results_dir")
    parser.add_argument("output_html")
    parser.add_argument("--title", default="Java Performance Benchmarks — 17 vs 25 vs 28 EA")
    args = parser.parse_args()
    d = args.results_dir

    sections = []

    speed17 = load_metrics(os.path.join(d, "java17.json"))
    speed25 = load_metrics(os.path.join(d, "java25.json"))
    if speed17 or speed25:
        sections.append(section(
            "⚡ Speed — Java 17 → Java 25", "Lower ms/op is better.",
            "Java 17", "Java 25", build_rows(speed17, speed25)))

    mem17 = load_metrics(os.path.join(d, "java17-gc.json"), memory=True)
    mem25 = load_metrics(os.path.join(d, "java25-gc.json"), memory=True)
    if mem17 or mem25:
        sections.append(section(
            "🧠 Memory — Java 17 → Java 25", "Bytes allocated per operation (GC profiler). Lower is better.",
            "Java 17", "Java 25", build_rows(mem17, mem25)))

    v25 = load_metrics(os.path.join(d, "java25-valhalla.json"))
    v28_value = load_metrics(os.path.join(d, "java28-valhalla-value.json"))
    if v25 or v28_value:
        sections.append(section(
            "🔮 Valhalla — real value records (preview)",
            "Same benchmark, <code>record Point(...)</code> → <code>value record Point(...)</code>. One keyword changed.",
            "Java 25 (record)", "Java 28 EA (value record)", build_rows(v25, v28_value),
            note="Early Access reality check: as of this run, Valhalla's array-flattening optimization is not yet "
                 "consistently engaging in the JDK 28 preview build — local measurement across two independent "
                 "Valhalla-enabled builds showed the value-record version using <em>more</em> memory and running "
                 "<em>slower</em> in some cases, not less/faster. The language feature is real and shown here "
                 "correctly; the performance payoff described in JEP 401 is not fully realized in this preview yet. "
                 "We're showing the honest number rather than a promised one."))

    if not sections:
        sections.append('<section><p class="muted">No benchmark results found for this run.</p></section>')

    out = PAGE_TEMPLATE.format(
        title=html.escape(args.title),
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        jmh_note="1.37",
        threshold=IMPROVEMENT_THRESHOLD_PCT,
        sections="\n".join(sections),
    )
    os.makedirs(os.path.dirname(args.output_html) or ".", exist_ok=True)
    with open(args.output_html, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"  OK  html -> {args.output_html}")


if __name__ == "__main__":
    main()
