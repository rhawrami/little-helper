"""Turn raw harvests into one tidy table per significance lens.

Reads the latest run of each source under $LH_DATA_DIR/raw/ and writes
$LH_DATA_DIR/derived/selection/<lens>.parquet.

Lenses:
  debian_{pre,now}  distribution dependency centrality (Debian sid snapshots)
  popcon            Debian Popularity Contest installs per source package
  repology          packaging ubiquity across distribution families
  dockerhub         Docker official-image pull counts
  criticality       OpenSSF Criticality Score (2025-07-25 snapshot)
  ossfuzz           OSS-Fuzz enrolment (main_repo)
  ecosystems        ecosyste.ms "critical" packages across 8 registries
"""

from __future__ import annotations

import gzip
import io
import json
import lzma
import re
from collections import defaultdict
from pathlib import Path

import polars as pl
import yaml

from .. import paths


def latest(source: str) -> Path:
    runs = sorted(p for p in paths.raw_dir(source).iterdir() if (p / "manifest.json").exists())
    return runs[-1]


def manifest(source: str) -> dict:
    return json.loads((latest(source) / "manifest.json").read_text())


def read(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix == ".gz":
        return gzip.decompress(data)
    if path.suffix == ".xz":
        return lzma.decompress(data)
    return data


def write(df: pl.DataFrame, name: str):
    out = paths.derived_dir("selection")
    out.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out / f"{name}.parquet")
    print(f"{name}: {df.height:,} rows")


def pct_rank(col: str) -> pl.Expr:
    """Percentile rank in [0, 1]; 1 = most significant within the lens."""
    return (pl.col(col).rank("average") / pl.col(col).count()).alias(f"{col}_pct")


# --------------------------------------------------------------------------- debian

def deb822(text: str):
    para: dict[str, str] = {}
    key = None
    for line in text.splitlines():
        if not line.strip():
            if para:
                yield para
            para, key = {}, None
        elif line[0] in " \t" and key:
            para[key] += "\n" + line.strip()
        else:
            key, _, val = line.partition(":")
            para[key] = val.strip()
    if para:
        yield para


DEP_NAME = re.compile(r"^\s*([a-z0-9][a-z0-9+.\-]+)")


def dep_names(field: str) -> set[str]:
    names = set()
    for clause in field.split(","):
        for alt in clause.split("|"):
            m = DEP_NAME.match(alt)
            if m:
                names.add(m.group(1))
    return names


def pagerank(nodes: list[str], edges: dict[str, set[str]], d: float = 0.85, iters: int = 60) -> dict[str, float]:
    """edges[t] = set of s that t depends on; rank flows from dependents to dependencies."""
    n = len(nodes)
    pr = {v: 1.0 / n for v in nodes}
    for _ in range(iters):
        nxt = {v: (1 - d) / n for v in nodes}
        dangling = 0.0
        for v in nodes:
            outs = edges.get(v)
            if outs:
                share = d * pr[v] / len(outs)
                for s in outs:
                    nxt[s] += share
            else:
                dangling += d * pr[v]
        for v in nodes:
            nxt[v] += dangling / n
        pr = nxt
    return pr


def build_debian(label: str) -> pl.DataFrame:
    run = latest("debian")
    sources_txt = read(run / f"{label}_main_source_Sources.xz").decode("utf-8", "replace")
    packages_txt = read(run / f"{label}_main_binary-amd64_Packages.xz").decode("utf-8", "replace")

    bin2src: dict[str, str] = {}
    provides: dict[str, set[str]] = defaultdict(set)
    essential: set[str] = set()
    runtime_deps: dict[str, set[str]] = defaultdict(set)  # src -> binary names it needs
    nbin: dict[str, int] = defaultdict(int)
    build_essential_bins: set[str] = set()

    for p in deb822(packages_txt):
        pkg = p.get("Package")
        if not pkg:
            continue
        src = p.get("Source", pkg).split(" ")[0]
        bin2src[pkg] = src
        nbin[src] += 1
        for v in dep_names(p.get("Provides", "")):
            provides[v].add(src)
        if p.get("Essential") == "yes":
            essential.add(src)
        deps = dep_names(p.get("Depends", "")) | dep_names(p.get("Pre-Depends", ""))
        runtime_deps[src] |= deps
        if pkg == "build-essential":
            build_essential_bins = deps

    def resolve(names: set[str], self_src: str) -> set[str]:
        out = set()
        for n in names:
            if n in bin2src:
                out.add(bin2src[n])
            else:
                out |= provides.get(n, set())
        out.discard(self_src)
        return out

    build_essential = resolve(build_essential_bins, "")
    rt_edges = {s: resolve(d, s) for s, d in runtime_deps.items()}

    rows, bd_edges = [], {}
    for p in deb822(sources_txt):
        src = p.get("Package")
        if not src:
            continue
        bd = (
            dep_names(p.get("Build-Depends", ""))
            | dep_names(p.get("Build-Depends-Arch", ""))
            | dep_names(p.get("Build-Depends-Indep", ""))
        )
        bd_edges[src] = resolve(bd, src)
        rows.append(
            {
                "source": src,
                "version": p.get("Version"),
                "homepage": p.get("Homepage"),
                "section": p.get("Section"),
            }
        )
    meta = pl.DataFrame(rows).unique("source", keep="last")

    rrt, rbd = defaultdict(set), defaultdict(set)
    for t, ss in rt_edges.items():
        for s in ss:
            rrt[s].add(t)
    for t, ss in bd_edges.items():
        for s in ss:
            rbd[s].add(t)

    nodes = sorted(set(meta["source"]) | set(rt_edges) | set(bd_edges))
    pr_rt = pagerank(nodes, rt_edges)
    pr_bd = pagerank(nodes, bd_edges)

    df = pl.DataFrame(
        {
            "source": nodes,
            "n_binaries": [nbin.get(s, 0) for s in nodes],
            "rdeps_runtime": [len(rrt.get(s, ())) for s in nodes],
            "rdeps_build": [len(rbd.get(s, ())) for s in nodes],
            "pagerank_runtime": [pr_rt[s] for s in nodes],
            "pagerank_build": [pr_bd[s] for s in nodes],
            "essential": [s in essential for s in nodes],
            "build_essential": [s in build_essential for s in nodes],
        }
    ).join(meta, on="source", how="left")
    snap = next(e["snapshot"] for e in manifest("debian")["entries"] if e["label"] == label)
    return df.with_columns(
        pct_rank("pagerank_runtime"),
        pct_rank("pagerank_build"),
        pct_rank("rdeps_runtime"),
        pct_rank("rdeps_build"),
        pl.lit(snap).alias("snapshot"),
    ).sort("pagerank_runtime", descending=True)


# --------------------------------------------------------------------------- others

def build_popcon() -> pl.DataFrame:
    run = latest("popcon")
    rows = []
    for line in read(run / "source_by_inst.txt.gz").decode("utf-8", "replace").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 4 or parts[1] == "Not":
            continue
        rows.append({"source": parts[1], "inst": int(parts[2]), "vote": int(parts[3])})
    return pl.DataFrame(rows).with_columns(pct_rank("inst"), pct_rank("vote"))


FAMILY_SUFFIX = re.compile(r"(_\d[\w.]*|_(edge|stable|testing|unstable|current|latest|rolling|sid|tumbleweed|leap\w*|rawhide|devel|backports|main|community|extra|core|ports|xports|aur))+$")


def build_repology() -> pl.DataFrame:
    run = latest("repology")
    rows = []
    for f in sorted(run.glob("projects_p*.json.gz")):
        for proj, pkgs in json.loads(read(f)).items():
            repos = {p["repo"] for p in pkgs}
            fams = {FAMILY_SUFFIX.sub("", r) for r in repos}
            rows.append({"project": proj, "n_repos": len(repos), "n_families_approx": len(fams)})
    return pl.DataFrame(rows).unique("project").with_columns(pct_rank("n_families_approx"))


def build_dockerhub() -> pl.DataFrame:
    run = latest("dockerhub")
    rows = []
    for f in run.glob("library_*.json"):
        for r in json.loads(read(f))["results"]:
            rows.append(
                {
                    "image": r["name"],
                    "pull_count": r["pull_count"],
                    "star_count": r["star_count"],
                    "date_registered": r.get("date_registered"),
                    "status": r.get("status_description"),
                }
            )
    return pl.DataFrame(rows).unique("image").with_columns(pct_rank("pull_count")).sort("pull_count", descending=True)


def build_criticality() -> pl.DataFrame:
    run = latest("criticality_score")
    df = pl.read_csv(io.BytesIO(read(run / "20250725_all.csv.gz")), infer_schema_length=0)
    df = df.select(
        pl.col("repo.url").str.to_lowercase().str.strip_suffix("/").alias("repo_url"),
        pl.col("repo.language").alias("language"),
        pl.col("repo.created_at").alias("repo_created_at"),
        pl.col("default_score").cast(pl.Float64, strict=False).alias("criticality_score"),
        pl.col("depsdev.dependent_count").cast(pl.Int64, strict=False).alias("depsdev_dependents"),
        pl.col("legacy.contributor_count").cast(pl.Int64, strict=False).alias("contributors"),
        pl.col("collection_date"),
    ).unique("repo_url")
    return df.with_columns(pct_rank("criticality_score")).sort("criticality_score", descending=True)


def build_ossfuzz() -> pl.DataFrame:
    run = latest("ossfuzz")
    rows = []
    for name, text in json.loads(read(run / "project_yaml.json.gz")).items():
        try:
            y = yaml.safe_load(text) or {}
        except yaml.YAMLError:
            y = {}
        rows.append(
            {
                "ossfuzz_project": name,
                "main_repo": str(y.get("main_repo") or ""),
                "language": str(y.get("language") or ""),
                "homepage": str(y.get("homepage") or ""),
            }
        )
    return pl.DataFrame(rows)


def build_ecosystems() -> pl.DataFrame:
    run = latest("ecosystems_critical")
    rows = []
    for f in sorted(p for p in run.glob("*.json.gz") if not p.name.startswith("._")):
        for p in json.loads(read(f)):
            rm = p.get("repo_metadata") or {}
            rk = p.get("rankings") or {}
            rows.append(
                {
                    "registry": f.name.rsplit("_p", 1)[0],
                    "name": p["name"],
                    "repository_url": (p.get("repository_url") or "").lower().rstrip("/"),
                    "licenses": p.get("licenses"),
                    "dependent_packages_count": p.get("dependent_packages_count"),
                    "dependent_repos_count": p.get("dependent_repos_count"),
                    "downloads": p.get("downloads"),
                    "downloads_period": p.get("downloads_period"),
                    "docker_dependents_count": p.get("docker_dependents_count"),
                    "rank_dependent_packages": rk.get("dependent_packages_count"),
                    "rank_dependent_repos": rk.get("dependent_repos_count"),
                    "rank_downloads": rk.get("downloads"),
                    "repo_full_name": rm.get("full_name"),
                    "repo_created_at": rm.get("created_at"),
                    "repo_size_kb": rm.get("size"),
                    "repo_archived": rm.get("archived"),
                }
            )
    df = pl.DataFrame(rows, infer_schema_length=None)
    return df.with_columns(
        (pl.col("dependent_packages_count").rank("average").over("registry")
         / pl.col("dependent_packages_count").count().over("registry")).alias("dependent_packages_pct_in_registry")
    )


def main(lenses: list[str] | None = None):
    wanted = set(lenses or [])
    jobs = {
        "debian_pre": lambda: build_debian("pre"),
        "debian_now": lambda: build_debian("now"),
        "popcon": build_popcon,
        "repology": build_repology,
        "dockerhub": build_dockerhub,
        "criticality": build_criticality,
        "ossfuzz": build_ossfuzz,
        "ecosystems": build_ecosystems,
    }
    for name, fn in jobs.items():
        if wanted and name not in wanted:
            continue
        try:
            write(fn(), name)
        except FileNotFoundError as e:
            print(f"skip {name}: {e}")
