"""Durable writes: run manifests, compressed page chunks, atomic files.

Every file under raw/ is written to a temporary name, flushed to disk and renamed
into place, so an interrupted run never leaves a half-written file under its final
name. Each committed file gets one manifest line with its sha256 and size, and is then
handed to objects.settle(), which uploads it when object storage is configured.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path

import zstandard

from . import objects, paths

ZSTD_LEVEL = 19


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _fsync_dir(directory: Path) -> None:
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass  # some filesystems (exFAT on macOS) refuse directory fsync
    finally:
        os.close(fd)


def commit_file(tmp: Path, final: Path) -> None:
    """Flush tmp to disk and atomically rename it to final."""
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, final)
    _fsync_dir(final.parent)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    commit_file(tmp, path)


def atomic_write_json(path: Path, obj) -> None:
    atomic_write_bytes(path, json.dumps(obj, indent=2, sort_keys=True, default=str).encode())


def write_parquet_atomic(df, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    df.write_parquet(tmp, compression="zstd", compression_level=10, statistics=True)
    commit_file(tmp, path)


_manifest_lock = threading.Lock()  # git extraction commits from several threads


class Manifest:
    """Append-only JSONL record of every file a run commits.

    One file per (source, run): <LH_MANIFEST_DIR>/<source>/<run_id>.jsonl.
    """

    def __init__(self, source: str, run_id: str):
        self.source, self.run_id = source, run_id
        self.path = paths.manifest_dir() / source / f"{run_id}.jsonl"

    def add(self, file: Path, **extra) -> dict:
        """Record a committed file, then upload it (and drop the local copy if heavy)."""
        entry = {
            "file": paths.relative_to_data(file),
            "bytes": file.stat().st_size,
            "sha256": sha256_file(file),
            "committed_at": paths.utcnow(),
            **extra,
        }
        with _manifest_lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
                f.flush()
                os.fsync(f.fileno())
            objects.settle(self.path)
        objects.settle(file, sha256=entry["sha256"])
        return entry


class PageWriter:
    """Write JSON records into zstd-compressed JSONL chunks.

    Records accumulate in the open chunk; commit() closes it, renames it into place
    and adds it to the manifest. Callers advance their resume cursor only after a
    commit, so a crash costs at most the open chunk.
    """

    def __init__(self, directory: Path, kind: str, manifest: Manifest, **meta):
        self.dir, self.kind, self.manifest, self.meta = Path(directory), kind, manifest, meta
        self.dir.mkdir(parents=True, exist_ok=True)
        # Count uploaded chunks too: with object storage they no longer exist locally.
        self.index = 1 + len(objects.list_files(self.dir, f"{kind}-*.jsonl.zst"))
        self.records = 0
        self._buf: io.BytesIO | None = None

    def write(self, record: dict) -> None:
        if self._buf is None:
            self._buf = io.BytesIO()
        self._buf.write(json.dumps(record, separators=(",", ":"), default=str).encode() + b"\n")
        self.records += 1

    @property
    def pending(self) -> int:
        return self.records

    def commit(self) -> Path | None:
        if self._buf is None or self.records == 0:
            return None
        final = self.dir / f"{self.kind}-{self.index:05d}.jsonl.zst"
        tmp = final.with_name(final.name + ".tmp")
        raw = self._buf.getvalue()
        tmp.write_bytes(zstandard.ZstdCompressor(level=ZSTD_LEVEL).compress(raw))
        commit_file(tmp, final)
        self.manifest.add(final, kind=self.kind, records=self.records, raw_bytes=len(raw), **self.meta)
        self.index += 1
        self.records = 0
        self._buf = None
        return final


def data_files(directory: Path, pattern: str) -> list[Path]:
    """Sorted glob that skips macOS AppleDouble files ("._name"), which macOS writes
    next to files on FAT and exFAT drives and which are not data."""
    return sorted(p for p in Path(directory).glob(pattern) if not p.name.startswith("._"))


def iter_records(path: Path) -> Iterator[dict]:
    """Yield the JSON records of one committed chunk."""
    with open(path, "rb") as f:
        reader = zstandard.ZstdDecompressor().stream_reader(f)
        for line in io.TextIOWrapper(reader, encoding="utf-8"):
            if line.strip():
                yield json.loads(line)


def load_state(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def save_state(path: Path, state: dict) -> None:
    atomic_write_json(path, state)
    objects.settle(path)
