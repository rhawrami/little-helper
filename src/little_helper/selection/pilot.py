"""Assemble the pilot sample table from the selection, signals, probe and verification.

Inputs:
  config/selection/pilot.yaml                     the 50 projects, basis and reasons
  $LH_DATA_DIR/derived/selection/candidate_signals significance channels per project
  $LH_DATA_DIR/derived/selection/github_probe      GitHub-side counts per repo
  config/selection/verification/*.yaml            verified hosting / review / issue facts

Output: data/selection/pilot_sample.csv (one row per project; small, committed).
"""

from __future__ import annotations

import polars as pl
import yaml

from .. import paths

SEL = paths.config_dir() / "selection"
DER = paths.derived_dir("selection")


def regime(v: dict, gh: dict) -> str:
    """Classify where a project's review and issue records live.

    A  GitHub-native: PRs and issues on GitHub
    B  GitHub PRs, issues elsewhere (Jira, Bugzilla, Trac)
    C  another forge or Gerrit for review (GitLab, Forgejo, Gerrit, Phabricator)
    D  mailing-list review (patches by email; patchwork/commitfest at best)
    E  no public outside-review record (closed contribution model)
    """
    rt = str(((v.get("review") or {}).get("current") or {}).get("type", "")).lower()
    it = str(((v.get("issues") or {}).get("current") or {}).get("type", "")).lower()
    # The venue named first in the verified description is the primary one
    # ("Gerrit CLs; GitHub PRs bridged in" is Gerrit, not GitHub).
    keys = {"github": "github", "gitlab": "forge", "forgejo": "forge", "gerrit": "forge",
            "phabricator": "forge", "mail": "mail", "patch": "mail", "fossil": "closed",
            "none": "closed", "not accept": "closed", "no outside": "closed"}
    hits = sorted((rt.find(k), cls) for k, cls in keys.items() if k in rt)
    if not hits:
        return "?"
    primary = hits[0][1]
    if primary == "closed":
        return "E"
    if primary == "mail":
        return "D"
    if primary == "forge":
        return "C"
    return "A" if "github" in it else "B"


def main():
    pilot = yaml.safe_load((SEL / "pilot.yaml").read_text())
    rows = [{"layer": layer, **x} for layer, xs in pilot.items() for x in xs]
    sig = pl.read_parquet(DER / "candidate_signals.parquet")
    sig_by = {r["id"]: r for r in sig.iter_rows(named=True)}
    probe = pl.read_parquet(DER / "github_probe.parquet")
    agg = probe.group_by("id").agg(
        pl.col("repo").str.join(";").alias("github_repos"),
        pl.col("default_branch_commits").sum(),
        pl.col("merged_prs").sum(), pl.col("closed_unmerged_prs").sum(), pl.col("open_prs").sum(),
        (pl.col("open_issues") + pl.col("closed_issues")).sum().alias("github_issues"),
        pl.col("issues_enabled").any().alias("github_issues_enabled"),
        pl.col("first_commit_authored").min().alias("first_commit_github"),
    )
    probe_by = {r["id"]: r for r in agg.iter_rows(named=True)}
    ver = {}
    for f in sorted((SEL / "verification").glob("*.yaml")):
        for v in yaml.safe_load(f.read_text()) or []:
            ver[v["id"]] = v

    out = []
    for r in rows:
        s, g, v = sig_by[r["id"]], probe_by.get(r["id"], {}), ver.get(r["id"], {})
        merged, closed = g.get("merged_prs") or 0, g.get("closed_unmerged_prs") or 0
        rev = (v.get("review") or {}).get("current") or {}
        iss = (v.get("issues") or {}).get("current") or {}
        out.append({
            "layer": r["layer"], "id": r["id"], "name": s["name"], "basis": r["basis"],
            "t1_channels": s["t1_channels"], "t2_channels": s["t2_channels"],
            "passed_gate_pre_chatgpt_debian": s["distro_dependents_tier_pre"] >= 1,
            "canonical_repo": (v.get("canonical_repo") or {}).get("url"),
            "vcs": (v.get("canonical_repo") or {}).get("vcs"),
            "github_role": (v.get("github") or {}).get("role"),
            "history_start": (v.get("history_start") or {}).get("date"),
            "review_venue": rev.get("type"), "review_url": rev.get("url"),
            "issue_tracker": iss.get("type"), "issue_url": iss.get("url"),
            "data_regime": regime(v, g) if v else None,
            "license": (v.get("license") or {}).get("spdx"),
            "governance": v.get("governance"),
            "ai_policy": (v.get("ai_policy") or {}).get("status"),
            "ai_policy_date": (v.get("ai_policy") or {}).get("date"),
            "github_repos": g.get("github_repos"),
            "default_branch_commits": g.get("default_branch_commits"),
            "github_merged_prs": merged, "github_closed_unmerged_prs": closed,
            "github_open_prs": g.get("open_prs"),
            # Share of closed PRs that GitHub marks merged. Low values mean either
            # many rejections or (more often here) changes landed outside the merge button.
            "github_merged_share": round(merged / (merged + closed), 3) if merged + closed else None,
            "github_issues": g.get("github_issues"),
            "verification_confidence": v.get("confidence"),
            "why": r["why"],
        })
    def flat(x):
        if isinstance(x, (list, tuple)):
            return "; ".join(str(i) for i in x)
        if x is None or isinstance(x, (bool, int, float)):
            return x
        return str(x)  # dates parsed by YAML, strings

    out = [{k: flat(v) for k, v in r.items()} for r in out]
    df = pl.DataFrame(out, infer_schema_length=None)
    df.write_csv(paths.published_dir("selection", "pilot_sample.csv"))
    print(df.select("layer", "id", "basis", "data_regime", "review_venue", "issue_tracker", "github_merged_share"))
    missing = [r["id"] for r in rows if r["id"] not in ver]
    if missing:
        print("no verification yet:", missing)


if __name__ == "__main__":
    main()
