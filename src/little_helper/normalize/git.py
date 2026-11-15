"""Git extracts -> canonical commits, commit_files, trailers, refs, trees, policy_files, ai_markers.

Uses the latest successful extract of each repository. Classification flags come from
classify.paths with the project's overrides; they are first-pass rules.
"""

from __future__ import annotations

import json

import polars as pl

from .. import config
from ..classify import ai_markers, bots, trailers
from ..classify import paths as path_rules
from ..collect.git import successful_runs
from . import ts, tz_minutes, write_partition

_MARKER_PREFILTER = "|".join(f"(?:{rx})" for mid, _t, fld, rx in ai_markers.RULES if fld == "message")


def _read(run, pattern: str) -> pl.DataFrame:
    files = sorted(run.glob(pattern))
    return pl.read_parquet(files) if files else pl.DataFrame()


def normalize_project(project: config.Project) -> dict:
    tables: dict[str, list[pl.DataFrame]] = {t: [] for t in
                                             ("commits", "commit_files", "trailers", "refs", "trees", "policy_files",
                                              "ai_markers")}
    used = []
    for repo in project.repos:
        runs = successful_runs(repo.key)
        if not runs:
            continue
        run = runs[-1]
        meta = json.loads((run / "meta.json").read_text())
        used.append({"repo": repo.key, "run_id": meta["run_id"], "commits": meta["commits"]})
        lit = [pl.lit(repo.key).alias("repo"), pl.lit(meta["run_id"]).alias("git_run")]

        c = _read(run, "commits-*.parquet")
        if c.height:
            c = c.with_columns(
                *lit,
                pl.col("parents").list.len().alias("n_parents"),
                ts("author_date").alias("author_time"), tz_minutes("author_date").alias("author_tz"),
                ts("committer_date").alias("committer_time"), tz_minutes("committer_date").alias("committer_tz"),
                pl.col("message").str.split("\n").list.first().alias("subject"),
                pl.col("message").str.len_chars().alias("message_len"),
                (pl.col("author_email").str.contains(bots.EMAIL_PATTERN).fill_null(False)
                 | pl.col("author_name").str.contains(bots.NAME_PATTERN).fill_null(False)).alias("author_is_bot"),
            ).with_columns((pl.col("n_parents") > 1).alias("is_merge")).drop("author_date", "committer_date")
            tables["commits"].append(c)

            msgs = c.select("sha", "message")
            t_rows = [{"sha": sha, "key": k, "value": v}
                      for sha, m in msgs.iter_rows() for k, v in trailers.parse(m)]
            if t_rows:
                tables["trailers"].append(pl.DataFrame(t_rows).with_columns(*lit))

            cand = msgs.filter(pl.col("message").str.contains(_MARKER_PREFILTER))
            m_rows = [{"object": "commit", "id": sha, **hit}
                      for sha, m in cand.iter_rows() for hit in ai_markers.find("message", m)]
            if m_rows:
                tables["ai_markers"].append(pl.DataFrame(m_rows).with_columns(*lit))

        f = _read(run, "files-*.parquet")
        if f.height:
            f = path_rules.add_flags(f, overrides=project.paths).with_columns(
                *lit, pl.col("added").is_null().alias("is_binary"))
            tables["commit_files"].append(f)

        r = _read(run, "refs.parquet")
        if r.height:
            r = r.with_columns(
                *lit,
                pl.when(pl.col("ref").str.starts_with("refs/tags/")).then(pl.lit("tag"))
                .when(pl.col("ref").str.starts_with("refs/heads/")).then(pl.lit("branch"))
                .otherwise(pl.lit("other")).alias("kind"),
                pl.col("ref").str.replace(r"^refs/(tags|heads)/", "").alias("name"),
                pl.coalesce("peeled", "object").alias("target"),
                (pl.col("object_type") == "tag").alias("annotated"),
                ts("date").alias("time"),
            )
            tables["refs"].append(r)

        tr = _read(run, "trees.parquet")
        if tr.height:
            tables["trees"].append(path_rules.add_flags(tr, overrides=project.paths).with_columns(*lit))

        pf = _read(run, "policy_files.parquet")
        if pf.height and c.height:
            pf = pf.join(c.select("sha", "author_time", "committer_time", "on_default"), on="sha", how="left")
            tables["policy_files"].append(pf.with_columns(*lit))

    counts = {}
    for name, frames in tables.items():
        df = pl.concat(frames, how="diagonal_relaxed") if frames else None
        counts[name] = write_partition(name, project.id, df)
    return {"project": project.id, "repos": used, **counts}


def run(projects: list[config.Project], log=print) -> list[dict]:
    out = []
    for p in projects:
        res = normalize_project(p)
        if res["repos"]:
            log(f"[normalize git] {p.id}: {res['commits']:,} commits, {res['commit_files']:,} file rows, "
                f"{res['trailers']:,} trailers, {res['ai_markers']:,} AI markers, {res['policy_files']} policy versions")
        else:
            log(f"[normalize git] {p.id}: no git extract yet")
        out.append(res)
    return out

