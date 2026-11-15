"""Probe the GitHub side of every pilot repository in one GraphQL call each.

Answers the feasibility questions that decide which measures a project
supports: is the repo a mirror, are issues enabled, how many PRs were merged /
closed-unmerged / are open, how many issues, how deep is the default-branch
history and when is its first commit. Raw responses go to
data/raw/github_probe/<run>/ with a manifest; a flat table goes to
data/derived/selection/github_probe.{parquet,csv}.

Uses the gh CLI for authentication so no token is handled here.
"""

from __future__ import annotations

import json
import subprocess
import time

import polars as pl
import yaml

from .. import paths
from .harvest import Recorder

QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    nameWithOwner createdAt pushedAt isMirror isArchived isFork hasIssuesEnabled
    description licenseInfo { spdxId }
    mergedPRs: pullRequests(states: MERGED) { totalCount }
    closedPRs: pullRequests(states: CLOSED) { totalCount }
    openPRs: pullRequests(states: OPEN) { totalCount }
    openIssues: issues(states: OPEN) { totalCount }
    closedIssues: issues(states: CLOSED) { totalCount }
    defaultBranchRef { name target { ... on Commit { oid history { totalCount } } } }
  }
  rateLimit { remaining resetAt }
}
"""

FIRST = """
query($owner: String!, $name: String!, $after: String!) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef { target { ... on Commit {
      history(first: 1, after: $after) { nodes { oid committedDate authoredDate } }
    } } }
  }
}
"""


def gql(query: str, **variables) -> dict:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += ["-F", f"{k}={v}"]
    for attempt in range(4):
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode == 0:
            return json.loads(r.stdout)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(r.stderr)


def main():
    pilot = yaml.safe_load((paths.config_dir() / "selection" / "pilot.yaml").read_text())
    repos = [(x["id"], slug) for xs in pilot.values() for x in xs for slug in x.get("repos", [])]
    rec = Recorder("github_probe")
    rows = []
    for pid, slug in repos:
        owner, name = slug.split("/")
        data = gql(QUERY, owner=owner, name=name)
        repo = data["data"]["repository"]
        target = (repo.get("defaultBranchRef") or {}).get("target") or {}
        total = (target.get("history") or {}).get("totalCount") or 0
        first = None
        if total >= 2:
            # Cursor trick: history cursors are "<head oid> <offset>", so the
            # last commit sits right after offset total-2.
            f = gql(FIRST, owner=owner, name=name, after=f"{target['oid']} {total - 2}")
            nodes = f["data"]["repository"]["defaultBranchRef"]["target"]["history"]["nodes"]
            first = nodes[0] if nodes else None
            data["first_commit"] = first
        rec.save(f"{owner}__{name}.json", f"graphql:{slug}", json.dumps(data).encode(), project=pid, repo=slug)
        rows.append({
            "id": pid, "repo": slug,
            "created_at": repo["createdAt"], "pushed_at": repo["pushedAt"],
            "is_mirror": repo["isMirror"], "archived": repo["isArchived"],
            "issues_enabled": repo["hasIssuesEnabled"],
            "license": (repo.get("licenseInfo") or {}).get("spdxId"),
            "description": repo.get("description"),
            "merged_prs": repo["mergedPRs"]["totalCount"],
            "closed_unmerged_prs": repo["closedPRs"]["totalCount"],
            "open_prs": repo["openPRs"]["totalCount"],
            "open_issues": repo["openIssues"]["totalCount"],
            "closed_issues": repo["closedIssues"]["totalCount"],
            "default_branch": (repo.get("defaultBranchRef") or {}).get("name"),
            "default_branch_commits": total,
            "first_commit_authored": (first or {}).get("authoredDate"),
            "first_commit_committed": (first or {}).get("committedDate"),
        })
        print(f"  {slug}: {total:,} commits, {rows[-1]['merged_prs']:,} merged PRs, "
              f"{rows[-1]['closed_issues'] + rows[-1]['open_issues']:,} issues")
    rec.close()
    df = pl.DataFrame(rows)
    df.write_parquet(paths.derived_dir("selection", "github_probe.parquet"))
    df.write_csv(paths.published_dir("selection", "github_probe.csv"))


if __name__ == "__main__":
    main()
