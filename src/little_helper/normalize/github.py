"""GitHub raw pages -> canonical change-proposal and issue tables.

Every committed chunk of every run is read in run order. Each item (PR or issue)
keeps its most recent version; its nested rows (reviews, comments, commits, files,
events, labels) come from the same run as that version, i.e. the main page plus
that run's overflow pages, deduplicated by row identity.

Long text (PR, issue, review and comment bodies) stays in raw; canonical tables keep
lengths, titles and AI markers found in the text. Logins are kept here (local data);
published outputs must use salted hashes.

Tables (partitioned by project):
  change_proposals  cp_reviews  cp_comments  cp_commits  cp_files  cp_events  cp_labels
  issues            issue_comments  issue_events  issue_labels
  gh_ai_markers     gh_repo_facts
"""

from __future__ import annotations

from collections import defaultdict

import polars as pl

from .. import config, objects, paths, store
from ..classify import ai_markers, bots
from ..classify import paths as path_rules
from ..collect.github import CONNECTIONS, SOURCE
from . import ts, write_partition


def _login(x: dict | None) -> tuple[str | None, str | None]:
    x = x or {}
    return x.get("login"), x.get("__typename")


def _event_row(parent: str, e: dict) -> dict:
    src = e.get("source") or e.get("subject") or e.get("canonical") or {}
    closer = e.get("closer") or {}
    req = e.get("requestedReviewer") or {}
    return {
        "id": e.get("id"), "parent_id": parent, "type": e.get("__typename"), "created_at": e.get("createdAt"),
        "actor": (e.get("actor") or {}).get("login"),
        "commit_oid": (e.get("commit") or {}).get("oid"),
        "before_oid": (e.get("beforeCommit") or {}).get("oid"), "after_oid": (e.get("afterCommit") or {}).get("oid"),
        "label": (e.get("label") or {}).get("name"),
        "requested_reviewer": req.get("login") or req.get("slug"), "requested_reviewer_type": req.get("__typename"),
        "ref_type": src.get("__typename"), "ref_number": src.get("number"),
        "ref_repo": (src.get("repository") or {}).get("nameWithOwner")
        or (e.get("fromRepository") or {}).get("nameWithOwner"),
        "will_close": e.get("willCloseTarget"), "state_reason": e.get("stateReason"),
        "closer_type": closer.get("__typename"), "closer_oid": closer.get("oid"), "closer_number": closer.get("number"),
    }


class _Acc:
    """Accumulates flat rows tagged with (parent id, run) so versions can be chosen later."""

    def __init__(self):
        self.rows: dict[str, list[dict]] = defaultdict(list)

    def add(self, table: str, row: dict):
        self.rows[table].append(row)

    def frame(self, table: str) -> pl.DataFrame:
        rows = self.rows.get(table) or []
        return pl.DataFrame(rows, infer_schema_length=None) if rows else pl.DataFrame()


def _children(acc: _Acc, kind: str, parent: str, alias: str, nodes: list[dict], tag: dict):
    prefix = "cp" if kind == "prs" else "issue"
    for n in nodes or []:
        if alias == "reviews":
            who, typ = _login(n.get("author"))
            acc.add("cp_reviews", {**tag, "parent_id": parent, "id": n.get("id"), "state": n.get("state"),
                                   "submitted_at": n.get("submittedAt"), "author": who, "author_type": typ,
                                   "association": n.get("authorAssociation"),
                                   "commit_oid": (n.get("commit") or {}).get("oid"),
                                   "body_len": len(n.get("body") or "")})
            for hit in ai_markers.find("login", who):
                acc.add("gh_ai_markers", {**tag, "object": "review_author", "id": n.get("id"), "parent_id": parent, **hit})
        elif alias == "comments":
            who, typ = _login(n.get("author"))
            acc.add(f"{prefix}_comments", {**tag, "parent_id": parent, "id": n.get("id"),
                                           "created_at": n.get("createdAt"), "author": who, "author_type": typ,
                                           "association": n.get("authorAssociation"),
                                           "body_len": len(n.get("body") or "")})
            for hit in ai_markers.find("login", who):
                acc.add("gh_ai_markers", {**tag, "object": "comment_author", "id": n.get("id"), "parent_id": parent, **hit})
        elif alias == "commits":
            c = n.get("commit") or {}
            acc.add("cp_commits", {**tag, "parent_id": parent, "oid": c.get("oid"),
                                   "authored_date": c.get("authoredDate"), "committed_date": c.get("committedDate")})
        elif alias == "files":
            acc.add("cp_files", {**tag, "parent_id": parent, "path": n.get("path"), "additions": n.get("additions"),
                                 "deletions": n.get("deletions"), "change_type": n.get("changeType")})
        elif alias == "labels":
            acc.add(f"{prefix}_labels", {**tag, "parent_id": parent, "label": n.get("name")})
        elif alias == "timeline":
            acc.add(f"{prefix}_events", {**tag, **_event_row(parent, n)})


def _pr_row(n: dict, tag: dict) -> dict:
    who, typ = _login(n.get("author"))
    merger, _ = _login(n.get("mergedBy"))
    return {**tag, "id": n["id"], "number": n["number"], "title": n.get("title"), "body_len": len(n.get("body") or ""),
            "state": n.get("state"), "is_draft": n.get("isDraft"), "locked": n.get("locked"),
            "created_at": n.get("createdAt"), "updated_at": n.get("updatedAt"), "closed_at": n.get("closedAt"),
            "merged_at": n.get("mergedAt"), "author": who, "author_type": typ, "association": n.get("authorAssociation"),
            "author_is_bot": bots.is_bot_login(who, typ), "merged_by": merger,
            "merge_commit": (n.get("mergeCommit") or {}).get("oid"), "base_ref": n.get("baseRefName"),
            "head_ref": n.get("headRefName"), "head_oid": n.get("headRefOid"),
            "is_cross_repo": n.get("isCrossRepository"), "head_owner": (n.get("headRepositoryOwner") or {}).get("login"),
            "additions": n.get("additions"), "deletions": n.get("deletions"), "changed_files": n.get("changedFiles"),
            "review_decision": n.get("reviewDecision"),
            "n_review_threads": (n.get("reviewThreads") or {}).get("totalCount"),
            **{f"n_{a}": (n.get(a) or {}).get("totalCount") for a in ("labels", "reviews", "comments", "commits", "files")},
            "n_timeline_all": (n.get("timeline") or {}).get("totalCount")}


def _issue_row(n: dict, tag: dict) -> dict:
    who, typ = _login(n.get("author"))
    return {**tag, "id": n["id"], "number": n["number"], "title": n.get("title"), "body_len": len(n.get("body") or ""),
            "state": n.get("state"), "state_reason": n.get("stateReason"), "locked": n.get("locked"),
            "created_at": n.get("createdAt"), "updated_at": n.get("updatedAt"), "closed_at": n.get("closedAt"),
            "author": who, "author_type": typ, "association": n.get("authorAssociation"),
            "author_is_bot": bots.is_bot_login(who, typ),
            "n_comments": (n.get("comments") or {}).get("totalCount"),
            "n_labels": (n.get("labels") or {}).get("totalCount")}


def _ingest(acc: _Acc, rec: dict, run: str):
    kind = rec["kind"]
    tag = {"run": run, "retrieved_at": rec.get("retrieved_at")}
    data = (rec.get("response") or {}).get("data") or {}
    if kind == "repo":
        r = data.get("repository") or {}
        acc.add("gh_repo_facts", {**tag, "repo": r.get("nameWithOwner"), "created_at": r.get("createdAt"),
                                  "is_mirror": r.get("isMirror"), "is_archived": r.get("isArchived"),
                                  "has_issues": r.get("hasIssuesEnabled"), "disk_kb": r.get("diskUsage"),
                                  "default_branch": (r.get("defaultBranchRef") or {}).get("name"),
                                  **{k: (r.get(k) or {}).get("totalCount") for k in
                                     ("pullRequests", "openPRs", "mergedPRs", "closedPRs", "issues", "openIssues")}})
        return
    if kind in ("prs", "issues"):
        for n in ((data.get("repository") or {}).get("page") or {}).get("nodes") or []:
            if kind == "prs":
                acc.add("change_proposals", _pr_row(n, tag))
                for hit in ai_markers.find("message", n.get("body")):
                    acc.add("gh_ai_markers", {**tag, "object": "pr_body", "id": n["id"], "parent_id": n["id"], **hit})
                for hit in ai_markers.find("login", _login(n.get("author"))[0]):
                    acc.add("gh_ai_markers", {**tag, "object": "pr_author", "id": n["id"], "parent_id": n["id"], **hit})
                for hit in ai_markers.find("branch", n.get("headRefName")):
                    acc.add("gh_ai_markers", {**tag, "object": "pr_branch", "id": n["id"], "parent_id": n["id"], **hit})
            else:
                acc.add("issues", _issue_row(n, tag))
                for hit in ai_markers.find("message", n.get("body")):
                    acc.add("gh_ai_markers", {**tag, "object": "issue_body", "id": n["id"], "parent_id": n["id"], **hit})
            for alias in CONNECTIONS[kind]:
                _children(acc, kind, n["id"], alias, (n.get(alias) or {}).get("nodes"), tag)
    elif kind in ("prs_overflow", "issues_overflow"):
        base = kind.removesuffix("_overflow")
        conn = ((data.get("node") or {}).get("conn") or {})
        _children(acc, base, rec["parent"], rec["connection"], conn.get("nodes"), tag)


# Row identity for deduplicating nested rows within one version.
_CHILD_KEYS = {
    "cp_reviews": ["parent_id", "id"], "cp_comments": ["parent_id", "id"], "cp_commits": ["parent_id", "oid"],
    "cp_files": ["parent_id", "path"], "cp_events": ["parent_id", "id", "type", "created_at"],
    "cp_labels": ["parent_id", "label"], "issue_comments": ["parent_id", "id"],
    "issue_events": ["parent_id", "id", "type", "created_at"], "issue_labels": ["parent_id", "label"],
    "gh_ai_markers": ["parent_id", "object", "id", "marker"],
}
_TIME_COLS = ["created_at", "updated_at", "closed_at", "merged_at", "submitted_at", "authored_date", "committed_date",
              "retrieved_at"]


def _latest(df: pl.DataFrame) -> pl.DataFrame:
    """Most recent version of each item (by retrieval time, then run)."""
    return df.sort(["retrieved_at", "run"]).unique(subset=["id"], keep="last")


def _versioned_children(child: pl.DataFrame, parents: pl.DataFrame, table: str) -> pl.DataFrame:
    if child.height == 0 or parents.height == 0:
        return child
    keep = parents.select(pl.col("id").alias("parent_id"), "run")
    out = child.join(keep, on=["parent_id", "run"], how="semi")
    keys = [k for k in _CHILD_KEYS[table] if k in out.columns]
    return out.unique(subset=keys, keep="first", maintain_order=True)


def _finish(df: pl.DataFrame, repo: str) -> pl.DataFrame:
    if df.height == 0:
        return df
    return df.with_columns(pl.lit(repo).alias("repo"),
                           *[ts(c).alias(c) for c in _TIME_COLS if c in df.columns and df[c].dtype == pl.Utf8])


def normalize_repo(project: config.Project, repo: config.Repo) -> dict[str, pl.DataFrame]:
    key = f"github.com/{repo.github}".lower()
    base = paths.raw_dir(SOURCE, key)
    acc = _Acc()
    for run_dir in objects.subdirs(base):  # local and object storage
        for chunk in objects.list_files(run_dir, "*.jsonl.zst"):
            with objects.local_copies([chunk]):  # one chunk on disk at a time
                for rec in store.iter_records(chunk):
                    _ingest(acc, rec, run_dir.name)
    out: dict[str, pl.DataFrame] = {}
    cps = _latest(acc.frame("change_proposals")) if acc.rows.get("change_proposals") else pl.DataFrame()
    iss = _latest(acc.frame("issues")) if acc.rows.get("issues") else pl.DataFrame()
    out["change_proposals"], out["issues"] = cps, iss
    for t in ("cp_reviews", "cp_comments", "cp_commits", "cp_files", "cp_events", "cp_labels"):
        out[t] = _versioned_children(acc.frame(t), cps, t)
    for t in ("issue_comments", "issue_events", "issue_labels"):
        out[t] = _versioned_children(acc.frame(t), iss, t)
    markers = acc.frame("gh_ai_markers")
    if markers.height:
        both = pl.concat([x.select("id", "run") for x in (cps, iss) if x.height]) if (cps.height or iss.height) else None
        if both is not None:
            markers = markers.join(both.rename({"id": "parent_id"}), on=["parent_id", "run"], how="semi")
        markers = markers.unique(subset=_CHILD_KEYS["gh_ai_markers"], keep="first", maintain_order=True)
    out["gh_ai_markers"] = markers
    facts = acc.frame("gh_repo_facts")
    out["gh_repo_facts"] = facts.sort("retrieved_at").tail(1) if facts.height else facts
    if out["cp_files"].height:
        out["cp_files"] = path_rules.add_flags(out["cp_files"], overrides=project.paths)
    if cps.height and out["cp_labels"].height:
        labels = out["cp_labels"].group_by("parent_id").agg(pl.col("label").alias("labels"))
        out["change_proposals"] = cps.join(labels.rename({"parent_id": "id"}), on="id", how="left")
    return {k: _finish(v, repo.github) for k, v in out.items()}


TABLES = ["change_proposals", "cp_reviews", "cp_comments", "cp_commits", "cp_files", "cp_events", "cp_labels",
          "issues", "issue_comments", "issue_events", "issue_labels", "gh_ai_markers", "gh_repo_facts"]


def normalize_project(project: config.Project) -> dict:
    frames: dict[str, list[pl.DataFrame]] = {t: [] for t in TABLES}
    for r in project.repos:
        if not r.github:
            continue
        for t, df in normalize_repo(project, r).items():
            if df.height:
                frames[t].append(df)
    counts = {t: write_partition(t, project.id, pl.concat(fs, how="diagonal_relaxed") if fs else None)
              for t, fs in frames.items()}
    return {"project": project.id, **counts}


def run(projects: list[config.Project], log=print) -> list[dict]:
    out = []
    for p in projects:
        if not (p.wants("github_prs") or p.wants("github_issues")):
            continue
        res = normalize_project(p)
        log(f"[normalize github] {p.id}: {res['change_proposals']:,} PRs ({res['cp_reviews']:,} reviews, "
            f"{res['cp_events']:,} events, {res['cp_files']:,} file rows), {res['issues']:,} issues, "
            f"{res['gh_ai_markers']:,} AI markers")
        out.append(res)
    return out
