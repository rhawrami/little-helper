"""Where everything lives.

Three locations. Each is set by an environment variable, else by config/local.yaml
(machine-specific and not committed, e.g. `data_dir: /Volumes/chiikawa/little-helper`),
else a default:

LH_DATA_DIR      raw, canonical and derived data. Point it at the external drive.
                 Default: <repo>/data (fine for tests and the selection files).
LH_WORK_DIR      transient bare clones, deleted after extraction. Keep it on a fast
                 internal disk. Default: $XDG_CACHE_HOME/little-helper/work or
                 ~/.cache/little-helper/work.
LH_MANIFEST_DIR  run manifests (file, sha256, bytes, retrieval time). Small and meant
                 to be committed. Default: <repo>/data/manifests.

Layout under LH_DATA_DIR:

    raw/<source>/...                  immutable responses and git extracts
    state/<source>/...                resumable cursors (mutable bookkeeping)
    canonical/<table>/project=<id>/   rebuildable from raw
    derived/<name>/                   rebuildable from canonical
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


LOCAL_CONFIG = REPO / "config" / "local.yaml"


def _local() -> dict:
    if not LOCAL_CONFIG.exists():
        return {}
    import yaml
    return yaml.safe_load(LOCAL_CONFIG.read_text()) or {}


def _setting(env: str, key: str) -> str | None:
    return os.environ.get(env) or _local().get(key)


def _env_path(name: str, default: Path, key: str | None = None) -> Path:
    value = _setting(name, key) if key else os.environ.get(name)
    return Path(value).expanduser() if value else default


def data_dir() -> Path:
    configured = _setting("LH_DATA_DIR", "data_dir")
    d = Path(configured).expanduser() if configured else REPO / "data"
    # On macOS, writing under /Volumes/<drive> while the drive is unmounted silently
    # creates that folder on the internal disk. Refuse unless the folder or its parent exists.
    if configured and not d.exists() and not d.parent.exists():
        raise SystemExit(f"data directory {d} is not available. Is the drive mounted?")
    return d


def work_dir() -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return _env_path("LH_WORK_DIR", cache / "little-helper" / "work", "work_dir")


def manifest_dir() -> Path:
    return _env_path("LH_MANIFEST_DIR", REPO / "data" / "manifests", "manifest_dir")


def config_dir() -> Path:
    return REPO / "config"


def published_dir(*parts: str) -> Path:
    """Small outputs committed to the repo (selection tables, reports)."""
    return REPO.joinpath("data", *parts)


def raw_dir(*parts: str) -> Path:
    return data_dir().joinpath("raw", *parts)


def state_dir(*parts: str) -> Path:
    return data_dir().joinpath("state", *parts)


def canonical_dir(*parts: str) -> Path:
    return data_dir().joinpath("canonical", *parts)


def derived_dir(*parts: str) -> Path:
    return data_dir().joinpath("derived", *parts)


def relative_to_data(path: Path) -> str:
    """How a data file is recorded in manifests: relative to LH_DATA_DIR."""
    return str(Path(path).resolve().relative_to(data_dir().resolve()))


def resolve_data_file(recorded: str) -> Path:
    """Resolve a file path recorded in a manifest.

    Manifests written before the package layout (2026-11-13) record paths relative to
    the repo ("data/raw/..."); newer ones record them relative to LH_DATA_DIR ("raw/...").
    """
    rel = recorded.removeprefix("data/") if recorded.startswith("data/") else recorded
    return data_dir() / rel


def free_bytes(path: Path) -> int:
    p = Path(path)
    while not p.exists():
        p = p.parent
    return shutil.disk_usage(p).free


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
