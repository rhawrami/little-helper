"""Audit the hand-nominated candidate pool against each lens's own top list.

Ties at a top-N cutoff are broken by name so reruns are identical.

1. Coverage: which of each lens's top entries are NOT mapped to any candidate?
   (A long list here means the pool, not the rule, is doing the selecting.)
2. Stability: how well does pre-ChatGPT (2022-11-29) Debian centrality predict
   2026 centrality? (High stability means selecting on 2026 significance is
   close to selecting on pre-period significance.)

Writes data/selection/pool_audit.json (committed) and prints a summary.
"""

from __future__ import annotations

import json
import re
import polars as pl
import yaml

from .. import paths

DER = paths.derived_dir("selection")

# Debian-internal infrastructure is not upstream software; skip it in audits.
DEBIAN_INFRA = re.compile(
    r"^(debhelper|dh-.*|dpkg|debconf|cdebconf|apt|po-debconf|debianutils|init-system-helpers|"
    r"lsb|sensible-utils|base-files|base-passwd|adduser|ucf|lintian|devscripts|.*-defaults|"
    r"debian-.*|tasksel|installation-report|haskell-devscripts|gem2deb|pkg-.*|javahelper|maven-debian-helper|"
    r"libtext-.*-perl|liblocale-gettext-perl|netbase|tzdata|mime-support|media-types|"
    r"ca-certificates|shared-mime-info|.*-keyring)$"
)


def main():
    cands = yaml.safe_load((paths.config_dir() / "selection" / "candidates.yaml").read_text())
    known = set()
    deb_pats = []
    for c in cands:
        known |= {c["id"].lower(), c.get("repology", "") or "", c.get("docker", "") or ""}
        for k in c.get("packages", []):
            known.add(k.split(":", 1)[1].lower())
        for d in c.get("debian", []):
            (deb_pats if d.startswith("^") else known.add(d) or []).append(d) if d.startswith("^") else known.add(d)
    deb_re = re.compile("|".join(p for p in deb_pats))

    def covered(name: str) -> bool:
        n = name.lower()
        return n in known or bool(deb_re.match(n))

    audit = {}
    deb = pl.read_parquet(DER / "debian_now.parquet")
    deb = deb.filter(~pl.col("source").str.contains(DEBIAN_INFRA.pattern))
    for col in ["pagerank_runtime", "pagerank_build"]:
        top = deb.sort([col, "source"], descending=[True, False]).head(100)["source"].to_list()
        audit[f"debian_{col}_top100_missing"] = [s for s in top if not covered(s)]
    pop = pl.read_parquet(DER / "popcon.parquet").filter(~pl.col("source").str.contains(DEBIAN_INFRA.pattern))
    audit["popcon_top100_missing"] = [s for s in pop.sort(["inst", "source"], descending=[True, False]).head(100)["source"] if not covered(s)]
    rep = pl.read_parquet(DER / "repology.parquet").sort(["n_families_approx", "project"], descending=[True, False]).head(100)
    audit["repology_top100_missing"] = [s for s in rep["project"] if not covered(s)]
    dock = pl.read_parquet(DER / "dockerhub.parquet").head(50)
    audit["docker_top50_missing"] = [s for s in dock["image"] if not covered(s)]
    eco = pl.read_parquet(DER / "ecosystems.parquet")
    audit["ecosystems_top15_per_registry_missing"] = {
        reg: [n for n in g.sort(["dependent_packages_count", "name"], descending=[True, False]).head(15)["name"] if not covered(n)]
        for reg, g in sorted(eco.group_by("registry"), key=lambda t: str(t[0]))
        for reg in [reg[0] if isinstance(reg, tuple) else reg]
    }

    # stability of Debian runtime centrality across the ChatGPT boundary
    pre = pl.read_parquet(DER / "debian_pre.parquet").select("source", pl.col("pagerank_runtime").alias("pre"))
    now = pl.read_parquet(DER / "debian_now.parquet").select("source", pl.col("pagerank_runtime").alias("now"))
    j = pre.join(now, on="source").with_columns(
        pl.col("pre").rank().alias("r_pre"), pl.col("now").rank().alias("r_now"))
    rho = j.select(pl.corr("r_pre", "r_now")).item()
    top_pre = set(j.sort(["pre", "source"], descending=[True, False]).head(400)["source"])
    top_now = set(j.sort(["now", "source"], descending=[True, False]).head(400)["source"])
    audit["debian_runtime_spearman_2022_vs_2026"] = round(rho, 4)
    audit["debian_runtime_top400_overlap_2022_vs_2026"] = round(len(top_pre & top_now) / 400, 4)
    audit["debian_sources_pre"] = pre.height
    audit["debian_sources_now"] = now.height

    paths.published_dir("selection", "pool_audit.json").write_text(json.dumps(audit, indent=2))
    for k, v in audit.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
