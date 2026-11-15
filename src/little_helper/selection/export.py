"""Write config/projects/<id>.yaml for every project in the pilot.

Inputs: config/selection/pilot.yaml, config/selection/verification/*.yaml,
data/selection/pilot_sample.csv (regimes) and the GitHub probe (issues enabled).
Repository sizes (GitHub diskUsage) are fetched in two batched GraphQL queries so
the git collector can schedule big clones first and check free space.

Generated keys are overwritten on every export. Hand-maintained keys survive:
  paths         extra path-classification regexes per class (test, vendored, ...)
  policy_paths  extra AI/contribution policy files to track, e.g. a docs page
  overrides     any generated key to replace, e.g. {collect: {github_issues: false}}
"""

from __future__ import annotations

import re
from datetime import date

import polars as pl
import yaml

from .. import config, ghapi, paths

HAND_KEYS = ("paths", "policy_paths", "overrides")
_URL = re.compile(r"^(https?|git)://\S+$")


def _sizes(slugs: list[str]) -> dict[str, float]:
    api = ghapi.GraphQL()
    out = {}
    try:
        for i in range(0, len(slugs), 25):
            chunk = slugs[i:i + 25]
            parts = []
            for j, s in enumerate(chunk):
                o, n = s.split("/")
                parts.append(f'r{j}: repository(owner: "{o}", name: "{n}") {{ nameWithOwner diskUsage }}')
            body, _ = api.execute("query { " + " ".join(parts) + " rateLimit { cost remaining resetAt } }", {})
            for j, s in enumerate(chunk):
                r = (body.get("data") or {}).get(f"r{j}")
                if r and r.get("diskUsage") is not None:
                    out[s] = round(r["diskUsage"] / 1024, 1)
    finally:
        api.close()
    return out


def main(fetch_sizes: bool = True):
    sel = paths.config_dir() / "selection"
    pilot = yaml.safe_load((sel / "pilot.yaml").read_text())
    ver, ver_file = {}, {}
    for f in sorted((sel / "verification").glob("*.yaml")):
        for v in yaml.safe_load(f.read_text()) or []:
            ver[v["id"]], ver_file[v["id"]] = v, f.name
    sample = {r["id"]: r for r in pl.read_csv(paths.published_dir("selection", "pilot_sample.csv")).iter_rows(named=True)}
    probe_path = paths.derived_dir("selection", "github_probe.parquet")
    issues_on = ({r["repo"].lower(): r["issues_enabled"] for r in pl.read_parquet(probe_path).iter_rows(named=True)}
                 if probe_path.exists() else {})
    slugs = sorted({s for xs in pilot.values() for x in xs for s in x.get("repos", [])})
    sizes = _sizes(slugs) if fetch_sizes else {}

    out_dir = config.projects_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for layer, xs in pilot.items():
        for x in xs:
            pid = x["id"]
            v, s = ver.get(pid, {}), sample.get(pid, {})
            regime = s.get("data_regime")
            canon = (v.get("canonical_repo") or {})
            url = canon.get("url") if isinstance(canon.get("url"), str) else None  # lists: multi-repo projects
            canon_url = url if canon.get("vcs") == "git" and _URL.match(url or "") else None
            role = (v.get("github") or {}).get("role")
            repos = []
            for i, slug in enumerate(x.get("repos", [])):
                entry = {"github": slug, "role": role if i == 0 else "related", "size_mb": sizes.get(slug)}
                if i == 0 and canon_url and "github.com" not in canon_url and role != "canonical":
                    entry["clone_urls"] = [canon_url]  # the GitHub mirror is the fallback
                repos.append(entry)
            if not repos and canon_url:
                repos.append({"clone_urls": [canon_url], "role": "canonical"})
            any_issues = any(issues_on.get(r.get("github", "").lower()) for r in repos)
            doc = {
                "id": pid, "name": s.get("name") or pid, "layer": layer, "basis": x.get("basis"),
                "regime": regime,
                "repos": repos,
                "collect": {
                    "git": True,
                    "github_prs": regime in ("A", "B"),
                    "github_issues": regime in ("A", "B") and any_issues,
                },
                "venues": {"review": s.get("review_venue"), "issues": s.get("issue_tracker")},
                "history_start": s.get("history_start"),
                "ai_policy": {"status": s.get("ai_policy"), "date": s.get("ai_policy_date")},
                "verification": f"config/selection/verification/{ver_file[pid]}" if pid in ver_file else None,
            }
            path = out_dir / f"{pid}.yaml"
            old = yaml.safe_load(path.read_text()) if path.exists() else {}
            if not fetch_sizes:  # keep the sizes recorded by the last export that fetched them
                old_sizes = {r.get("github"): r.get("size_mb") for r in (old or {}).get("repos", [])}
                for r in doc["repos"]:
                    r["size_mb"] = r.get("size_mb") or old_sizes.get(r.get("github"))
            for k in HAND_KEYS:
                doc[k] = (old or {}).get(k) or ({} if k != "policy_paths" else [])
            for k, val in (doc.get("overrides") or {}).items():
                doc[k] = {**doc[k], **val} if isinstance(doc.get(k), dict) and isinstance(val, dict) else val
            header = (f"# Generated by `lh selection export` on {date.today().isoformat()} from config/selection/.\n"
                      f"# Edit only: {', '.join(HAND_KEYS)} (kept on regeneration). See selection/export.py.\n")
            path.write_text(header + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=110))
            written.append(pid)
    print(f"wrote {len(written)} project configs to {out_dir}")
