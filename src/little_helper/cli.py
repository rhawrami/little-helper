"""`lh`: the little-helper command line.

    uv run lh info                               where data goes, free space, token status
    uv run lh projects [--set slice]             list configured projects
    uv run lh selection rebuild                  re-run the offline selection steps
    uv run lh selection export                   regenerate config/projects/*.yaml
    uv run lh collect git curl zlib              clone -> extract -> delete
    uv run lh collect github --set slice         PRs and issues via GraphQL (resumable)
    uv run lh normalize git --set slice          raw -> canonical tables
    uv run lh status --set slice                 what has been collected
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone

from . import config, paths


def _add_selection(p: argparse.ArgumentParser):
    p.add_argument("projects", nargs="*", help="project ids (see config/projects/)")
    p.add_argument("--set", dest="set_name", help="a named set from config/study.yaml (e.g. slice)")
    p.add_argument("--all", action="store_true", help="every configured project")


def _projects(args) -> list[config.Project]:
    return config.select(args.projects, args.set_name, args.all)


def _table(rows: list[dict], cols: list[str]):
    if not rows:
        print("(nothing)")
        return
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in cols))


def cmd_info(_args):
    from . import ghapi
    from .collect.git import git_version
    for name, d in (("data (LH_DATA_DIR)", paths.data_dir()), ("work (LH_WORK_DIR)", paths.work_dir()),
                    ("manifests (LH_MANIFEST_DIR)", paths.manifest_dir())):
        print(f"{name:28} {d}  [{paths.free_bytes(d) / 1e9:,.1f} GB free]")
    print(f"{'projects configured':28} {len(config.load_projects())}")
    print(f"{'git':28} {git_version()}")
    try:
        ghapi.token()
        print(f"{'GitHub token':28} available")
    except ghapi.GitHubError as e:
        print(f"{'GitHub token':28} MISSING ({e})")


def cmd_projects(args):
    ps = config.select(args.projects, args.set_name, True if not (args.projects or args.set_name) else args.all)
    rows = [{"id": p.id, "regime": p.regime, "repos": ",".join(r.github or r.key for r in p.repos),
             "size_mb": round(sum(r.size_mb or 0 for r in p.repos)),
             "collect": ",".join(k for k, v in p.collect.items() if v)} for p in ps]
    _table(rows, ["id", "regime", "size_mb", "collect", "repos"])
    print(f"{len(rows)} projects, {sum(r['size_mb'] for r in rows) / 1024:,.1f} GB of GitHub diskUsage")


def cmd_selection(args):
    from .selection import audit, export, harvest, pilot, probe, render, score, signals
    steps = {"harvest": lambda: harvest.main(args.names), "signals": lambda: signals.main(args.names),
             "score": score.main, "probe": probe.main, "audit": audit.main, "pilot": pilot.main,
             "render": render.main, "export": lambda: export.main(fetch_sizes=not args.no_sizes)}
    if args.step == "rebuild":
        for s in ("signals", "score", "audit", "pilot", "render"):
            print(f"== {s}")
            steps[s]()
    else:
        steps[args.step]()


def _run_logger(source: str):
    """Print with a UTC timestamp and append the same line to <data>/logs/<source>-<time>.log."""
    path = paths.data_dir() / "logs" / f"{source}-{paths.new_run_id()}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"logging to {path}", flush=True)

    def log(msg: str):
        line = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}Z {msg}"
        print(line, flush=True)
        with open(path, "a") as f:
            f.write(line + "\n")
    return log


def cmd_collect(args):
    projects = _projects(args)
    log = _run_logger(args.source)
    if args.source == "git":
        from .collect import git
        rows = git.run(projects, jobs=args.jobs, keep=args.keep, force=args.force, log=log)
        _table(rows, ["project", "repo", "status", "commits", "file_rows", "policy_versions", "clone_mb", "kept_mb",
                      "seconds", "error"])
    else:
        from .collect import github
        rows = github.run(projects, only=args.only, log=log)
        _table(rows, ["project", "repo", "status", "kind", "mode", "items", "platform_total", "pages", "seconds",
                      "error"])
    failed = [r for r in rows if str(r.get("status", "")).startswith("failed")]  # "not found" is a config problem
    if failed:
        print(f"{len(failed)} repo(s) failed; re-run the same command to resume them", file=sys.stderr)
        sys.exit(1)


def cmd_normalize(args):
    projects = _projects(args)
    if args.source == "git":
        from .normalize import git
        git.run(projects)
    else:
        from .normalize import github
        github.run(projects)


def r_totals(repo, kind: str) -> int | None:
    """Platform total from the selection probe, before a repo's first GitHub pass."""
    probe = paths.derived_dir("selection", "github_probe.parquet")
    if not repo.github or not probe.exists():
        return None
    import polars as pl
    row = pl.read_parquet(probe).filter(pl.col("repo").str.to_lowercase() == repo.github.lower())
    if row.height == 0:
        return None
    r = row.row(0, named=True)
    return (r["merged_prs"] + r["closed_unmerged_prs"] + r["open_prs"]) if kind == "prs" else (
        r["open_issues"] + r["closed_issues"])


def cmd_status(args):
    from . import store
    from .collect.git import successful_runs
    rows = []
    totals = {"prs": [0, 0], "issues": [0, 0]}
    rate_items = []
    for p in _projects(args):
        for r in p.repos:
            row = {"project": p.id, "repo": r.github or r.key}
            runs = successful_runs(r.key)
            if runs:
                meta = json.loads((runs[-1] / "meta.json").read_text())
                row["git"] = f"{meta['run_id']} ({meta['commits']:,} commits)"
            elif p.wants("git"):
                row["git"] = "-"
            if r.github and (p.wants("github_prs") or p.wants("github_issues")):
                st = store.load_state(paths.state_dir("github", f"github.com/{r.github}".lower() + ".json"))
                for k, want in (("prs", p.wants("github_prs")), ("issues", p.wants("github_issues"))):
                    if not want:
                        continue
                    s = st.get(k) or {}
                    total = s.get("platform_total") or r_totals(r, k)
                    done = total if s.get("complete") else s.get("items_done", 0)
                    totals[k][0] += done or 0
                    totals[k][1] += total or 0
                    if s.get("run_started_at") and s.get("run_items"):
                        started = datetime.fromisoformat(s["run_started_at"])
                        rate_items.append((started, s["run_items"], s.get("updated_at") or st.get("updated_at")))
                    row[k] = ("complete" if s.get("complete") else
                              f"{done:,}/{total:,}" if total else (f"{done:,}" if s else "-"))
                if st.get("heavy"):
                    row["heavy"] = len(st["heavy"])
            rows.append(row)
    _table(rows, ["project", "repo", "git", "prs", "issues", "heavy"])
    for k in ("prs", "issues"):
        done, total = totals[k]
        if total:
            print(f"{k}: {done:,} of {total:,} collected ({done / total:.0%})")
    # Recent rate: items collected by the current or latest pass of each repo, over the time since it began.
    if rate_items:
        start = min(t for t, _, _ in rate_items)
        end = max(datetime.fromisoformat(u) for _, _, u in rate_items if u)
        n = sum(i for _, i, _ in rate_items)
        hours = max(1e-6, (end - start).total_seconds() / 3600)
        left = sum(t - d for d, t in totals.values())
        if n and left > 0:
            print(f"rate over the latest passes: {n / hours:,.0f} items/hour; about {left / (n / hours):,.1f} hours left")


def cmd_clean_work(_args):
    d = paths.work_dir()
    if d.exists():
        shutil.rmtree(d)
    print(f"removed {d}")


def main(argv: list[str] | None = None):
    ap = argparse.ArgumentParser(prog="lh", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("info", help="paths, free space, token status").set_defaults(fn=cmd_info)

    p = sub.add_parser("projects", help="list configured projects")
    _add_selection(p)
    p.set_defaults(fn=cmd_projects)

    p = sub.add_parser("selection", help="sample-selection steps")
    p.add_argument("step", choices=["harvest", "signals", "score", "probe", "audit", "pilot", "render", "export",
                                    "rebuild"])
    p.add_argument("names", nargs="*", help="harvest: sources; signals: lenses")
    p.add_argument("--no-sizes", action="store_true", help="export: skip fetching GitHub repo sizes")
    p.set_defaults(fn=cmd_selection)

    p = sub.add_parser("collect", help="collect raw data")
    p.add_argument("source", choices=["git", "github"])
    _add_selection(p)
    p.add_argument("--jobs", type=int, help="git: clones in flight (default from config/study.yaml)")
    p.add_argument("--keep", action="store_true", help="git: keep the clones in LH_WORK_DIR")
    p.add_argument("--force", action="store_true", help="git: re-extract repos that already have an extract")
    p.add_argument("--only", choices=["prs", "issues"], help="github: collect only PRs or only issues")
    p.set_defaults(fn=cmd_collect)

    p = sub.add_parser("normalize", help="raw -> canonical tables")
    p.add_argument("source", choices=["git", "github"])
    _add_selection(p)
    p.set_defaults(fn=cmd_normalize)

    p = sub.add_parser("status", help="what has been collected")
    _add_selection(p)
    p.set_defaults(fn=cmd_status)

    sub.add_parser("clean-work", help="delete LH_WORK_DIR (leftover clones)").set_defaults(fn=cmd_clean_work)

    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except KeyboardInterrupt:
        print("\ninterrupted; committed data and cursors are saved, re-run the same command to resume", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
