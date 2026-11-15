"""Attach every significance signal to every candidate in candidates.yaml.

Writes data/derived/selection/candidate_signals.{parquet,csv}: one row per
candidate project with the raw value and within-lens percentile of each lens,
top-tier flags, and the matched identifiers (so every number can be traced).

Per-package ecosyste.ms lookups are cached under data/raw/ecosystems_packages/.
"""

from __future__ import annotations

import json
import re
import time
from urllib.parse import quote

import httpx
import polars as pl
import yaml

from .. import paths
from .harvest import UA, Recorder, get

CANDIDATES = paths.config_dir() / "selection" / "candidates.yaml"

# Two tiers per lens: T1 ("dominant") and T2 ("high"). Package lenses use
# registry-wide percentiles (top 0.1% / top 1%); Debian lenses use percentiles
# over ~42k source packages (top 0.5% / top 2%); Repology and Docker are
# threshold signals by nature (Repology saturates near ~113 families; there are
# only ~180 Docker official images).
#
# The OpenSSF Criticality Score is reported but deliberately NOT a lens: it is
# built from 2025 commit frequency, contributor counts and issue activity, i.e.
# from the very outcomes this project studies. Selecting on it would select on
# the dependent variable. OSS-Fuzz enrolment is reported as a designation only.
TIERS = {
    #                    T1             T2
    "lib_dependents":   (0.999,         0.99),         # ecosyste.ms dependent packages pct
    "app_dependents":   (0.999,         0.99),         # ecosyste.ms dependent repositories pct
    "downloads":        (0.999,         0.99),         # ecosyste.ms downloads pct
    "container":        (1_000_000_000, 100_000_000),  # Docker official-image pulls
    "container_pkg":    (20_000,        2_000),        # ecosyste.ms docker images containing pkg
    "distro_dependents": (0.995,        0.98),         # Debian PageRank pct (max runtime/build)
    "distro_installs":  (0.995,         0.98),         # Debian popcon installs pct
    "distro_packaging": (100,           70),           # Repology distribution families
    "managed":          (3,             2),            # hyperscalers running it as a managed service
}
# Lenses are grouped into CHANNELS, each an independent route by which other
# software comes to rely on a project. A channel's tier is the max of its lenses,
# so three correlated ecosyste.ms lenses cannot corroborate each other.
CHANNELS = {
    "packages": ["lib_dependents", "app_dependents", "downloads"],  # declared in language package graphs
    "containers": ["container", "container_pkg"],                   # shipped in container images
    "distro_graph": ["distro_dependents"],                          # linked/required by OS packages
    "distro_installs": ["distro_installs"],                         # installed on (Debian) machines
    "distro_packaging": ["distro_packaging"],                       # packaged across OS families
    "managed": ["managed"],                                         # run as a cloud service
}


def tier(value, lens) -> int:
    """2 = T1, 1 = T2, 0 = below."""
    if value is None:
        return 0
    t1, t2 = TIERS[lens]
    return 2 if value >= t1 else 1 if value >= t2 else 0


def load(name: str) -> pl.DataFrame:
    return pl.read_parquet(paths.derived_dir("selection", f"{name}.parquet"))


def match_sources(df: pl.DataFrame, keys: list[str]) -> pl.DataFrame:
    if not keys:
        return df.head(0)
    exact = [k for k in keys if not k.startswith("^")]
    pats = [k for k in keys if k.startswith("^")]
    cond = pl.col("source").is_in(exact)
    for p in pats:
        cond = cond | pl.col("source").str.contains(p)
    return df.filter(cond)


def norm_repo(url: str) -> str:
    u = (url or "").lower().strip().removesuffix(".git").rstrip("/")
    u = re.sub(r"^(git\+)?(https?|git|ssh)://(git@)?", "", u)
    u = u.replace("git@github.com:", "github.com/")
    return u


def fetch_packages(keys: set[str]) -> dict[str, dict | None]:
    cache_dir = paths.raw_dir("ecosystems_packages")
    cached: dict[str, dict | None] = {}
    for run in sorted(cache_dir.glob("*/manifest.json")) if cache_dir.exists() else []:
        for e in json.loads(run.read_text())["entries"]:
            body = paths.resolve_data_file(e["file"]).read_bytes()
            cached[e["key"]] = json.loads(body) if e.get("status") == 200 else None
    missing = sorted(k for k in keys if k not in cached)
    if missing:
        rec = Recorder("ecosystems_packages")
        with httpx.Client(headers={"User-Agent": UA}, timeout=120, follow_redirects=True) as c:
            for k in missing:
                reg, name = k.split(":", 1)
                url = f"https://packages.ecosyste.ms/api/v1/registries/{reg}/packages/{quote(name, safe='')}"
                r = c.get(url)
                if r.status_code == 404:
                    rec.save(re.sub(r"[^\w.-]", "_", k) + ".json", url, b"null", key=k, status=404)
                    cached[k] = None
                else:
                    r = get(c, url)
                    rec.save(re.sub(r"[^\w.-]", "_", k) + ".json", url, r.content, key=k, status=200)
                    cached[k] = r.json()
                print(f"  fetched {k}: {r.status_code}")
                time.sleep(0.5)
        rec.close()
    return cached


def main():
    cands = yaml.safe_load(CANDIDATES.read_text())
    deb_now, deb_pre = load("debian_now"), load("debian_pre")
    popcon, repology = load("popcon"), load("repology")
    docker, crit, fuzz = load("dockerhub"), load("criticality"), load("ossfuzz")

    crit = crit.with_columns(pl.col("repo_url").map_elements(norm_repo, return_dtype=pl.Utf8).alias("key"))
    crit_by = {r["key"]: r for r in crit.iter_rows(named=True)}
    fuzz = fuzz.with_columns(pl.col("main_repo").map_elements(norm_repo, return_dtype=pl.Utf8).alias("key"))
    fuzz_by_repo = {r["key"]: r["ossfuzz_project"] for r in fuzz.iter_rows(named=True)}
    fuzz_names = set(fuzz["ossfuzz_project"])
    docker = docker.with_columns((pl.col("pull_count").rank("average") / pl.len()).alias("pct"))
    dock_by = {r["image"]: r for r in docker.iter_rows(named=True)}
    repo_by = {r["project"]: r for r in repology.iter_rows(named=True)}

    pkg_keys = {k for c in cands for k in c.get("packages", [])}
    pkgs = fetch_packages(pkg_keys)
    eco = load("ecosystems")
    crit_dl_median = {r["registry"]: r["downloads"] for r in
                      eco.group_by("registry").agg(pl.col("downloads").median()).iter_rows(named=True)}

    rows = []
    for c in cands:
        row = {"id": c["id"], "name": c["name"], "layer": c["layer"], "github": c.get("github")}

        for label, deb in (("now", deb_now), ("pre", deb_pre)):
            m = match_sources(deb, c.get("debian", []))
            row[f"debian_sources_{label}"] = ",".join(sorted(m["source"])) or None
            row[f"dist_pr_runtime_pct_{label}"] = m["pagerank_runtime_pct"].max() if m.height else None
            row[f"dist_pr_build_pct_{label}"] = m["pagerank_build_pct"].max() if m.height else None
            row[f"dist_rdeps_runtime_{label}"] = m["rdeps_runtime"].max() if m.height else None
            row[f"dist_rdeps_build_{label}"] = m["rdeps_build"].max() if m.height else None
            row[f"essential_{label}"] = bool(m["essential"].any()) if m.height else None

        pm = match_sources(popcon, c.get("debian", []))
        row["popcon_inst"] = pm["inst"].max() if pm.height else None
        row["popcon_inst_pct"] = pm["inst_pct"].max() if pm.height else None

        rp = repo_by.get(c.get("repology", ""))
        row["repology_families"] = rp["n_families_approx"] if rp else None

        dk = dock_by.get(c.get("docker", ""))
        row["docker_pulls"] = dk["pull_count"] if dk else None
        row["docker_pulls_pct"] = dk["pct"] if dk else None

        best = None
        for k in c.get("packages", []):
            p = pkgs.get(k)
            if not p:
                continue
            rk = p.get("rankings") or {}
            # ecosyste.ms rankings are "top X percent of the registry"; convert to a percentile.
            dep_pct = 1 - (rk.get("dependent_packages_count") or 100) / 100
            repo_pct = 1 - (rk.get("dependent_repos_count") or 100) / 100
            dl_pct = 1 - (rk.get("downloads") or 100) / 100
            cand = {
                "pkg_key": k,
                "pkg_first_release": p.get("first_release_published_at"),
                "pkg_dependent_packages": p.get("dependent_packages_count"),
                "pkg_dependent_repos": p.get("dependent_repos_count"),
                "pkg_docker_dependents": p.get("docker_dependents_count"),
                "pkg_downloads": p.get("downloads"),
                "pkg_dep_pct": dep_pct,
                "pkg_repo_pct": repo_pct,
                "pkg_dl_pct": dl_pct,
                "pkg_critical": p.get("critical"),
            }
            if best is None or max(dep_pct, repo_pct, dl_pct) > max(best["pkg_dep_pct"], best["pkg_repo_pct"], best["pkg_dl_pct"]):
                best = cand
        row.update(best or {"pkg_key": None, "pkg_first_release": None, "pkg_dependent_packages": None,
                             "pkg_dependent_repos": None, "pkg_docker_dependents": None, "pkg_downloads": None,
                             "pkg_dep_pct": None, "pkg_repo_pct": None, "pkg_dl_pct": None, "pkg_critical": None})
        row["packages_mapped"] = ",".join(c.get("packages", [])) or None

        gh = norm_repo("github.com/" + c["github"]) if c.get("github") else None
        cr = crit_by.get(gh) if gh else None
        row["criticality_score"] = cr["criticality_score"] if cr else None
        row["criticality_pct"] = cr["criticality_score_pct"] if cr else None
        row["gh_repo_created"] = cr["repo_created_at"] if cr else None

        fz = c.get("ossfuzz") if c.get("ossfuzz") in fuzz_names else fuzz_by_repo.get(gh or "")
        row["ossfuzz"] = fz

        def dist(label):
            vals = [row[f"dist_pr_runtime_pct_{label}"], row[f"dist_pr_build_pct_{label}"]]
            vals = [v for v in vals if v is not None]
            return max(vals) if vals else None

        row["managed_services"] = c.get("managed", 0)
        # Stale-ranking fallback: ecosyste.ms rankings lag for fast-growing new
        # packages (uv: 127.7M downloads/month but ranked at the 27th percentile on
        # 2026-11-12). If raw downloads reach the median of that registry's
        # critical set, the package is unambiguously in the registry's top 0.1%.
        dl_tier = tier(row["pkg_dl_pct"], "downloads")
        if row["pkg_key"] and row["pkg_downloads"]:
            reg = row["pkg_key"].split(":", 1)[0]
            med = crit_dl_median.get(reg)
            if med and row["pkg_downloads"] >= med:
                dl_tier = max(dl_tier, 2)
        # Debian policy forbids declaring dependencies on Essential packages, so the
        # dependency graph cannot see them; every package depends on them implicitly.
        dist_tier = tier(dist("now"), "distro_dependents")
        if row["essential_now"]:
            dist_tier = 2
        lens = {
            "lib_dependents": tier(row["pkg_dep_pct"], "lib_dependents"),
            "app_dependents": tier(row["pkg_repo_pct"], "app_dependents"),
            "downloads": dl_tier,
            "container": tier(row["docker_pulls"], "container"),
            "container_pkg": tier(row["pkg_docker_dependents"], "container_pkg"),
            "distro_dependents": dist_tier,
            "distro_installs": tier(row["popcon_inst_pct"], "distro_installs"),
            "distro_packaging": tier(row["repology_families"], "distro_packaging"),
            "managed": tier(row["managed_services"] or None, "managed"),
        }
        tiers = {ch: max(lens[l] for l in ls) for ch, ls in CHANNELS.items()}
        for k, v in tiers.items():
            row[f"tier_{k}"] = v
        row["n_t1"] = sum(v == 2 for v in tiers.values())
        row["n_t2plus"] = sum(v >= 1 for v in tiers.values())
        row["points"] = sum(tiers.values())
        row["t1_channels"] = ",".join(k for k, v in tiers.items() if v == 2) or None
        row["t2_channels"] = ",".join(k for k, v in tiers.items() if v == 1) or None
        # Qualification rule ("dominance or breadth"): one dominant channel plus
        # corroboration from a second, independent channel; OR high standing in at
        # least three channels without dominating any (the quiet-engine path:
        # libuv, nghttp2, libsodium).
        row["qualifies_dominance"] = row["n_t1"] >= 1 and row["n_t2plus"] >= 2
        row["qualifies_breadth"] = row["n_t2plus"] >= 3
        row["qualifies"] = row["qualifies_dominance"] or row["qualifies_breadth"]
        # Entrants (first public release 2020 or later) cannot yet be packaged by
        # distributions, so the distro channels lag by years. Lag-adjusted gate:
        # one dominant channel among those that can move fast.
        # Only hand-coded first_release dates count: ecosyste.ms first-release dates
        # start at its own index date (requests shows 2023-08-18) and GitHub
        # creation dates reflect mirrors and moves (valkey-io/valkey was created in
        # 2024 but carries Redis history from 2009).
        first = c.get("first_release")
        row["first_release"] = str(first)[:10] if first else None
        row["entrant"] = bool(first) and str(first)[:4] >= "2020"
        row["qualifies_entrant"] = row["entrant"] and any(
            tiers[ch] == 2 for ch in ("packages", "containers", "managed"))
        row["niche"] = c.get("niche")
        # Pre-ChatGPT anchor (Debian sid on 2022-11-29), for the selection-bias check.
        row["distro_dependents_tier_pre"] = tier(dist("pre"), "distro_dependents")
        rows.append(row)

    df = pl.DataFrame(rows, infer_schema_length=None).sort(["layer", "points"], descending=[False, True])
    df.write_parquet(paths.derived_dir("selection", "candidate_signals.parquet"))
    df.write_csv(paths.published_dir("selection", "candidate_signals.csv"))
    print(f"candidate_signals: {df.height} rows")


if __name__ == "__main__":
    main()
