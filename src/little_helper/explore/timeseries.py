"""Quarterly activity charts for one project, as a standalone HTML page.

    uv run lh plot xz          -> data/plots/xz-timeseries.html (in the repo, gitignored)

Reads the canonical tables (run `lh normalize git|github <project>` first). Every chart
counts per calendar quarter in UTC:

1. Commits on the default branch, dated by committer time, with the two most frequent
   authors shown separately.
2. Pull requests by the quarter they were opened, split by outcome. "Landed via commit"
   means GitHub closed the PR because a commit referencing it reached the default
   branch: accepted, but not through the merge button (merged != accepted).
3. Issues opened.
4. Distinct people active: commit authors (by name), PR and issue authors (by login),
   bots excluded.

The page draws with plotly.js from a CDN and follows the viewer's light/dark setting.
It shows author names, so it is for local exploration only; published outputs use
hashed identities.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import polars as pl

from .. import config, paths
from ..normalize import read_table

# Dated events worth marking on a project's charts.
NOTES: dict[str, list[tuple[str, str]]] = {
    "xz": [("2024-03-29", "Backdoor disclosed")],
}

PR_OUTCOMES = ["Merged", "Landed via commit", "Closed without landing", "Still open"]


def _q(col: str) -> pl.Expr:
    return pl.col(col).dt.convert_time_zone("UTC").dt.truncate("1q").dt.date().alias("q")


def _label(d: date) -> str:
    return f"{d.year} Q{(d.month - 1) // 3 + 1}"


def _quarters(first: date, last: date) -> list[date]:
    return pl.date_range(first, last, "1q", eager=True).to_list()


def _counts(df: pl.DataFrame, quarters: list[date], by: str, names: list[str]) -> list[dict]:
    got = {(r[by], r["q"]): r["n"] for r in df.group_by(by, "q").agg(pl.len().alias("n")).iter_rows(named=True)}
    out = [{"name": n, "values": [got.get((n, q), 0) for q in quarters]} for n in names]
    return [s for s in out if any(s["values"])]


def _distinct(df: pl.DataFrame, quarters: list[date], key: str, name: str) -> dict:
    got = dict(df.group_by("q").agg(pl.col(key).n_unique()).iter_rows())
    return {"name": name, "values": [got.get(q, 0) for q in quarters]}


def _chart(cid: str, kind: str, title: str, subtitle: str, quarters: list[date], series: list[dict],
           notes: list[tuple[str, str]]) -> dict:
    for i, s in enumerate(series):
        s["slot"] = i + 1  # fixed categorical order: slot follows the series' position, never its rank
    marks = []
    for day, text in notes:
        d = date.fromisoformat(day)
        q = date(d.year, 3 * ((d.month - 1) // 3) + 1, 1)
        if q in quarters:
            nxt = date(q.year + (q.month == 10), (q.month + 2) % 12 + 1, 1)
            frac = (d - q).days / (nxt - q).days
            marks.append({"x": quarters.index(q) - 0.5 + frac, "label": f"{text}, {d:%-d %b %Y}"})
    return {"id": cid, "kind": kind, "title": title, "subtitle": subtitle,
            "labels": [_label(q) for q in quarters], "series": series, "notes": marks}


def build(pid: str) -> dict:
    project = config.select([pid], None, False)[0]
    notes = NOTES.get(pid, [])
    commits = read_table("commits", pid)
    if commits.is_empty():
        raise SystemExit(f"no canonical commits for {pid}: run `lh normalize git {pid}` first")
    commits = commits.filter(pl.col("on_default")).with_columns(_q("committer_time"))
    prs = read_table("change_proposals", pid)
    issues = read_table("issues", pid)
    events = read_table("cp_events", pid)

    stamps = [commits["committer_time"].max()] + [t["retrieved_at"].max() for t in (prs, issues) if not t.is_empty()]
    cutoff = max(stamps).astimezone(timezone.utc)
    last_q = date(cutoff.year, 3 * ((cutoff.month - 1) // 3) + 1, 1)
    all_q = _quarters(commits["q"].min(), last_q)

    top = (commits.group_by("author_name").len().sort(["len", "author_name"], descending=[True, False])
           .head(2)["author_name"].to_list())
    commits = commits.with_columns(pl.when(pl.col("author_name").is_in(top)).then(pl.col("author_name"))
                                   .otherwise(pl.lit("Everyone else")).alias("who"))
    charts = [_chart("commits", "bar", "Commits per quarter",
                     "Default branch, dated by committer time. The two most frequent authors are shown "
                     "separately.", all_q, _counts(commits, all_q, "who", top + ["Everyone else"]), notes)]

    gh_first = min((t["created_at"].min() for t in (prs, issues) if not t.is_empty()), default=None)
    gh_q = None
    if gh_first is not None:
        gh_first = gh_first.astimezone(timezone.utc)
        gh_q = _quarters(date(gh_first.year, 3 * ((gh_first.month - 1) // 3) + 1, 1), last_q)
    if not prs.is_empty():
        landed = set()
        if not events.is_empty():
            last_close = (events.filter(pl.col("type") == "ClosedEvent").sort("created_at")
                          .group_by("parent_id").last())
            landed = set(last_close.filter(pl.col("closer_type") == "Commit")["parent_id"])
        prs = prs.with_columns(
            _q("created_at"),
            pl.when(pl.col("state") == "MERGED").then(pl.lit("Merged"))
            .when(pl.col("state") == "OPEN").then(pl.lit("Still open"))
            .when(pl.col("id").is_in(list(landed))).then(pl.lit("Landed via commit"))
            .otherwise(pl.lit("Closed without landing")).alias("outcome"))
        charts.append(_chart(
            "prs", "bar", "Pull requests opened per quarter, by outcome",
            "“Landed via commit”: GitHub closed the PR because a commit referencing it reached the "
            "default branch, so it was accepted without the merge button.",
            gh_q, _counts(prs, gh_q, "outcome", PR_OUTCOMES), notes))
    if not issues.is_empty():
        issues = issues.with_columns(_q("created_at"), pl.lit("Issues opened").alias("kind"))
        charts.append(_chart("issues", "bar", "Issues opened per quarter", "Every issue, open or closed.",
                             gh_q, _counts(issues, gh_q, "kind", ["Issues opened"]), notes))

    # Over the GitHub era only, so the three lines share a range; the commits chart covers the rest.
    people_q = gh_q or all_q
    humans = commits.filter(~pl.col("author_is_bot")).with_columns(pl.col("author_name").str.to_lowercase())
    people = [_distinct(humans, people_q, "author_name", "Commit authors")]
    if not prs.is_empty():
        people.append(_distinct(prs.filter(~pl.col("author_is_bot")), people_q, "author", "PR authors"))
    if not issues.is_empty():
        people.append(_distinct(issues.filter(~pl.col("author_is_bot")), people_q, "author", "Issue authors"))
    charts.append(_chart("people", "line", "People active per quarter",
                         "Distinct commit authors (by name) and PR and issue authors (by GitHub login), bots "
                         "excluded, since the project's GitHub history begins.", people_q, people, notes))

    repo = next((r.github for r in project.repos if r.github), project.repos[0].key)
    return {"project": pid, "name": project.name, "repo": repo,
            "cutoff": f"{cutoff:%-d %b %Y}", "generated": paths.utcnow(), "charts": charts}


def main(pid: str, out: str | None = None) -> Path:
    data = build(pid)
    path = Path(out) if out else paths.REPO / "data" / "plots" / f"{pid}-timeseries.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__TITLE__", f"{data['name']} activity over time").replace("__DATA__", payload)
    path.write_text(html, encoding="utf-8")
    return path


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface-1: #fcfcfb;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a; --series-4: #eda100;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface-1: #1a1a19;
    --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface-1: #1a1a19;
  --text-primary: #f0efec; --text-secondary: #c3c2b7; --text-muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--text-primary);
       font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1040px; margin: 0 auto; padding: 32px 16px 48px; }
h1 { font-size: 24px; font-weight: 600; margin: 0 0 4px; }
.lede { color: var(--text-secondary); margin: 0 0 24px; max-width: 72ch; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px;
        padding: 20px 20px 12px; margin-bottom: 16px; }
.card h2 { font-size: 16px; font-weight: 600; margin: 0; }
.card p { color: var(--text-secondary); margin: 2px 0 8px; max-width: 80ch; }
.plot { height: 320px; }
details { margin-top: 4px; color: var(--text-secondary); }
summary { cursor: pointer; font-size: 13px; padding: 4px 0; }
.table-wrap { max-height: 320px; overflow: auto; margin-top: 8px; }
table { border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
th, td { padding: 4px 12px 4px 0; text-align: right; border-bottom: 1px solid var(--grid); white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--text-primary); font-weight: 600; position: sticky; top: 0; background: var(--surface-1); }
footer { color: var(--text-muted); font-size: 12px; margin-top: 24px; }
code { font-size: 12px; }
</style>
</head>
<body>
<main>
  <h1 id="title"></h1>
  <p class="lede" id="lede"></p>
  <div id="charts"></div>
  <footer id="foot"></footer>
</main>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
<script>
const DATA = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const fmt = v => v == null ? "\\u2013" : v.toLocaleString("en-US");

document.title = `${DATA.name} activity over time`;
document.getElementById("title").textContent = document.title;
document.getElementById("lede").textContent =
  `${DATA.repo}: git history plus GitHub pull requests and issues, counted per calendar quarter (UTC). ` +
  `Data through ${DATA.cutoff}, so the last quarter is partial.`;
document.getElementById("foot").innerHTML =
  `Generated by <code>lh plot ${esc(DATA.project)}</code> at ${esc(DATA.generated)} from the canonical tables. ` +
  `Author names are shown for local exploration only.`;

const root = document.getElementById("charts");
for (const ch of DATA.charts) {
  const card = document.createElement("section");
  card.className = "card";
  const head = `<tr><th>Quarter</th>${ch.series.map(s => `<th>${esc(s.name)}</th>`).join("")}</tr>`;
  const rows = ch.labels.map((l, i) =>
    `<tr><td>${l}</td>${ch.series.map(s => `<td>${fmt(s.values[i])}</td>`).join("")}</tr>`).join("");
  card.innerHTML = `<h2>${esc(ch.title)}</h2><p>${esc(ch.subtitle)}</p><div class="plot" id="${ch.id}"></div>` +
    `<details><summary>Show the numbers</summary><div class="table-wrap"><table><thead>${head}</thead>` +
    `<tbody>${rows}</tbody></table></div></details>`;
  root.appendChild(card);
}

// Year labels centred under each year's four quarters. Ticks sit between categories on
// purpose: a tick on a category would also replace that quarter's name in the hover header.
function ticks(labels, width) {
  const q1 = labels.flatMap((l, i) => l.endsWith("Q1") ? [i] : []);
  const need = Math.ceil(q1.length * 44 / Math.max(width - 70, 120));
  const step = [1, 2, 5, 10].find(s => s >= need) || 10;
  const keep = q1.filter(i => +labels[i].slice(0, 4) % step === 0);
  return {tickvals: keep.map(i => i + 1.5), ticktext: keep.map(i => labels[i].slice(0, 4))};
}

function render(ch) {
  const el = document.getElementById(ch.id);
  const surface = css("--surface-1"), muted = css("--text-muted"), sec = css("--text-secondary");
  const traces = ch.series.map(s => {
    const color = css(`--series-${s.slot}`);
    const t = {x: ch.labels, y: s.values, name: s.name, hovertemplate: `${esc(s.name)}: %{y:,}<extra></extra>`};
    return ch.kind === "bar"
      ? {...t, type: "bar", marker: {color, line: {color: surface, width: 1}}}
      : {...t, type: "scatter", mode: "lines", line: {color, width: 2}, connectgaps: false};
  });
  const ymax = Math.max(1, ...ch.labels.map((_, i) => ch.kind === "bar"
    ? ch.series.reduce((a, s) => a + (s.values[i] || 0), 0)
    : Math.max(0, ...ch.series.map(s => s.values[i] || 0))));
  const many = ch.series.length > 1;
  const layout = {
    barmode: "stack", barcornerradius: 4, bargap: 0.25,
    paper_bgcolor: surface, plot_bgcolor: surface,
    font: {family: 'system-ui, -apple-system, "Segoe UI", sans-serif', size: 12, color: sec},
    margin: {l: 44, r: 8, t: many ? 32 : 8, b: 28},
    showlegend: many,
    legend: {orientation: "h", x: 0, xanchor: "left", y: 1.0, yanchor: "bottom", font: {color: sec},
             traceorder: "normal"},
    hovermode: "x unified",
    hoverlabel: {bgcolor: surface, bordercolor: css("--axis"), font: {color: css("--text-primary")}},
    xaxis: {type: "category", ...ticks(ch.labels, el.clientWidth), tickfont: {color: muted}, linecolor: css("--axis"),
            showgrid: false, ticks: "", fixedrange: true},
    yaxis: {range: [0, ymax * (ch.notes.length ? 1.18 : 1.06)], gridcolor: css("--grid"), gridwidth: 1,
            zeroline: false, tickfont: {color: muted}, tickformat: ymax >= 10000 ? "~s" : ",d", fixedrange: true},
    shapes: ch.notes.map(n => ({type: "line", xref: "x", x0: n.x, x1: n.x, yref: "paper", y0: 0, y1: 1,
                                line: {color: muted, width: 1}})),
    annotations: ch.notes.map(n => ({xref: "x", x: n.x, yref: "paper", y: 1, xanchor: "right", yanchor: "top",
                                     xshift: -4, text: esc(n.label), showarrow: false, font: {size: 11, color: sec}})),
  };
  Plotly.react(el, traces, layout, {displayModeBar: false, responsive: true});
}

const renderAll = () => DATA.charts.forEach(render);
renderAll();
let timer;
addEventListener("resize", () => { clearTimeout(timer); timer = setTimeout(renderAll, 150); });
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderAll);
</script>
</body>
</html>
"""
