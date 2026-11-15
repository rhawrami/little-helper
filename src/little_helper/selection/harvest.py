"""Harvest raw candidate-nomination sources for sample selection.

Every response is written verbatim (gzipped where large) under
$LH_DATA_DIR/raw/<source>/<run_id>/ and recorded in a run manifest with its URL,
UTC retrieval time, byte count and sha256. Nothing here interprets data;
see signals.py for that.

Usage:
    uv run lh selection harvest                  # all sources
    uv run lh selection harvest debian popcon    # a subset
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
import httpx

from .. import paths

UA = "oss-research-client/0.1"
RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# Debian snapshot timestamps: one just before ChatGPT's release (2022-11-30)
# and one at harvest time. Both use sid so packaging conventions match.
DEBIAN_SNAPSHOTS = {"pre": "20221129T000000Z", "now": "20261111T000000Z"}

ECOSYSTEMS_REGISTRIES = [
    "pypi.org",
    "npmjs.org",
    "crates.io",
    "repo1.maven.org",
    "proxy.golang.org",
    "rubygems.org",
    "nuget.org",
    "packagist.org",
]

REPOLOGY_MIN_FAMILIES = 30


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Recorder:
    def __init__(self, source: str):
        self.source = source
        self.dir = paths.raw_dir(source, RUN_ID)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[dict] = []

    def save(self, name: str, url: str, content: bytes, compress: bool = False, **extra):
        path = self.dir / (name + (".gz" if compress else ""))
        data = gzip.compress(content) if compress else content
        path.write_bytes(data)
        self.entries.append(
            {
                "url": url,
                "file": paths.relative_to_data(path),
                "retrieved_at": utcnow(),
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                **extra,
            }
        )

    def close(self):
        manifests = paths.manifest_dir()
        manifests.mkdir(parents=True, exist_ok=True)
        manifest = {"source": self.source, "run_id": RUN_ID, "entries": self.entries}
        (self.dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        (manifests / f"{self.source}_{RUN_ID}.json").write_text(json.dumps(manifest, indent=2))
        print(f"[{self.source}] {len(self.entries)} files -> {self.dir}")


def client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": UA}, timeout=httpx.Timeout(120.0), follow_redirects=True
    )


def get(c: httpx.Client, url: str, tries: int = 5, **kw) -> httpx.Response:
    for attempt in range(tries):
        try:
            r = c.get(url, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                wait = int(r.headers.get("retry-after", 10 * (attempt + 1)))
                print(f"  {r.status_code} on {url}; sleeping {wait}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except httpx.TransportError as e:
            print(f"  transport error {e!r}; retrying")
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"failed after {tries} tries: {url}")


def harvest_ecosystems():
    rec = Recorder("ecosystems_critical")
    with client() as c:
        for reg in ECOSYSTEMS_REGISTRIES:
            page = 1
            while True:
                url = (
                    f"https://packages.ecosyste.ms/api/v1/registries/{reg}/packages"
                    f"?critical=true&per_page=100&page={page}"
                )
                r = get(c, url)
                rows = r.json()
                if not rows:
                    break
                rec.save(f"{reg}_p{page:03d}.json", url, r.content, compress=True, registry=reg, page=page)
                print(f"  {reg} page {page}: {len(rows)}")
                page += 1
                time.sleep(0.5)
    rec.close()


def harvest_debian():
    rec = Recorder("debian")
    with client() as c:
        for label, ts in DEBIAN_SNAPSHOTS.items():
            base = f"https://snapshot.debian.org/archive/debian/{ts}/dists/sid"
            for rel in ["Release", "main/source/Sources.xz", "main/binary-amd64/Packages.xz"]:
                url = f"{base}/{rel}"
                r = get(c, url)
                name = f"{label}_{rel.replace('/', '_')}"
                rec.save(name, url, r.content, snapshot=ts, label=label)
                print(f"  {label} {rel}: {len(r.content):,} bytes")
                time.sleep(2)
    rec.close()


def harvest_popcon():
    rec = Recorder("popcon")
    with client() as c:
        url = "https://popcon.debian.org/source/by_inst"
        r = get(c, url)
        rec.save("source_by_inst.txt", url, r.content, compress=True)
    rec.close()


def harvest_repology():
    rec = Recorder("repology")
    with client() as c:
        start, page = "", 1
        while True:
            url = f"https://repology.org/api/v1/projects/{start + '/' if start else ''}?families={REPOLOGY_MIN_FAMILIES}-"
            r = get(c, url)
            data = r.json()
            names = sorted(data)
            if start:
                names = [n for n in names if n != start]
            if not names:
                break
            rec.save(f"projects_p{page:03d}.json", url, r.content, compress=True, page=page)
            print(f"  page {page}: {len(names)} projects, last={names[-1]}")
            if len(data) < 200:
                break
            start, page = names[-1], page + 1
            time.sleep(1.5)  # repology asks for <= 1 req/s
    rec.close()


def harvest_dockerhub():
    rec = Recorder("dockerhub")
    # Anonymous clients get 403 on page 2 (checked 2026-11-12), so fetch page 1
    # in both orderings; with ~181 official images that covers all of them.
    with client() as c:
        for order in ["pull_count", "-pull_count"]:
            url = f"https://hub.docker.com/v2/repositories/library/?page_size=100&page=1&ordering={order}"
            r = get(c, url)
            rec.save(f"library_{order.replace('-', 'asc_') or 'desc'}.json", url, r.content, ordering=order)
            time.sleep(1)
    rec.close()


def harvest_criticality():
    rec = Recorder("criticality_score")
    with client() as c:
        # The OpenSSF GCS bucket refuses downloads (billing disabled, checked 2026-11-12);
        # the project's repo carries the 2025-07-25 snapshot instead.
        path = "data/20250725_all.csv.gz"
        meta = get(c, f"https://api.github.com/repos/ossf/criticality_score/contents/{path}").json()
        url = meta["download_url"]
        r = get(c, url)
        content = gzip.decompress(r.content)
        rec.save("20250725_all.csv", url, content, compress=True, git_sha=meta["sha"])
    rec.close()


def harvest_ossfuzz():
    rec = Recorder("ossfuzz")
    work = rec.dir / "oss-fuzz"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
         "https://github.com/google/oss-fuzz.git", str(work)],
        check=True, capture_output=True,
    )
    subprocess.run(["git", "-C", str(work), "sparse-checkout", "set", "--no-cone", "/projects/*/project.yaml"],
                   check=True, capture_output=True)
    head = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    projects = {}
    for y in sorted((work / "projects").glob("*/project.yaml")):
        projects[y.parent.name] = y.read_text(errors="replace")
    content = json.dumps(projects, indent=0).encode()
    rec.save("project_yaml.json", "https://github.com/google/oss-fuzz", content, compress=True, commit=head)
    subprocess.run(["rm", "-rf", str(work)], check=True)
    rec.close()


SOURCES = {
    "debian": harvest_debian,
    "popcon": harvest_popcon,
    "dockerhub": harvest_dockerhub,
    "criticality": harvest_criticality,
    "ossfuzz": harvest_ossfuzz,
    "repology": harvest_repology,
    "ecosystems": harvest_ecosystems,
}

def main(wanted: list[str] | None = None):
    wanted = wanted or list(SOURCES)
    print(f"run {RUN_ID}: {wanted}")
    for name in wanted:
        try:
            SOURCES[name]()
        except Exception as e:  # keep going; record failure loudly
            print(f"!! {name} failed: {e!r}")
