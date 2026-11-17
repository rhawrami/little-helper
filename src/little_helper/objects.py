"""Object storage behind LH_DATA_DIR: DigitalOcean Spaces or any S3-compatible store.

Off unless a bucket is configured. When on, the bucket holds the study's data and the
local disk is a working copy:

- Every file `lh` commits under LH_DATA_DIR or LH_MANIFEST_DIR is uploaded to
  <prefix>/<path relative to LH_DATA_DIR> (manifests to <prefix>/manifests/...) and
  verified: size and a sha256 stored as object metadata must match the local file.
- Heavy files (*.parquet, *.jsonl.zst) are then deleted locally, unless keep_local is
  set. Small bookkeeping stays: state cursors, git meta.json, queries.json.
- Readers (normalize, plot) list local and remote files together and download what
  they need for as long as they need it.
- raw/ is immutable: a raw object is never overwritten with different content.
- If an upload fails (network down), the file stays local and is retried at the end
  of the run and at the start of the next one; `lh sync push` also catches up.

Settings (environment variable, else config/local.yaml key):

    LH_S3_BUCKET     s3_bucket     bucket (Space) name; setting it turns storage on
    LH_S3_PREFIX     s3_prefix     key prefix inside the bucket (default little-helper)
    LH_S3_ENDPOINT   s3_endpoint   e.g. https://nyc3.digitaloceanspaces.com. Optional
                                   when ~/.aws/config sets endpoint_url for the profile
    LH_S3_REGION     s3_region     default: taken from a Spaces endpoint, else the profile
    AWS_PROFILE      s3_profile    profile in ~/.aws/credentials (default: [default])
    LH_KEEP_LOCAL    keep_local    1 keeps local copies of heavy files after upload

Credentials come from ~/.aws/credentials (or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY)
as boto3 resolves them. They are never read or logged by this module.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import sys
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from . import paths

HEAVY_SUFFIXES = (".parquet", ".jsonl.zst")
MARKER = ".lh-sync"  # written into LH_DATA_DIR once this machine is in step with the bucket
CATCH_UP_AGE = 1800  # seconds; younger local files may still be in the hands of another lh process

_lock = threading.Lock()
_pending: set[Path] = set()


class Conflict(RuntimeError):
    """A raw object already exists with different content. Raw data is never overwritten."""


class UploadError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    bucket: str
    prefix: str
    endpoint: str | None
    region: str | None
    profile: str | None
    keep_local: bool


def settings() -> Settings | None:
    bucket = paths._setting("LH_S3_BUCKET", "s3_bucket")
    if not bucket:
        return None
    endpoint = paths._setting("LH_S3_ENDPOINT", "s3_endpoint")
    region = paths._setting("LH_S3_REGION", "s3_region")
    if not region and endpoint and "digitaloceanspaces.com" in endpoint:
        region = endpoint.split("://", 1)[-1].split(".", 1)[0]  # https://nyc3.digitaloceanspaces.com -> nyc3
    prefix = paths._setting("LH_S3_PREFIX", "s3_prefix")
    keep = str(paths._setting("LH_KEEP_LOCAL", "keep_local") or "").lower() in ("1", "true", "yes")
    return Settings(bucket=bucket, prefix=("little-helper" if prefix is None else prefix).strip("/"),
                    endpoint=endpoint, region=region,
                    profile=os.environ.get("AWS_PROFILE") or paths._local().get("s3_profile"), keep_local=keep)


def enabled() -> bool:
    return settings() is not None


def pruning() -> bool:
    s = settings()
    return s is not None and not s.keep_local


def describe() -> str:
    s = settings()
    if not s:
        return "off (set LH_S3_BUCKET to use object storage)"
    where = s.endpoint or "endpoint from the AWS config"
    return (f"s3://{s.bucket}/{s.prefix} at {where}, profile {s.profile or 'default'}; "
            + ("local copies kept" if s.keep_local else "heavy files deleted locally after upload"))


# ------------------------------------------------------------------ client

@lru_cache(maxsize=4)
def _client_for(s: Settings):
    import boto3
    from botocore.config import Config

    session = boto3.session.Session(profile_name=s.profile) if s.profile else boto3.session.Session()
    cfg = Config(
        retries={"max_attempts": 10, "mode": "standard"},
        connect_timeout=20, read_timeout=120,
        s3={"addressing_style": "virtual"},
        # botocore >= 1.36 adds CRC checksums to every upload by default; not every
        # S3-compatible store accepts them. Integrity is checked with our own sha256.
        request_checksum_calculation="when_required", response_checksum_validation="when_required",
    )
    return session.client("s3", endpoint_url=s.endpoint or None, region_name=s.region or session.region_name
                          or "us-east-1", config=cfg)


def _client():
    s = settings()
    if s is None:
        raise RuntimeError("object storage is off")
    with _lock:
        return _client_for(s), s


def _transfer():
    from boto3.s3.transfer import TransferConfig
    return TransferConfig(multipart_threshold=64 << 20, multipart_chunksize=64 << 20, max_concurrency=4)


def _errors() -> tuple[type[BaseException], ...]:
    from boto3.exceptions import S3UploadFailedError
    from botocore.exceptions import BotoCoreError, ClientError
    return BotoCoreError, ClientError, S3UploadFailedError, UploadError, OSError


def _warn(msg: str):
    print(f"[objects] {msg}", file=sys.stderr, flush=True)


# ------------------------------------------------------------------ keys

def _bases() -> list[tuple[Path, str]]:
    # The manifest dir first: by default it sits inside the data dir (data/manifests).
    return [(paths.manifest_dir().resolve(), "manifests"), (paths.data_dir().resolve(), "")]


def relkey(path: Path) -> str:
    """Key of a local path without the prefix: raw/..., state/..., manifests/..."""
    p = Path(path).resolve()
    for base, sub in _bases():
        try:
            rel = p.relative_to(base).as_posix()
        except ValueError:
            continue
        return "/".join(x for x in (sub, "" if rel == "." else rel) if x)
    raise ValueError(f"{path} is outside LH_DATA_DIR and LH_MANIFEST_DIR")


def key(path: Path) -> str:
    s = settings()
    rk = relkey(path)
    return "/".join(x for x in ((s.prefix if s else ""), rk) if x)


def path_for(k: str) -> Path:
    """Local path of an object key (the inverse of key())."""
    s = settings()
    rk = k[len(s.prefix) + 1:] if s and s.prefix else k
    if rk.startswith("manifests/"):
        return paths.manifest_dir() / rk.removeprefix("manifests/")
    return paths.data_dir() / rk


def heavy(path: Path) -> bool:
    return Path(path).name.endswith(HEAVY_SUFFIXES)


def immutable(path: Path) -> bool:
    return relkey(path).startswith("raw/")


def _skip(name: str) -> bool:
    return name.startswith("._") or name.endswith(".tmp") or name == MARKER


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------ objects

def _head(k: str) -> dict | None:
    from botocore.exceptions import ClientError
    client, s = _client()
    try:
        r = client.head_object(Bucket=s.bucket, Key=k)
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
            return None
        raise
    return {"size": r["ContentLength"], "sha256": (r.get("Metadata") or {}).get("sha256")}


def upload(path: Path, sha256: str | None = None) -> str:
    """Upload one file and verify it. Returns "uploaded" or "present". Raises on failure."""
    path = Path(path)
    client, s = _client()
    k = key(path)
    sha = sha256 or sha256_file(path)
    size = path.stat().st_size
    if immutable(path):
        head = _head(k)
        if head and head["size"] == size and head["sha256"] == sha:
            return "present"
        if head:
            raise Conflict(f"{k} already exists in the bucket with different content ({head['size']} bytes, "
                           f"sha256 {head['sha256']}); raw objects are never overwritten")
    client.upload_file(str(path), s.bucket, k, ExtraArgs={"Metadata": {"sha256": sha}}, Config=_transfer())
    head = _head(k)
    if not head or head["size"] != size or head["sha256"] != sha:
        raise UploadError(f"{k}: verification failed after upload ({head})")
    return "uploaded"


def settle(path: Path, sha256: str | None = None) -> bool:
    """Upload a newly committed file, then delete it locally if it is heavy and pruning is on.

    Never raises for storage or network errors: the file stays local and is retried later.
    Returns True when the file is safely in the bucket (or storage is off).
    """
    if not enabled():
        return True
    path = Path(path)
    try:
        upload(path, sha256)
    except Conflict:
        raise
    except _errors() as e:
        with _lock:
            _pending.add(path)
        _warn(f"upload of {relkey(path)} failed, kept locally for a retry: {e}")
        return False
    with _lock:
        _pending.discard(path)
    if heavy(path) and pruning():
        path.unlink(missing_ok=True)
    return True


def delete(path: Path) -> None:
    if not enabled():
        return
    client, s = _client()
    client.delete_object(Bucket=s.bucket, Key=key(path))


def download(path: Path) -> Path:
    """Fetch one object to its local path, verifying its sha256 when recorded."""
    path = Path(path)
    client, s = _client()
    k = key(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.tmp")
    try:
        client.download_file(s.bucket, k, str(tmp), Config=_transfer())
        head = _head(k)
        if head and head["sha256"] and sha256_file(tmp) != head["sha256"]:
            raise UploadError(f"{k}: downloaded content does not match its sha256")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return path


def listing(directory: Path, delimiter: bool = False) -> dict[str, int]:
    """Remote objects under a local directory: {relative path: size}. With delimiter,
    the immediate subdirectories instead ({name/: 0})."""
    if not enabled():
        return {}
    client, s = _client()
    base = key(directory).rstrip("/") + "/"
    out: dict[str, int] = {}
    kw = {"Bucket": s.bucket, "Prefix": base, **({"Delimiter": "/"} if delimiter else {})}
    for page in client.get_paginator("list_objects_v2").paginate(**kw):
        for o in page.get("Contents", []) or []:
            if not delimiter:
                out[o["Key"][len(base):]] = o["Size"]
        for cp in page.get("CommonPrefixes", []) or []:
            out[cp["Prefix"][len(base):]] = 0
    return out


def list_files(directory: Path, pattern: str) -> list[Path]:
    """Data files matching a glob under `directory`, local and remote together, sorted."""
    directory = Path(directory)
    depth = pattern.count("/")
    found = {}
    if directory.exists():
        for p in directory.glob(pattern):
            if p.is_file() and not _skip(p.name):
                found[p.relative_to(directory).as_posix()] = p
    for rel in listing(directory):
        if rel.count("/") == depth and fnmatch.fnmatch(rel, pattern) and not _skip(rel.rsplit("/", 1)[-1]):
            found.setdefault(rel, directory / rel)
    return [found[k] for k in sorted(found)]


def subdirs(directory: Path) -> list[Path]:
    directory = Path(directory)
    names = {p.name for p in directory.iterdir() if p.is_dir()} if directory.exists() else set()
    names |= {n.rstrip("/") for n in listing(directory, delimiter=True)}
    return [directory / n for n in sorted(names)]


def exists(path: Path) -> bool:
    path = Path(path)
    return path.exists() or (enabled() and _head(key(path)) is not None)


@contextmanager
def local_copies(files: list[Path]) -> Iterator[list[Path]]:
    """Make sure the files are on local disk while in use. Files downloaded here are
    deleted afterwards when pruning is on."""
    fetched = []
    try:
        for f in files:
            if not Path(f).exists():
                download(f)
                fetched.append(Path(f))
        yield list(files)
    finally:
        if pruning():
            for f in fetched:
                f.unlink(missing_ok=True)


# ------------------------------------------------------------------ catching up

def retry_pending(log=print) -> int:
    """Retry uploads that failed earlier in this process. Returns how many are still pending."""
    with _lock:
        todo = sorted(_pending)
    for p in todo:
        if p.exists():
            settle(p)
        else:
            with _lock:
                _pending.discard(p)
    with _lock:
        left = len(_pending)
    if left:
        log(f"[objects] {left} file(s) still not uploaded; they stay local. Run `lh sync push` later.")
    return left


def catch_up(log=print) -> int:
    """Upload heavy files left locally by an earlier run whose uploads failed. Only
    files older than CATCH_UP_AGE are touched, so another running lh is never disturbed."""
    if not pruning():
        return 0
    n = 0
    now = time.time()
    for top in (paths.raw_dir(), paths.canonical_dir()):
        if not top.exists():
            continue
        for root, dirs, files in os.walk(top):
            dirs[:] = [d for d in dirs if not d.endswith(".partial")]
            for name in files:
                p = Path(root) / name
                if heavy(p) and not _skip(name) and now - p.stat().st_mtime > CATCH_UP_AGE:
                    if settle(p):
                        n += 1
    if n:
        log(f"[objects] uploaded {n} file(s) left over from an earlier run")
    return n


# ------------------------------------------------------------------ sync

SYNC_TOPS = ("raw", "state", "canonical", "derived", "logs")


def _root(s: Settings) -> str:
    return f"{s.prefix}/" if s.prefix else ""


def _local_files() -> Iterator[Path]:
    seen = set()
    roots = [paths.data_dir() / t for t in SYNC_TOPS] + [paths.manifest_dir()]
    for top in roots:
        if not top.exists():
            continue
        for root, dirs, files in os.walk(top):
            dirs[:] = [d for d in dirs if not d.endswith(".partial")]
            for name in files:
                p = (Path(root) / name).resolve()
                if not _skip(name) and p not in seen:
                    seen.add(p)
                    yield Path(root) / name


def push(*, prune: bool = False, dry_run: bool = False, log=print) -> dict:
    """Upload every local file the bucket lacks or holds an older version of."""
    client, s = _client()
    remote: dict[str, int] = {}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=s.bucket, Prefix=_root(s)):
        for o in page.get("Contents", []) or []:
            remote[o["Key"]] = o["Size"]
    counts = {"uploaded": 0, "present": 0, "conflicts": 0, "failed": 0, "pruned": 0, "bytes": 0}
    for p in _local_files():
        k, size = key(p), p.stat().st_size
        if k in remote and remote[k] == size and (immutable(p) or (_head(k) or {}).get("sha256") == sha256_file(p)):
            result = "present"
        elif k in remote and immutable(p):
            log(f"  conflict: {relkey(p)} differs from the bucket copy; not overwritten")
            counts["conflicts"] += 1
            continue
        elif dry_run:
            log(f"  would upload {relkey(p)} ({size:,} bytes)")
            counts["uploaded"] += 1
            counts["bytes"] += size
            continue
        else:
            try:
                result = upload(p)
            except Conflict as e:
                log(f"  conflict: {e}")
                counts["conflicts"] += 1
                continue
            except _errors() as e:
                log(f"  FAILED {relkey(p)}: {e}")
                counts["failed"] += 1
                continue
            counts["bytes"] += size
        counts[result] += 1
        if prune and not dry_run and heavy(p):
            p.unlink()
            counts["pruned"] += 1
    if not dry_run and not counts["failed"] and not counts["conflicts"]:
        mark_synced()
    return counts


def pull(*, everything: bool = False, dry_run: bool = False, log=print) -> dict:
    """Download objects missing locally. By default only what a machine needs to resume:
    state/ (the cursors), derived/ (selection tables `lh status` reads) and each git
    run's meta.json (the record that a repo is extracted). The rest stays in the bucket."""
    client, s = _client()
    counts = {"downloaded": 0, "present": 0, "skipped": 0, "bytes": 0}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=s.bucket, Prefix=_root(s)):
        for o in page.get("Contents", []) or []:
            p = path_for(o["Key"])
            rk = relkey(p)
            wanted = everything or rk.split("/", 1)[0] in ("state", "derived") or (
                rk.startswith("raw/git/") and p.name == "meta.json")
            if not wanted or _skip(p.name):
                counts["skipped"] += 1
            elif p.exists():
                counts["present"] += 1
            elif dry_run:
                log(f"  would download {rk} ({o['Size']:,} bytes)")
                counts["downloaded"] += 1
                counts["bytes"] += o["Size"]
            else:
                download(p)
                counts["downloaded"] += 1
                counts["bytes"] += o["Size"]
    if not dry_run:
        mark_synced()
    return counts


def check(log=print) -> None:
    """Write, read back and delete a probe object. Raises if anything fails."""
    client, s = _client()
    client.head_bucket(Bucket=s.bucket)
    k = "/".join(x for x in (s.prefix, f"_probe/{uuid.uuid4().hex}") if x)
    body = os.urandom(1024)
    client.put_object(Bucket=s.bucket, Key=k, Body=body, Metadata={"sha256": hashlib.sha256(body).hexdigest()})
    got = client.get_object(Bucket=s.bucket, Key=k)["Body"].read()
    client.delete_object(Bucket=s.bucket, Key=k)
    if got != body:
        raise UploadError("probe object came back different")
    log(f"object storage OK: wrote, read and deleted a probe in s3://{s.bucket}/{s.prefix}")


def mark_synced() -> None:
    m = paths.data_dir() / MARKER
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(f"{paths.utcnow()}\n")


def preflight() -> None:
    """Refuse to collect on a machine that has not synced with a bucket that already holds
    data: without the state cursors it would start every crawl over."""
    s = settings()
    if s is None or (paths.data_dir() / MARKER).exists():
        return
    client, _ = _client()
    for top in ("state/", "raw/"):
        if client.list_objects_v2(Bucket=s.bucket, Prefix=_root(s) + top, MaxKeys=1).get("KeyCount", 0):
            raise SystemExit(f"s3://{s.bucket}/{s.prefix} already holds data, but this machine has not synced "
                             "with it.\nRun `uv run lh sync pull` first (or `uv run lh sync push` if this "
                             "machine's data is the original).")
    mark_synced()  # an empty bucket: this machine starts the study
