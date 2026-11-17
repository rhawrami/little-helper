# little-helper
Looking at open source software progress

little-helper is a project for studying the impacts of large language models on open source software. It's quite clear that AI has significantly increased the amount of code online, especially open source code. In this project, though, we're focusing on existing, fundamental software libraries that power several open and closed source applications. For instance, we aren't going to look at some random user's GitHub repository that they started five years ago and is a Python statistical plotting library, and the accelerated commits they've recently made; we'd rather look at libraries like matplotlib or plotly or d3. Better yet, we'd like to look at the "systems" software that powers even the largest companies, like PostgreSQL or ffmpeg.

We identify those projects, clone their repositories, and track their progression from inception to now: commits, change proposals (accepted, rejected and pending), issues, diff size and breadth, review, contributor concentration, AI policies and visible AI markers. Projects are not limited to GitHub. A project hosted on a mailing list, GitLab, Gerrit or Forgejo is included when it passes the significance gate, and the data we can collect depends on where its review happens ([data regimes A–E](docs/sample_selection.md)).

Later down the line, we'd like to also do things like measure the efficiency gains/benchmarks for these projects over time with each added commit, or more likely small sets of commits. This is harder to do, though, and the first part of the analysis will be more than enough work to start with.

The setup stays simple: Python managed with uv, httpx for the GitHub GraphQL API (and other forges' APIs later), polars for data wrangling, and plotly for visualization. Everything is recreatable and timestamped: every downloaded file is listed in a manifest with its URL, retrieval time and sha256.

## Documents

- [Literature review](docs/literature_review.md), with the research notes behind it in [docs/research_notes/](docs/research_notes/)
- [Sample selection](docs/sample_selection.md): how projects qualify, the 50-project pilot and its data regimes
- [Data collection plan](docs/data_collection_plan.md): sources, costs, storage, the rolling git mode, what is built

## Setup

```bash
uv sync
uv run lh info
```

`lh info` shows where data will go, the free space there, whether object storage is on, and whether a GitHub token is available. The token comes from `GITHUB_TOKEN`, a token file (`github_token_file` in `config/local.yaml`), or the `gh` CLI if you are logged in (`gh auth login`).

**Running on a server:** the long collection runs on a DigitalOcean droplet with a Spaces bucket as the store of record. Setup, starting and monitoring the collection are in [deploy/README.md](deploy/README.md).

### Where data lives

| Variable | What | Default |
|---|---|---|
| `LH_DATA_DIR` | raw downloads, git extracts, canonical tables. Point it at the external drive. | `./data` |
| `LH_WORK_DIR` | temporary bare clones, deleted after extraction. Keep it on the internal disk. | `~/.cache/little-helper/work` |
| `LH_MANIFEST_DIR` | run manifests (small, committed) | `./data/manifests` |
| `LH_S3_BUCKET` | optional object storage (DigitalOcean Spaces or any S3). When set, every committed file is uploaded and verified, and heavy files then leave the local disk. See [deploy/README.md](deploy/README.md#settings). | off |

Each can instead be set in `config/local.yaml` (machine-specific, not committed): `data_dir`, `work_dir`, `manifest_dir`, `s3_bucket` and so on.

With the USB drive formatted as exFAT (readable and writable on both macOS and Fedora):

```bash
export LH_DATA_DIR=/Volumes/<drive>/little-helper        # macOS
export LH_DATA_DIR=/run/media/$USER/<drive>/little-helper   # Fedora
```

Add the line to your shell profile. If the variable points at the drive and the drive is not mounted, `lh` refuses to run rather than writing to the internal disk. To move the selection data already collected on this Mac to the drive:

```bash
rsync -a data/raw data/derived "$LH_DATA_DIR/"
```

Keep a second copy of `$LH_DATA_DIR/raw/` somewhere other than the drive: raw API pages cannot be downloaded again as they were.

## Collecting data

Projects are configured in `config/projects/<id>.yaml`, generated from the pilot by `lh selection export`. Named sets live in `config/study.yaml`; `slice` is 20 projects spanning every data regime, to run before the full census.

```bash
uv run lh projects --set slice          # what will be collected
uv run lh collect git --set slice       # clone -> extract -> delete; ~10.6 GB downloaded, minutes per repo
uv run lh normalize git --set slice     # canonical commits, commit_files, trailers, refs, trees, policy_files, ai_markers
uv run lh collect github --set slice    # PRs and issues; ~190k PRs and ~65k issues, about 17–21 hours
uv run lh normalize github --set slice  # canonical change_proposals, cp_*, issues, issue_*, gh_ai_markers
uv run lh status --set slice           # progress, and time left for PRs and issues separately
uv run lh sync check|push|pull         # object storage: test access, upload local data, fetch cursors
```

- **Interrupting is safe.** Ctrl-C, a crash or a sleeping laptop loses at most the open chunk of pages. Run the same command again to resume. Already-extracted git repos are skipped (use `--force` to redo them).
- **Long runs:** keep the Mac awake with `caffeinate -i uv run lh collect github --set slice`. On the droplet a systemd user service runs the collection and restarts it after failures ([deploy/README.md](deploy/README.md)).
- **A finished GitHub repo** is refreshed on the next run: only items updated since the last pass are fetched.
- **The GitHub collector sends one request at a time,** as GitHub's API guidance asks. Measured on the slice: 10–13k PRs and about 40k issues an hour.

Canonical tables are partitioned parquet files: `$LH_DATA_DIR/canonical/<table>/project=<id>/part-0.parquet`. Read all projects at once with polars (`pl.scan_parquet(".../canonical/commits/*/*.parquet", hive_partitioning=True)`) or DuckDB.

## Sample selection

```bash
uv run lh selection rebuild    # re-run the offline steps from archived raw files
uv run lh selection export     # regenerate config/projects/*.yaml
```

The full sequence (harvest → signals → score → audit → probe → pilot → render → export) is in [sample_selection.md §11](docs/sample_selection.md#11-reproduce).

## Repository layout

```
config/        study.yaml, selection/ (candidates, pilot, verification), projects/<id>.yaml
deploy/        droplet setup: bootstrap.sh, the systemd service, local.yaml template, guide
docs/          design documents, literature review, research notes
src/little_helper/
  cli.py       the `lh` command
  objects.py   object storage: upload and verify on commit, read back on demand
  collect/     git (rolling clone/extract/delete) and github (GraphQL) collectors: write raw only
  normalize/   raw -> canonical tables
  classify/    path rules (test/docs/vendored/generated/CI/build), bots, trailers, AI markers
  selection/   the sample-selection pipeline
  explore/     exploratory views (lh plot)
tests/         `uv run pytest` (a tiny git repo, a fake GraphQL server and an in-memory S3; no network)
data/          committed provenance only: manifests/ and selection/ outputs
```
