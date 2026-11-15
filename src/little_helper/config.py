"""Study settings (config/study.yaml) and per-project configs (config/projects/*.yaml)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import yaml

from . import paths


@cache
def study() -> dict:
    return yaml.safe_load((paths.config_dir() / "study.yaml").read_text()) or {}


@dataclass
class Repo:
    """One repository belonging to a project."""

    key: str  # host/owner/name, used for raw and state paths
    clone_urls: list[str]  # tried in order
    github: str | None = None  # owner/name when the repo (or a mirror) is on GitHub
    role: str | None = None  # primary, official_mirror, unofficial_mirror
    size_mb: float | None = None  # GitHub diskUsage, used to schedule clones

    @property
    def slug(self) -> str:
        return self.key.split("/", 1)[1]


@dataclass
class Project:
    id: str
    name: str
    regime: str | None
    repos: list[Repo]
    collect: dict = field(default_factory=dict)
    paths: dict = field(default_factory=dict)  # classification overrides
    policy_paths: list[str] = field(default_factory=list)  # extra AI/contribution policy files
    raw: dict = field(default_factory=dict)  # the whole YAML document

    def wants(self, what: str) -> bool:
        return bool(self.collect.get(what, False))


def repo_key_from_url(url: str) -> str:
    u = url.strip().removesuffix(".git").rstrip("/")
    for prefix in ("https://", "http://", "git://", "ssh://"):
        u = u.removeprefix(prefix)
    u = u.removeprefix("git@").replace(":", "/", 1) if u.startswith("git@") else u
    return u.lower()


def _project(doc: dict) -> Project:
    repos = []
    for r in doc.get("repos", []):
        urls = list(r.get("clone_urls") or [])
        gh = r.get("github")
        if gh and f"https://github.com/{gh}.git" not in urls:
            urls.append(f"https://github.com/{gh}.git")
        key = r.get("key") or (f"github.com/{gh}".lower() if gh else repo_key_from_url(urls[0]))
        repos.append(Repo(key=key, clone_urls=urls, github=gh, role=r.get("role"), size_mb=r.get("size_mb")))
    return Project(
        id=doc["id"], name=doc.get("name", doc["id"]), regime=doc.get("regime"), repos=repos,
        collect=doc.get("collect") or {}, paths=doc.get("paths") or {},
        policy_paths=doc.get("policy_paths") or [], raw=doc,
    )


def projects_dir() -> Path:
    return paths.config_dir() / "projects"


def load_projects() -> dict[str, Project]:
    out = {}
    for f in sorted(projects_dir().glob("*.yaml")):
        doc = yaml.safe_load(f.read_text())
        out[doc["id"]] = _project(doc)
    return out


def select(ids: list[str] | None = None, set_name: str | None = None, all_: bool = False) -> list[Project]:
    projects = load_projects()
    if all_:
        return list(projects.values())
    wanted = list(ids or [])
    if set_name:
        sets = study().get("sets", {})
        if set_name not in sets:
            raise SystemExit(f"unknown set {set_name!r}; defined: {', '.join(sets)}")
        wanted += sets[set_name]
    if not wanted:
        raise SystemExit("name projects, or pass --set NAME or --all")
    missing = [i for i in wanted if i not in projects]
    if missing:
        raise SystemExit(f"no config for: {', '.join(missing)} (see config/projects/)")
    seen, out = set(), []
    for i in wanted:
        if i not in seen:
            seen.add(i)
            out.append(projects[i])
    return out
