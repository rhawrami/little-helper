"""Rolling git collection: clone -> extract -> verify -> delete.

For each repository (docs/data_collection_plan.md §3.1a):

1. Bare-clone into LH_WORK_DIR (the fast internal disk). The clone has no working tree.
2. Extract into raw/git/<host>/<owner>/<repo>/<run_id>/:
     commits-NNNNN.parquet   one row per commit reachable from any branch or tag:
                             sha, parents, author/committer name, email, ISO date,
                             full message, on_default, first_parent
     files-NNNNN.parquet     one row per (commit, changed path): lines added and
                             deleted (null for binary), change type A/M/D.
                             Merge commits carry no rows, as in `git log`.
     refs.parquet            every branch and tag with its target, peeled commit, date
     trees.parquet           yearly (or quarterly) listings of the default branch
                             tree: path, type, size. Codebase size without a checkout.
     policy_files.parquet    every version of AI-policy, agent-instruction and
                             contribution-policy files (content capped per version)
     meta.json               clone URL, timings, sizes, counts, git and extractor
                             versions, HEAD and default branch
3. Verify: the parsed commit count must equal `git rev-list --all --count`.
4. Delete the clone (unless --keep).

The extract directory is written under a temporary name and renamed when complete,
so a raw/git run directory either has every file or does not exist.
"""

from __future__ import annotations

import codecs
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from .. import config, paths, store

EXTRACTOR_VERSION = 1
SOURCE = "git"
_RS, _FS = b"\x1e", "\x1f"
LOG_FORMAT = "%x1e%H%x1f%P%x1f%an%x1f%ae%x1f%aI%x1f%cn%x1f%ce%x1f%cI%x1f%B%x1f"
CLONE_MARKER = "lh-clone-complete"  # written into a bare clone once `git clone` succeeds
REUSE_CLONE_HOURS = 24  # a kept clone younger than this is reused instead of downloaded again
_TRANSIENT = ("could not resolve host", "unexpected disconnect", "early eof", "connection reset", "timed out",
              "rpc failed", "remote end hung up", "operation too slow", "ssl", "gnutls", "http/2 stream",
              "failed to connect", "connection refused", "transfer closed", "the requested url returned error: 5")


_STOP = threading.Event()  # set on Ctrl-C so worker threads stop retrying and exit


def _git_env() -> dict:
    # Read os.environ per call. Do not strip GIT_CONFIG_PARAMETERS: some shells set
    # safe.bareRepository=explicit there, which is why every call names the repo with --git-dir.
    return {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "echo", "LC_ALL": "C"}
BATCH_COMMITS = 200_000

COMMIT_COLS = ["sha", "parents", "author_name", "author_email", "author_date",
               "committer_name", "committer_email", "committer_date", "message"]


class GitError(RuntimeError):
    pass


def settings() -> dict:
    return config.study().get("git", {})


def git(*args: str, cwd: Path | None = None, input: bytes | None = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run git; `cwd` is a bare repository, addressed explicitly with --git-dir."""
    cmd = ["git", *([f"--git-dir={cwd}"] if cwd else []), *args]
    r = subprocess.run(cmd, input=input, capture_output=True, env=_git_env())
    if check and r.returncode != 0:
        raise GitError(f"{' '.join(cmd[:6])}: {r.stderr.decode(errors='replace')[-500:]}")
    return r


def git_version() -> str:
    return git("--version").stdout.decode().strip()


# ------------------------------------------------------------------ policy files

def _glob_rx(g: str) -> str:
    return re.escape(g).replace(r"\*", "[^/]*")


def policy_regex(extra_paths: list[str] | None = None) -> re.Pattern:
    pf = settings().get("policy_files", {})
    alts = []
    if pf.get("anywhere"):
        alts.append(r"(^|/)(" + "|".join(re.escape(n) for n in pf["anywhere"]) + r")$")
    if pf.get("top_level"):
        alts.append(r"^(\.github/|docs?/)?(" + "|".join(_glob_rx(g) for g in pf["top_level"]) + r")$")
    if pf.get("dirs"):
        alts.append(r"(^|/)(" + "|".join(re.escape(d.rstrip("/") + "/") for d in pf["dirs"]) + r")")
    if pf.get("name_words"):
        alts.append(r"(^|/)[^/]*(" + "|".join(pf["name_words"]) + r")[^/]*\.(md|rst|txt|adoc|html?)$")
    for p in extra_paths or []:
        alts.append(p if p.startswith("^") else "^" + re.escape(p) + "$")
    return re.compile("|".join(f"(?:{a})" for a in alts) or r"(?!)", re.I)


# ------------------------------------------------------------------ parsing

def _unquote(path: str) -> str:
    """Undo git's C-style quoting of unusual paths ("a\\tb", octal UTF-8 bytes)."""
    if len(path) >= 2 and path[0] == '"' and path[-1] == '"':
        raw = codecs.escape_decode(path[1:-1].encode("utf-8", "surrogateescape"))[0]
        return raw.decode("utf-8", "replace")
    return path


def parse_record(rec: bytes) -> tuple[dict, list[tuple[str, int | None, int | None, str]]]:
    text = rec.decode("utf-8", "replace")
    head = text.split(_FS, 8)
    if len(head) < 9:
        raise GitError(f"unparseable log record: {text[:120]!r}")
    sha, parents, an, ae, ad, cn, ce, cd, remainder = head
    message, _, diff = remainder.rpartition(_FS)
    files: dict[str, list] = {}
    for line in diff.splitlines():
        if not line:
            continue
        if line[0] == " ":
            parts = line.strip().split(" ")
            if parts[:2] == ["create", "mode"] and len(parts) >= 4:
                p = _unquote(line.strip().split(" ", 3)[3])
                files.setdefault(p, [p, None, None, "M"])[3] = "A"
            elif parts[:2] == ["delete", "mode"] and len(parts) >= 4:
                p = _unquote(line.strip().split(" ", 3)[3])
                files.setdefault(p, [p, None, None, "M"])[3] = "D"
            continue
        cols = line.split("\t", 2)
        if len(cols) != 3:
            continue
        a, d, p = cols
        p = _unquote(p)
        row = files.setdefault(p, [p, None, None, "M"])
        row[1] = None if a == "-" else int(a)
        row[2] = None if d == "-" else int(d)
    commit = {"sha": sha, "parents": parents.split() if parents else [], "author_name": an, "author_email": ae,
              "author_date": ad, "committer_name": cn, "committer_email": ce, "committer_date": cd,
              "message": message}
    return commit, [tuple(r) for r in files.values()]


def iter_log(gitdir: Path) -> Iterator[tuple[dict, list]]:
    cmd = ["git", f"--git-dir={gitdir}", "-c", "core.quotepath=off", "log", "--all", "--no-renames",
           "--numstat", "--summary", "--no-color", f"--format={LOG_FORMAT}"]
    with tempfile.TemporaryFile() as err:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err, env=_git_env())
        buf = b""
        assert proc.stdout is not None
        for chunk in iter(lambda: proc.stdout.read(1 << 20), b""):
            buf += chunk
            parts = buf.split(_RS)
            buf = parts.pop()
            for rec in parts:
                if rec:
                    yield parse_record(rec)
        if buf:
            yield parse_record(buf)
        if proc.wait() != 0:
            err.seek(0)
            raise GitError(f"git log failed: {err.read().decode(errors='replace')[-500:]}")


def _rev_set(gitdir: Path, *args: str) -> set[str]:
    r = git("rev-list", *args, cwd=gitdir, check=False)
    return set(r.stdout.decode().split()) if r.returncode == 0 else set()


# ------------------------------------------------------------------ extraction

def extract(gitdir: Path, out: Path, policy_rx: re.Pattern, log=print) -> dict:
    """Extract every table from a bare clone into `out`. Returns counts and facts."""
    out.mkdir(parents=True, exist_ok=True)
    head = git("rev-parse", "--verify", "-q", "HEAD", cwd=gitdir, check=False).stdout.decode().strip() or None
    default_branch = git("symbolic-ref", "--short", "-q", "HEAD", cwd=gitdir, check=False).stdout.decode().strip() or None
    on_default = _rev_set(gitdir, "HEAD") if head else set()
    first_parent = _rev_set(gitdir, "--first-parent", "HEAD") if head else set()

    cols: dict[str, list] = {c: [] for c in COMMIT_COLS}
    fcols: dict[str, list] = {"sha": [], "path": [], "added": [], "deleted": [], "change": []}
    n_commits = n_files = part = 0
    policy_hits: list[tuple[str, str]] = []
    min_fp_date: str | None = None

    def flush():
        nonlocal part
        if not cols["sha"]:
            return
        c = pl.DataFrame(cols, schema={"sha": pl.Utf8, "parents": pl.List(pl.Utf8), **{k: pl.Utf8 for k in COMMIT_COLS[2:]}})
        c = c.with_columns(pl.col("sha").is_in(list(on_default)).alias("on_default"),
                           pl.col("sha").is_in(list(first_parent)).alias("first_parent"))
        c.write_parquet(out / f"commits-{part:05d}.parquet", compression="zstd", compression_level=10)
        f = pl.DataFrame(fcols, schema={"sha": pl.Utf8, "path": pl.Utf8, "added": pl.Int64, "deleted": pl.Int64,
                                        "change": pl.Utf8})
        f.write_parquet(out / f"files-{part:05d}.parquet", compression="zstd", compression_level=10)
        for v in cols.values():
            v.clear()
        for v in fcols.values():
            v.clear()
        part += 1

    t0 = time.time()
    for commit, files in iter_log(gitdir):
        for k in COMMIT_COLS:
            cols[k].append(commit[k])
        sha = commit["sha"]
        if sha in first_parent and (min_fp_date is None or commit["committer_date"] < min_fp_date):
            min_fp_date = commit["committer_date"]
        for p, a, d, ch in files:
            fcols["sha"].append(sha)
            fcols["path"].append(p)
            fcols["added"].append(a)
            fcols["deleted"].append(d)
            fcols["change"].append(ch)
            if ch != "D" and policy_rx.search(p):
                policy_hits.append((sha, p))
        n_commits += 1
        n_files += len(files)
        if len(cols["sha"]) >= BATCH_COMMITS:
            flush()
    flush()
    t_log = time.time() - t0

    expected = int(git("rev-list", "--all", "--count", cwd=gitdir).stdout.decode().strip() or 0)
    if expected != n_commits:
        raise GitError(f"parsed {n_commits} commits but rev-list --all counts {expected}")

    refs = _refs(gitdir)
    refs.write_parquet(out / "refs.parquet", compression="zstd")
    trees = _trees(gitdir, head, min_fp_date) if head else pl.DataFrame()
    if trees.height:
        trees.write_parquet(out / "trees.parquet", compression="zstd", compression_level=10)
    policies = _policy_contents(gitdir, policy_hits)
    if policies.height:
        policies.write_parquet(out / "policy_files.parquet", compression="zstd", compression_level=10)
    return {"head": head, "default_branch": default_branch, "commits": n_commits, "file_rows": n_files,
            "parts": part, "refs": refs.height, "tree_rows": trees.height, "policy_versions": policies.height,
            "first_parent_commits": len(first_parent), "default_branch_commits": len(on_default),
            "seconds_log": round(t_log, 1)}


def _refs(gitdir: Path) -> pl.DataFrame:
    fmt = "%(refname)%1f%(objecttype)%1f%(objectname)%1f%(*objectname)%1f%(*objecttype)%1f%(creatordate:iso-strict)"
    rows = []
    for line in git("for-each-ref", f"--format={fmt}", cwd=gitdir).stdout.decode("utf-8", "replace").splitlines():
        name, otype, oid, peeled, ptype, date = (line.split(_FS) + [""] * 6)[:6]
        rows.append({"ref": name, "object_type": otype, "object": oid, "peeled": peeled or None,
                     "peeled_type": ptype or None, "date": date or None})
    schema = {k: pl.Utf8 for k in ["ref", "object_type", "object", "peeled", "peeled_type", "date"]}
    return pl.DataFrame(rows, schema=schema)


def snapshot_dates(first_date: str | None, freq: str, now: datetime | None = None) -> list[str]:
    if not first_date:
        return []
    start = datetime.fromisoformat(first_date).astimezone(timezone.utc)
    now = now or datetime.now(timezone.utc)
    months = (1, 4, 7, 10) if freq == "quarterly" else (1,)
    out = []
    for y in range(start.year, now.year + 1):
        for m in months:
            d = datetime(y, m, 1, tzinfo=timezone.utc)
            if start < d <= now:
                out.append(d.strftime("%Y-%m-%dT00:00:00Z"))
    return out


def _trees(gitdir: Path, head: str, first_date: str | None) -> pl.DataFrame:
    freq = settings().get("tree_snapshots", "yearly")
    targets = []
    for d in snapshot_dates(first_date, freq):
        c = git("rev-list", "-1", "--first-parent", f"--before={d}", head, cwd=gitdir).stdout.decode().strip()
        if c:
            targets.append((d[:10], c))
    targets.append(("head", head))
    frames = []
    for label, commit in targets:
        raw = git("-c", "core.quotepath=off", "ls-tree", "-r", "-l", "--full-tree", "-z", commit, cwd=gitdir).stdout
        rows = {"snapshot": [], "commit": [], "path": [], "type": [], "size": []}
        for entry in raw.split(b"\0"):
            if not entry:
                continue
            meta, _, p = entry.partition(b"\t")
            mode, typ, _oid, size = meta.decode().split()
            rows["snapshot"].append(label)
            rows["commit"].append(commit)
            rows["path"].append(p.decode("utf-8", "replace"))
            rows["type"].append(typ)
            rows["size"].append(None if size == "-" else int(size))
        frames.append(pl.DataFrame(rows, schema={"snapshot": pl.Utf8, "commit": pl.Utf8, "path": pl.Utf8,
                                                 "type": pl.Utf8, "size": pl.Int64}))
    return pl.concat(frames) if frames else pl.DataFrame()


def _policy_contents(gitdir: Path, hits: list[tuple[str, str]]) -> pl.DataFrame:
    schema = {"sha": pl.Utf8, "path": pl.Utf8, "blob": pl.Utf8, "size": pl.Int64, "truncated": pl.Boolean,
              "content": pl.Utf8}
    if not hits:
        return pl.DataFrame(schema=schema)
    cap = int(settings().get("policy_files", {}).get("max_bytes", 524288))
    stdin = b"".join(f"{sha}:{p}\n".encode() for sha, p in hits)
    data = git("cat-file", "--batch", cwd=gitdir, input=stdin).stdout
    rows, pos = [], 0
    for sha, p in hits:
        nl = data.index(b"\n", pos)
        line = data[pos:nl].decode(errors="replace")
        pos = nl + 1
        if line.endswith((" missing", " ambiguous")):
            continue  # the request echoes back "<sha>:<path> missing"; paths may contain spaces
        oid, typ, size_s = line.split()
        size = int(size_s)
        body = data[pos:pos + size]
        pos += size + 1
        if typ != "blob":
            continue
        rows.append({"sha": sha, "path": p, "blob": oid, "size": size, "truncated": size > cap,
                     "content": body[:cap].decode("utf-8", "replace")})
    return pl.DataFrame(rows, schema=schema)


# ------------------------------------------------------------------ one repository

def dir_size(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total


def successful_runs(key: str) -> list[Path]:
    base = paths.raw_dir(SOURCE, key)
    if not base.exists():
        return []
    out = []
    for meta in sorted(base.glob("*/meta.json")):
        if json.loads(meta.read_text()).get("status") == "ok":
            out.append(meta.parent)
    return out


@dataclass
class Job:
    project: config.Project
    repo: config.Repo

    @property
    def size_mb(self) -> float:
        return self.repo.size_mb if self.repo.size_mb is not None else float(settings().get("unknown_size_mb", 4096))


def _reusable_clone(clone_dir: Path) -> bool:
    """A complete clone kept from an earlier attempt (e.g. extraction failed) and still fresh."""
    marker = clone_dir / CLONE_MARKER
    if not marker.exists() or (time.time() - marker.stat().st_mtime) > REUSE_CLONE_HOURS * 3600:
        return False
    return git("rev-parse", "--git-dir", cwd=clone_dir, check=False).returncode == 0


def _clone(urls: list[str], clone_dir: Path, log, attempts: int = 3) -> str:
    """Clone from the first URL that works, retrying transient network failures."""
    errors = []
    for u in urls:
        for attempt in range(attempts):
            if _STOP.is_set():
                raise GitError("interrupted")
            shutil.rmtree(clone_dir, ignore_errors=True)
            r = subprocess.run(["git", "clone", "--bare", "--quiet", u, str(clone_dir)], capture_output=True,
                               env=_git_env())
            if r.returncode == 0:
                (clone_dir / CLONE_MARKER).write_text(f"{u}\n{paths.utcnow()}\n")
                return u
            if r.returncode < 0 or _STOP.is_set():  # killed by a signal (Ctrl-C), not a network error
                shutil.rmtree(clone_dir, ignore_errors=True)
                raise GitError("interrupted")
            err = r.stderr.decode(errors="replace").strip()
            transient = any(t in err.lower() for t in _TRANSIENT)
            errors.append(f"{u} (attempt {attempt + 1}): {err[-300:]}")
            if not transient or attempt == attempts - 1:
                break
            wait = 30 * 4 ** attempt  # 30 s, then 2 min
            log(f"[git] {clone_dir.name}: network error cloning {u}; retrying in {wait}s")
            if _STOP.wait(wait):
                raise GitError("interrupted")
    shutil.rmtree(clone_dir, ignore_errors=True)
    raise GitError("clone failed: " + " | ".join(errors))


def collect_repo(job: Job, run_id: str, manifest: store.Manifest, *, keep: bool = False, log=print) -> dict:
    repo, key = job.repo, job.repo.key
    clone_dir = paths.work_dir() / "git" / f"{key}.git"
    final = paths.raw_dir(SOURCE, key, run_id)
    tmp_out = final.with_name(final.name + ".partial")
    summary = {"project": job.project.id, "repo": key, "status": "failed"}
    cloned = False
    try:
        t0 = time.time()
        if _reusable_clone(clone_dir):
            url = (clone_dir / CLONE_MARKER).read_text().split("\n")[0]
            t_clone = 0.0
            log(f"[git] {key}: reusing the clone kept from an earlier attempt")
        else:
            need = job.size_mb * 1.6 * 1e6 + float(settings().get("reserve_free_gb", 10)) * 1e9
            free = paths.free_bytes(paths.work_dir())
            if free < need:
                raise GitError(f"not enough free space in {paths.work_dir()}: {free / 1e9:.1f} GB free, "
                               f"need ~{need / 1e9:.1f} GB (clone estimate + reserve)")
            clone_dir.parent.mkdir(parents=True, exist_ok=True)
            url = _clone(repo.clone_urls, clone_dir, log)
            t_clone = time.time() - t0
        cloned = True
        cloned_at = (clone_dir / CLONE_MARKER).read_text().split("\n")[1]
        clone_bytes = dir_size(clone_dir)
        if t_clone:
            log(f"[git] {key}: cloned {clone_bytes / 1e6:,.0f} MB from {url} in {t_clone:.0f}s")

        if tmp_out.exists():
            shutil.rmtree(tmp_out)
        facts = extract(clone_dir, tmp_out, policy_regex(job.project.policy_paths), log=log)
        meta = {"status": "ok", "project": job.project.id, "repo": key, "run_id": run_id, "clone_url": url,
                "cloned_at": cloned_at, "seconds_clone": round(t_clone, 1), "clone_bytes": clone_bytes,
                "git_version": git_version(), "extractor_version": EXTRACTOR_VERSION,
                "tree_snapshots": settings().get("tree_snapshots", "yearly"), **facts}
        store.atomic_write_json(tmp_out / "meta.json", meta)
        final.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_out, final)
        kept_mb = round(dir_size(final) / 1e6, 1)
        # Each file is uploaded as it is recorded; with object storage, heavy files then
        # leave the local disk and meta.json stays as the record of a successful run.
        for f in store.data_files(final, "*"):  # skips macOS "._" files on exFAT drives
            manifest.add(f, repo=key, project=job.project.id, extractor_version=EXTRACTOR_VERSION)
        summary.update(status="ok", commits=facts["commits"], file_rows=facts["file_rows"],
                       policy_versions=facts["policy_versions"], clone_mb=round(clone_bytes / 1e6),
                       kept_mb=kept_mb, seconds=round(time.time() - t0))
        log(f"[git] {key}: {facts['commits']:,} commits, {facts['file_rows']:,} file rows, "
            f"{facts['policy_versions']} policy-file versions -> {summary['kept_mb']} MB kept")
    except Exception as e:  # report and move on; the census run continues
        summary["error"] = str(e)[:500]
        log(f"[git] {key}: FAILED {e}" + (" (clone kept for the next run)" if cloned and not keep else ""))
        shutil.rmtree(tmp_out, ignore_errors=True)
    finally:
        # Delete after success. After an extraction failure keep the clone so a fixed
        # extractor can reuse it instead of downloading it again (`lh clean-work` removes it).
        if not keep and summary["status"] == "ok":
            shutil.rmtree(clone_dir, ignore_errors=True)
            _prune_empty(clone_dir.parent, stop=paths.work_dir())
        elif not cloned:
            shutil.rmtree(clone_dir, ignore_errors=True)
            _prune_empty(clone_dir.parent, stop=paths.work_dir())
    return summary


def _prune_empty(d: Path, stop: Path):
    """Remove empty owner/host folders left behind by deleted clones."""
    while d != stop and stop in d.parents:
        try:
            d.rmdir()
        except OSError:
            return
        d = d.parent


# ------------------------------------------------------------------ scheduling

class _Slots:
    """Counting semaphore where a big clone takes every slot."""

    def __init__(self, n: int):
        self.free, self.cv = n, threading.Condition()

    def acquire(self, k: int):
        with self.cv:
            while self.free < k:
                self.cv.wait()
            self.free -= k

    def release(self, k: int):
        with self.cv:
            self.free += k
            self.cv.notify_all()


def run(projects: list[config.Project], *, jobs: int | None = None, keep: bool = False, force: bool = False,
        log=print) -> list[dict]:
    jobs = jobs or int(settings().get("jobs", 2))
    big = float(settings().get("big_clone_mb", 2048))
    todo, skipped = [], []
    for p in projects:
        if not p.wants("git"):
            continue
        for r in p.repos:
            if not force and successful_runs(r.key):
                skipped.append({"project": p.id, "repo": r.key, "status": "skipped (already extracted)"})
            else:
                todo.append(Job(p, r))
    todo.sort(key=lambda j: j.size_mb, reverse=True)  # biggest first, while the disk is emptiest
    run_id = paths.new_run_id()
    manifest = store.Manifest(SOURCE, run_id)
    log(f"[git] run {run_id}: {len(todo)} repos to extract, {len(skipped)} already done; "
        f"work dir {paths.work_dir()}, data dir {paths.data_dir()}")
    slots = _Slots(jobs)
    lock = threading.Lock()

    def safe_log(msg):
        with lock:
            print(msg, flush=True) if log is print else log(msg)

    def task(job: Job) -> dict:
        k = jobs if job.size_mb >= big else 1
        slots.acquire(k)
        try:
            return collect_repo(job, run_id, manifest, keep=keep, log=safe_log)
        finally:
            slots.release(k)

    results = list(skipped)
    _STOP.clear()
    pool = ThreadPoolExecutor(max_workers=jobs)
    try:
        for fut in as_completed([pool.submit(task, j) for j in todo]):
            results.append(fut.result())
    except KeyboardInterrupt:
        _STOP.set()  # running clones were killed by the same Ctrl-C; stop their retries
        pool.shutdown(wait=True, cancel_futures=True)  # start nothing new
        raise
    pool.shutdown()
    return results
