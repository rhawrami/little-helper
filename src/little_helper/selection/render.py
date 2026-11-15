"""Render data/selection/pilot_sample.csv as the markdown table in docs/sample_selection.md.

Replaces everything between the markers
<!-- pilot-table:start --> and <!-- pilot-table:end -->.
"""

from __future__ import annotations

import re
import polars as pl

from .. import paths

DOC = paths.REPO / "docs" / "sample_selection.md"
CH = {"packages": "pkg", "containers": "ctr", "distro_graph": "dgraph", "distro_installs": "dinst",
      "distro_packaging": "dpack", "managed": "mgd"}
LAYERS = {"kernel_os": "Kernel & OS base", "toolchain": "Toolchains & build", "runtime": "Runtimes",
          "core_libs": "Core libraries", "security_net": "Security & networking", "data_stores": "Data stores",
          "servers_infra": "Servers & infrastructure", "media_graphics": "Media & graphics",
          "scientific": "Scientific computing", "ml": "ML frameworks", "app_frameworks": "Application frameworks"}


def short(s: str | None, table: list[tuple[str, str]]) -> str:
    s = (s or "").lower()
    hits = sorted((s.find(k), v) for k, v in table if k in s)
    return hits[0][1] if hits else "?"


REVIEW = [("github", "GitHub PR"), ("gitlab", "GitLab MR"), ("gerrit", "Gerrit"), ("forgejo", "Forgejo PR"),
          ("mail", "mailing list"), ("none", "none (closed)")]
ISSUES = [("jira", "Jira"), ("jbs", "Jira"), ("bugzilla", "Bugzilla"), ("trac", "Trac"), ("gitlab", "GitLab"),
          ("forgejo", "Forgejo"), ("github", "GitHub"), ("forum", "forum"), ("mail", "mailing list")]


def channels(t1, t2) -> str:
    def m(x):
        return ", ".join(CH[c] for c in x.split(",")) if x else ""
    a, b = m(t1), m(t2)
    return f"**{a}**" + (f" / {b}" if b else "") if a else (b or "—")


def main():
    d = pl.read_csv(paths.published_dir("selection", "pilot_sample.csv"))
    lines = [
        "| Layer | Project | Basis | Gate evidence: **T1** / T2 | Regime | Review / issues | GitHub merged share | AI policy (first adopted) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in d.iter_rows(named=True):
        share = r["github_merged_share"]
        share_s = "—" if share is None else (f"{share:.2f} †" if share < 0.3 else f"{share:.2f}")
        pol = r["ai_policy"] or "?"
        pol = "none found" if pol == "none_found" else f"{pol} ({str(r['ai_policy_date'])[:10]})"
        pre = "" if r["passed_gate_pre_chatgpt_debian"] else " ◦"
        lines.append(
            f"| {LAYERS[r['layer']]} | {r['name']}{pre} | {r['basis'].replace('_', ' ')} | "
            f"{channels(r['t1_channels'], r['t2_channels'])} | {r['data_regime']} | "
            f"{short(r['review_venue'], REVIEW)} / {short(r['issue_tracker'], ISSUES)} | {share_s} | {pol} |"
        )
    lines += [
        "",
        "Channels: pkg = language package graphs, ctr = containers, dgraph = Debian dependency graph, "
        "dinst = Debian installs, dpack = packaging across OS families, mgd = hyperscaler managed services. "
        "Regimes A–E as in section 8.5. "
        "† = under 30% of closed GitHub PRs are marked merged; accepted changes must be reconstructed from commits (section 8.4). "
        "◦ = did not pass the Debian dependency-graph tier in the 2022-11-29 snapshot. "
        "This mostly marks language libraries and cloud platforms that Debian barely packages, not post-2022 risers. "
        "AI-policy dates are the first formal policy text; several projects have tightened theirs since "
        "(see `config/selection/verification/`).",
    ]
    table = "\n".join(lines)
    text = DOC.read_text()
    text = re.sub(r"<!-- pilot-table:start -->.*<!-- pilot-table:end -->",
                  f"<!-- pilot-table:start -->\n{table}\n<!-- pilot-table:end -->", text, flags=re.S)
    DOC.write_text(text)
    print(table)


if __name__ == "__main__":
    main()
