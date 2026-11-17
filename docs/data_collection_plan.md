# Data collection plan: ~1,000 projects

Status: 2026-11-14. Built: the `lh` package and CLI (§6), rolling git collection (§3.1a), GitHub PR and issue collection (§3.2), and normalizers for both (see the README for commands). Not built yet: other forges, external trackers, vulnerabilities, linkers, metrics, git refresh by shallow window, and blobless mode for Chromium (§9). All costs and sizes below were **measured** on real repositories and APIs on 2026-11-13/14 unless marked as an estimate. The measurements are described in section 9.

## 1. Bottom line

- **Pull history from git, not from APIs.** Commits, diff sizes, file breadth, test-to-code share, trailers (`Reviewed-by`, `Co-authored-by`, `Assisted-by`), tags, AI-policy and `AGENTS.md` adoption dates, and truck factor all come from local bare clones. That is one fetch per repository and no rate limits.
- **Use APIs only for what git doesn't have:** change proposals (PRs, MRs, Gerrit changes) with their reviews, comments and events, and issues. For regimes A–C, GitHub GraphQL is the workhorse. Points are not the limit; server response time is. A page of 25 PRs with reviews, comments, commits, files, labels and timeline events takes 4–7 s and 1–2 points, so one token collects **about 12–20k PRs an hour** and 55–70k issues an hour (measured 2026-11-14). Stored raw, that is under 1 KB per item. The full census needs about **two weeks of continuous collection** on one token, run serially as GitHub's API guidance asks.
- **Storage: run git in rolling mode, and the census fits on this Mac.** Each repo is cloned, its tables are extracted, and the clone is deleted (§3.1a). Clones are 70–75% of a keep-everything build, and the tables we keep from them are about 4.5% of clone size, as measured on curl and NumPy. Kept data comes to **≈20 GB lean and ≈28 GB likely**, and the peak working space is the largest clone in flight (≈20 GB for Kibana, ≈7 GB without giants). This Mac has 45 GiB free. Keeping every clone instead needs 200–550 GB and an external drive (§5.2). A backup of `raw/` belongs off this machine either way.
- **Organize the code as one small Python package** with a CLI, one adapter per source and three data layers: immutable raw responses, rebuildable canonical tables, and derived metrics. The data directory lives outside the git repo (`LH_DATA_DIR`), and only manifests and small outputs are committed.

## 2. What we collect, and from where

| Measure | Source | Regimes | Notes |
|---|---|---|---|
| Commits (counts, authors, timing) | local git clone | all | author and committer timestamps with offsets; `.mailmap`; bot flags; first-parent vs all |
| Diff size (lines, files) | git `--numstat` (commits); platform API (PRs) | all / A–C | exclude vendored, generated and lock files per project |
| Diff breadth: spatial (modules touched, entropy) | git | all | top-level-directory and module maps per project |
| Diff breadth: kind (feature, fix, **perf**, refactor, test, docs, build, deps, security, revert) | commit messages, PR titles, labels, paths | all | rules first, then a classifier validated on hand labels; GSO/SWE-Perf/SWE-fficiency provide labelled perf commits |
| Test-to-code share | git (commits); PR file lists via API | all / A–C | path rules per ecosystem (`tests/`, `*_test.go`, `__tests__`, `spec/`) plus overrides |
| Change proposals: accepted / rejected / withdrawn / superseded / pending | GitHub, GitLab, Gerrit, Forgejo APIs, **linked to commits** | **A–C only** (decided) | the merged flag is not reliable (sample_selection.md §8.4); per-project linkers |
| Review rounds, reviewer count | review events, force-push events, Gerrit patch sets, GitLab MR versions; `Reviewed-by`/`Acked-by` trailers | A–C; trailers for D | for D, reviewer counts exist only for *accepted* changes |
| PR and issue description length | API bodies (template text stripped); commit-message length | A–C; messages all | PR-template adoption is itself a dated break |
| Issues | GitHub/GitLab/Forgejo issues, Jira, Bugzilla, Trac | all where public | ASF Bugzilla now requires a login (account needed) |
| Truck factor / contribution concentration | git (degree-of-authorship from commit history, per year) | all | no `git blame` needed |
| AI-policy adoption; `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `copilot-instructions.md` | git history of those files plus CONTRIBUTING keyword history; hand check | all | dated project events for event studies |
| AI markers (bots, trailers, branch prefixes, PR-body signatures) | git plus API | all / A–C | lower bounds; disclosure rules differ by project |
| Security fixes, CVEs per release | OSV.dev bulk export, GitHub Advisory DB; `CVE-` references in commits and release notes; tags | all | model CNA changes (e.g. the Linux kernel assigning CVEs itself since Feb 2024) |
| Releases | git tags; GitHub/GitLab release objects | all | |

Two things we deliberately don't collect:

- **Mailing-list archives**, by decision for regime D. Accepted/rejected/pending is restricted to A–C, and D gets commits, issues and reviewer trailers.
- **GH Archive.** The platform APIs return full history for PRs and issues, and downloading GH Archive locally would mean multiple TB. It stays a fallback for events the APIs no longer expose; querying it in BigQuery would need a GCP account.

## 3. Collection strategy by source

### 3.1 Git (all ~1,000 projects)

- **What.** A bare clone of each repo's branches and tags (`git clone --bare`), then periodic `git fetch`. Do *not* mirror-clone (`--mirror` pulls every `refs/pull/*`).
- **Measured on NumPy:**
  - The bare clone is 203 MB (GitHub reports 183 MB), about 1.1× GitHub's `diskUsage`. It took 67 s.
  - Fetching every PR head (`refs/pull/*`) grew it to 500 MB, or 324 MB after `git repack`, about 1.8× `diskUsage`. That is what makes rejected PRs' code available locally.
  - **Recommendation:** don't fetch PR refs by default. Get PR-level file lists from the API instead (`files(first:100)` on the PR query), and fetch PR refs only for projects or analyses that need the code of rejected PRs.
- **Extraction.** On NumPy, `git log --all --numstat` (75k commits including PR heads) took 17 s.
  - Commits table: **~95 bytes per commit**, about 100 B with the message, zstd parquet.
  - File-change table: **~13 bytes per row**, 2.3 rows per commit.
  - At census scale (~15–20M commits) that is 2–5 GB in total. Extraction is CPU-light: hours, not days.
- **Throughput.** Cloning is bound by network and GitHub-side pack generation; we measured ~3 MB/s on one stream. With 4 parallel clones, a ~150 GB initial fetch takes roughly 4–8 hours; Chromium alone (67 GB) adds hours. Re-fetches are incremental and fast.

### 3.1a Rolling mode (default on this Mac)

Each repo goes through **clone → extract → verify → delete**, so only a few clones exist at any moment. The full ~245 GB still passes through the network, but it never sits on disk at once.

**What we keep from each clone**, all written before the clone is deleted:

- **Commits** with full messages, so trailers and `CVE-` references can be re-parsed later without the clone.
- **File changes** (path, lines added and deleted, change type).
- **Tags, and every ref with its commit ID at clone time.**
- **Yearly (or quarterly) tree listings** of the default branch with file sizes (`git ls-tree -r -l`). These give codebase size and test share by path over time without a checkout.
- **Every version of the policy and governance files:** `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `copilot-instructions.md`, CONTRIBUTING, CODEOWNERS, MAINTAINERS, SECURITY and PR templates.
- **Optionally, per-PR diff stats** from transient PR refs (below).

**Measured 2026-11-14:**

| | curl | NumPy |
|---|---|---|
| Bare clone | 138 MB, 40 s | 203 MB, 53 s |
| Kept tables (commits + file changes, zstd parquet) | 6.2 MB (4.5%) | 8.8 MB (4.3%) |
| Full diff text of all history, zstd -19 --long | 21 MB (15%) | 31 MB (15%) |
| Blobless clone (commits and trees, no file contents) | 43 MB (31%) | 47 MB (23%) |
| One-month shallow clone (for refreshes) | 7.4 MB, 4 s, 367 commits | — |
| Yearly tree listings, 2000–2026 | 0.2 MB | — |

**Peak disk.** It is the clones in flight, not the census:

- Clones over 2 GB run alone; the rest run 4 at a time.
- The largest clone is Kibana (≈20 GB) or WebKit (≈14 GB), or the Linux kernel (≈7 GB) if no giants pass the gate.
- Run the biggest repos first, while little else is on disk.

**PR refs become affordable.**

- Fetch `refs/pull/*/head`, compute every PR's file list and line counts against its base, including rejected PRs, then delete.
- This costs download, not disk. On NumPy it added 297 MB to a 203 MB clone, so expect a few extra hours over the census.
- It could replace `files(first:100)` in the PR query.
- Repos over ~5 GB grow too large with their PR refs, so they keep the API file lists.

**Refreshes without a stored clone.**

- Use a shallow clone that starts a few weeks before the last cut-off (`--shallow-since`). Skip commits already in the tables.
- Drop boundary commits, whose diffs would be computed against nothing.
- If a new commit's parent is in neither the tables nor the window (an old branch merged recently), deepen and retry.
- Measured on curl: the last month was 7.4 MB and 4 s, against 138 MB for a full clone.

**What deletion costs:**

- **The git fields are fixed when the clone is deleted.** Adding one means another pass over the census: the same download, ~4–8 h plus giants. The extractor carries a version number, and every table records it.
- **Code-level work needs the code again.** This covers diff text for classifying perf changes, line survival, and phase-2 builds.
  - Keeping all diff text would be ~15% of clone size (≈35 GB likely), which doesn't fit next to everything else.
  - Instead, re-clone the subset an analysis needs, or keep diff text only for chosen projects. The 15% figure holds for curl and NumPy; repos with large generated text files would be higher.
- **A later re-clone may not reproduce the tables.** Branches get deleted, and history is occasionally rewritten. The tables plus the recorded refs are the record of what we saw; a re-clone checks those commit IDs and flags any that are gone.

**Chromium doesn't fit even alone** (67 GB). Two options:

- **A blobless clone** gives every commit's file list without downloading file contents. On curl, `git log --raw` ran with lazy fetching disabled and needed no downloads. Gerrit supplies line counts per change. Chromium's blobless size is unmeasured; at curl's and NumPy's ratios it would be 15–21 GB.
- **Leave it until a drive is available**, if it passes the gate at all.

### 3.2 GitHub GraphQL (regimes A and B, ~80% of the census)

- **One PR query per page of 50.** Each page carries title, body, state, dates, author, merger, additions/deletions/changed files, labels, reviews (state, author, time, body), comments, review-thread count, commit SHAs and timeline events. The events are force-pushes (for review rounds), closed-by-commit, merged, reopened, ready-for-review, review-requested and cross-references.
- **Measured on 5 repos, 50 PRs per page:** **3 points per page**, 1.8–7.1 KB per PR (mean 4.5 KB), and 4.6× gzip, so about **1 KB per PR stored**. Issues at 100 per page also cost 3 points, at 2.7–11 KB per issue (mean 6.1 KB) and 3.5× gzip, about 1.7 KB per issue.
- **Points are cheap because GitHub charges per sub-request, not per item:** a page of 50 PRs with six nested connections is about 300 sub-requests, which is 3 points. The binding limits are therefore 5,000 points/hour, response time (2–4 s per page), and the 10-second query timeout on heavy pages. Shrink pages adaptively for repos like Kubernetes.
- **Truncation.** Nested connections are capped (50 reviews and 50 comments per PR in this query). PRs that hit a cap get follow-up pagination; budget about +15% for this.
- **Incremental updates.** Order by `UPDATED_AT` and keep a per-repo cursor, so re-runs fetch only what changed.
- **Accounts.** Use one authenticated token (`gh auth token`). Do not spread collection across multiple accounts to evade rate limits; GitHub's terms forbid it.

### 3.3 Other forges (regime C)

- **GitLab** instances (gitlab.gnome.org, gitlab.freedesktop.org, gitlab.kitware.com, gitlab.com): MRs, notes, approvals, versions (= review rounds), issues. Anonymous read works; a token raises limits.
- **Gerrit** (go-review, chromium-review, review.qt.io, …): `/changes/` with `o=DETAILED_ACCOUNTS&o=MESSAGES&o=ALL_REVISIONS`. Patch-set count gives review rounds directly. **Chromium is the outlier**: millions of changes. If it enters the census, cap its review data to a window or a sample. Commits and git-derived measures stay complete.
- **Forgejo** (code.ffmpeg.org, codeberg.org): its API is close to Gitea/GitHub REST.

### 3.4 External issue trackers

These are Jira (issues.apache.org, bugs.openjdk.org, unicode-org.atlassian.net), Bugzilla (sourceware, kernel.org, mindrot, bz.apache.org) and Trac (code.djangoproject.com). Volumes are small (≈0.3–0.5M issues in total). Each needs its own adapter.

Access problems already seen:

- **ASF Bugzilla requires a login.** We need an account, or we drop httpd's pre-GitHub bugs.
- **Anubis bot walls** on several wikis and Trac sites. Use APIs and exports, never scraping around them.

### 3.5 Vulnerabilities

Use the OSV.dev bulk export (all ecosystems, a zip per ecosystem) and the GitHub Advisory Database (a git repo), joined to projects through package names and repo URLs. `CVE-` references in commit messages, release notes and tags give per-release counts for projects outside package ecosystems (kernel, glibc, OpenSSH).

### 3.6 Selection sources (re-run at census scale)

These are the existing harvesters (`selection/harvest.py`), extended:

- top-N nomination per lens, with per-registry caps
- per-package lookups
- a possible HTTP Archive channel for browser libraries
- a sourced managed-service table

About 0.2–1 GB per snapshot.

## 4. Time budget (estimates from the measurements above)

| Step | Volume (census) | Rate | Wall clock |
|---|---|---|---|
| Initial clones | 135–250 GB | ~1.3–3 MB/s per stream (curl, git, NumPy), 4 streams | 4–8 h (+ Chromium) |
| Git extraction | 15–20M commits | ~4,400 commits/s/core (NumPy) | 1–3 h |
| GitHub PRs | ~4–4.5M PRs | 12–20k PRs/h (25 per page, 4–7 s per page) | ~9–14 days |
| GitHub issues | ~2.6–2.9M issues | 55–70k issues/h (50 per page, ~3 s) | ~2 days |
| Overflow pagination | +15% | included in the zlib rate (11.7k PRs/h) | |
| Other forges + trackers | ~0.5–1M items | per-instance limits | 1–2 days, in parallel with GitHub |
| Vulnerability data | bulk downloads | | < 1 h |

Rates measured 2026-11-14 on flask, NumPy, Vite and zlib. My earlier estimate (~3 days for PRs) assumed pages of 50 at 2–4 s. Pages of 50 with per-PR file lists time out (HTTP 502), and the binding limit is server response time, not the 5,000 points/hour: 25 PRs per page cost only 1–2 points. Parallel requests on one token would be faster, but GitHub's best practices ask clients to send one request at a time, so the collector is serial.

So the initial build is about **two weeks**, dominated by GitHub PRs, with git and everything else running alongside. Git collection for the whole census finishes in the first day. Refreshes after that only fetch what changed (§3.2) and take hours.

## 5. Storage estimate

Basis (measured 2026-11-13/14):

- **133 candidate repos:** 70.5 GB of GitHub `diskUsage`, 1.87M PRs, 1.22M issues, 7.1M commits. The top 10 repos hold 42% of the disk.
- **A random sample of 150 repos behind ecosyste.ms "critical" packages** (≥1 MB): per repo, a mean of 50 MB disk (median 3.9 MB), 2,113 PRs (median 425), 1,292 issues and 4,889 commits. Scaled to ~1,050 tail repos, that is ≈ 52 GB, 2.2M PRs, 1.36M issues, 5.1M commits.
- **Giants that may pass the gate:**

  | Repo | `diskUsage` | Review on GitHub? |
  |---|---|---|
  | Chromium | 67 GB | no (Gerrit) |
  | Kibana | 18 GB | yes, 203k PRs |
  | WebKit | 13 GB | yes, 81k PRs |
  | LibreOffice | 7 GB | no (Gerrit) |
  | Firefox (gecko-dev) | 6 GB | no |

### 5.1 Rolling mode (default)

| Component | Lean | Likely | Basis |
|---|---|---|---|
| Clones in flight (transient peak) | ≈7 GB | ≈20 GB | largest clone ×1.1 (Linux; Kibana); scheduled first |
| Git-derived tables | 3 GB | 4–5 GB | ≈4.5% of clone size (curl, NumPy) |
| GitHub raw, zstd per repo | 8 GB | 11 GB | 600 B/PR measured on NumPy (760 B as per-page gzip), 1.7 KB/issue ×0.8 |
| Other forges and trackers raw | 2 GB | 3 GB | Chromium Gerrit capped |
| Vulnerability and selection data | 2 GB | 3 GB | OSV and GHSA extracted, not kept whole; one selection snapshot is 0.3 GB today |
| Canonical tables (long text stays in raw) | 2 GB | 3 GB | text-free PR tables measured at 190 B/PR, about a third of raw |
| Derived metrics | 2 GB | 3 GB | |
| **Kept at the end** | **≈20 GB** | **≈28 GB** | |

This fits in the Mac's 45 GiB free and leaves about 15–20 GB for the system. The clone peak comes early, before API data accumulates.

Raw API pages are worth backing up off the machine: they are the frozen record and can't be re-fetched as they were. The backup can go to a cheap external disk or cloud storage, since no git runs on it. After the backup, the local copy of `raw/` can be deleted for projects that are already normalized, bringing local use to ≈15 GB.

**Since 2026-11-16 the run moves to a DigitalOcean droplet (60 GB disk) with a Spaces bucket** ([deploy/README.md](../deploy/README.md)). The bucket is the store of record. Every committed file is uploaded and verified there, and heavy files then leave the local disk, so the droplet holds only the clone in flight and bookkeeping. That leaves room for the ≈20 GB Kibana clone peak. Measured on the slice so far: 941k commits extract to 0.15 GB, and 80k PRs plus 33k issues of raw pages take 0.12 GB. The slice starts over on the droplet. The Mac's partial run (all 20 git extracts, 80k PRs, 33k issues) stays on the USB drive as the pilot record.

Doing the same with raw API pages saves little. A GraphQL page already holds only the fields we asked for. A parsed table with all text is 705 B/PR, larger than the compressed raw page (599 B/PR). Only dropping text gets it down, to 190 B/PR.

### 5.2 Keep-everything mode (needs an external drive)

| Component | Lean | Likely | Heavy | Basis |
|---|---|---|---|---|
| Bare git clones | 135 GB | 245 GB | 245 GB | ≈1.1× `diskUsage`; "likely" adds the giants |
| PR refs for rejected-PR code | — | — | +100 GB | ≈1.8× `diskUsage` on GitHub-review repos |
| GitHub raw (gz JSONL) | 10 GB | 13 GB | 15 GB | 1 KB/PR, 1.7 KB/issue, +15% overflow, + file lists |
| Other forges and trackers raw | 2 GB | 4 GB | 60 GB | heavy = full Chromium Gerrit history |
| Vulnerability and selection data | 4 GB | 5 GB | 6 GB | bulk exports; 2–3 selection snapshots |
| Canonical tables (parquet) | 8 GB | 12 GB | 20 GB | commits ≈100 B, file rows ≈13 B, PR/issue tables ≈30–40% of raw (text-free; with full text they match raw) |
| Derived metrics | 2 GB | 3 GB | 5 GB | |
| Headroom (git gc/repack, temp, sorting) | +20% | +20% | +20% | |
| **Total** | **≈200 GB** | **≈340 GB** | **≈550 GB** | |

This mode is worth it only if code-level analyses or phase 2 need many full clones at once. In that case get a 1 TB external SSD formatted APFS, with `LH_DATA_DIR` pointing at it. Git on spinning disks or network drives is painfully slow.

**Recommendation: rolling mode on this Mac for the census.** Back up `raw/` and the git-derived tables to a second location. Re-clone subsets when an analysis needs the code.

The phase-2 performance work (building and benchmarking old commits) is out of scope here. It needs separate space for toolchains, containers and build caches, likely 100s of GB.

## 6. Repository organization

As built on 2026-11-14:

```
little-helper/
├── pyproject.toml, uv.lock, .python-version   # uv-managed; `lh` entry point
├── README.md                                  # setup and commands
├── config/
│   ├── study.yaml                             # git/GitHub settings, policy-file patterns, named project sets
│   ├── selection/                             # candidates.yaml, pilot.yaml, verification/*.yaml
│   └── projects/<id>.yaml                     # generated by `lh selection export`; repos, regime, what to collect,
│                                              #   plus hand-kept path rules and policy paths
├── docs/                                      # sample_selection, data_collection_plan, literature_review, research_notes/
├── src/little_helper/
│   ├── cli.py                                 # `uv run lh <command>`
│   ├── paths.py, config.py, store.py          # locations, configs, atomic writes and manifests
│   ├── ghapi.py                               # GitHub GraphQL client (pacing, rate limits, timeouts)
│   ├── selection/                             # harvest, signals, score, probe, audit, pilot, render, export
│   ├── collect/   git.py github.py            # write raw only
│   ├── normalize/ git.py github.py            # raw -> canonical tables
│   └── classify/  paths.py bots.py trailers.py ai_markers.py
├── tests/                                     # a tiny git repo and a fake GraphQL server; `uv run pytest`
└── data/                                      # committed: manifests/ and selection/ (small outputs) only
```

Still to add: `collect/` adapters for GitLab, Gerrit, Forgejo, Jira, Bugzilla, Trac and OSV; `link/` (change proposal ↔ commit); `metrics/`; and `analysis/` for notebooks and figures.

The data directory is **outside the repo** (`LH_DATA_DIR`, default `./data` for tests):

```
$LH_DATA_DIR/
├── raw/git/<host>/<owner>/<repo>/<run_id>/            # git extracts (parquet + meta.json); clones are deleted
├── raw/github/github.com/<owner>/<repo>/<run_id>/     # zstd JSONL chunks of API pages + queries.json
├── raw/<selection source>/<run_id>/                   # selection harvests
├── state/github/github.com/<owner>/<repo>.json        # resume cursors and refresh watermarks
├── canonical/<table>/project=<id>/part-0.parquet      # rebuildable from raw
└── derived/selection/*.parquet                        # lens tables for the selection
$LH_WORK_DIR/git/...                                   # transient bare clones (internal disk)
$LH_MANIFEST_DIR (default data/manifests/)             # one JSONL per (source, run): file, bytes, sha256
```

## 7. Pipeline principles

1. **Raw is immutable and complete.** Every API page is stored verbatim with its request, parameters and UTC retrieval time, and is never edited. Normalization bugs are fixed by re-normalizing, not re-fetching.
2. **Canonical and derived data are pure functions of raw**, so they can be deleted and rebuilt at any time. In rolling mode the git extracts count as raw: each one is written once, tagged with the extractor version and the refs it came from, and never edited.
3. **Idempotent, resumable, incremental.** There is one state file per (source, project); a crash resumes from the last page, and a refresh asks only for items updated since the cursor.
4. **Freezes.** Analyses run against a named freeze (e.g. `freeze=2026-12-31`). Data are truncated at the freeze time, so a refresh never silently changes published numbers.
5. **Provenance.** Every row in a canonical table carries the run ID and source it came from. Manifests (URL, time, bytes, sha256) are committed.
6. **Privacy and terms.** Raw and canonical data stay local. Published outputs use salted-hash identities, never emails or logins; the salt lives outside the repo. GitHub's Acceptable Use Policies allow research use of public data with open-access publication, and they constrain personal data.
7. **Minimal stack.** We use the git CLI via subprocess, httpx, polars and pyyaml, with plain parquet files and no database server. DuckDB can be added later for ad hoc SQL over the parquet files.

## 8. Canonical tables (first cut)

- **projects, repos.** Census membership, layer and classification, regime, venues, and dated breaks.
- **commits.** SHA, parents, hashed author and committer, timestamps with offsets, message length and text, merge flag, first-parent flag.
- **commit_files.** Path, lines added and deleted, change type, and is_test / is_vendored / is_generated / is_docs flags, plus module.
- **trailers.** Key and value per commit: `Signed-off-by`, `Reviewed-by`, `Acked-by`, `Co-authored-by`, `Assisted-by`, `PR-URL`, `Change-Id` and so on.
- **tags_releases.**
- **change_proposals.** Platform, ID, author, open/close/merge times, platform state, harmonized outcome and the rule that decided it, linked commit SHAs, title and body lengths (raw and template-stripped), labels, additions, deletions and files.
- **cp_files, cp_reviews, cp_comments, cp_events.** Review rounds come from force-push and patch-set events.
- **issues, issue_comments.** Tracker, state, resolution or state reason, labels, lengths.
- **identities.** Hashed person IDs, login and email clusters, bot flag.
- **project_events.** Dated AI-policy adoption and revision, `AGENTS.md`-type files, platform moves, license changes, governance changes, merge-bot changes.
- **ai_markers.** Commit- or proposal-level markers with tool and marker type.
- **vulns.** Advisory, CVE aliases, affected and fixed versions, fix commits, project.

## 9. Phased plan

| Phase | Output | Gate to next phase | Built (2026-11-14) |
|---|---|---|---|
| 0. Census | mechanical nomination → gate → eligibility → ~1,000 projects with auto-detected regimes; ~10–20% hand-checked | the list and its selection report are frozen and committed before any activity data are pulled | pilot of 50 only |
| 1. Git layer | clones; commits, files, trailers, tags; policy and agent-file dates | spot-checks on 20 projects across regimes | yes: `lh collect git`, `lh normalize git` |
| 2. Platform layer | GitHub GraphQL PRs and issues; GitLab, Gerrit, Forgejo | per-regime completeness checks against platform totals | GitHub only: `lh collect github`, `lh normalize github` |
| 3. Trackers and vulnerabilities | Jira, Bugzilla, Trac; OSV and GHSA | | no |
| 4. Link and normalize | CP↔commit linkers per project and era, validated on hand-labelled samples; identities and bots | linker precision and recall reported per project | normalizers yes; linkers no |
| 5. Metrics | the measures in §2 | | no |

Start phases 1–4 on a **20-project slice spanning all regimes** before running the full census, so adapter and linker bugs surface while they are cheap. The slice is defined in `config/study.yaml` (`--set slice`).

Lessons from the first live runs (2026-11-14, on zlib, xz, curl and git):

- **`Assisted-by:` is not always AI.** curl has used it for human helpers since 2013, and git used it for people before AI tools. AI markers from trailers therefore require a tool or model name in the value (and "Claude" must look like the model, not a person).
- **Date AI-era events by commit time, not author time.** One git commit carrying `Assisted-by: Opus 4.7` has an author date in 2019 and a commit date in 2026: an old branch rebased with AI help.
- **The merged flag undercounts acceptance badly.** zlib has 740 PRs on GitHub; 3 are merged and 629 closed, because its maintainer applies patches by hand. Linkers (phase 4) are essential.

How the numbers in this document were measured (2026-11-13/14):

- GitHub GraphQL `diskUsage`, PR, issue and commit counts for the 133 candidate repos, 24 possible giants, and a seeded random sample of 150 repos behind ecosyste.ms critical packages (≥1 MB).
- Full PR and issue pages for numpy, kubernetes, curl, flask and vite, with byte counts and `rateLimit.cost`.
- A bare clone of NumPy, timed, plus fetching `refs/pull/*`, repacking, and extracting `git log --numstat` to zstd parquet.
- Rolling-mode cycles on curl and NumPy (2026-11-14), each followed by deleting the clone. They measured:
  - kept table sizes
  - full diff text compressed with zstd
  - blobless clone size, and `git log --raw` on it with lazy fetching disabled
  - a one-month shallow clone
  - yearly tree listings
- 100 NumPy PRs (2 pages; the third returned a gateway error), stored four ways:
  - per-page gzip
  - one zstd -19 --long stream
  - a parsed table with all text
  - a text-free table

The one-off scripts are in the session scratchpad, not the repo. They will be rewritten as `lh` stages.

## 10. Decisions and risks

1. **Storage.** Rolling mode (§3.1a) on this Mac: ≈28 GB kept, ≈20 GB peak for clones. Back up `raw/` off the machine. An external SSD is needed only for keep-everything mode.
2. **Git fields are fixed at extraction.** Settle the extract list (§3.1a) on the 20-project slice before the census pass. A missed field costs a re-clone pass (~4–8 h plus giants), not a failure.
3. **Giants.** If Chromium (67 GB, Gerrit), Firefox or LibreOffice pass the gate, keep their git-derived measures in full and cap their review data to a window or sample. Chromium needs a blobless clone or an external drive.
4. **PR refs.** Without stored clones, they cost download time rather than ~100 GB of disk. Fetch them transiently for repos under ~5 GB if we want rejected PRs' file lists from git; otherwise use the API's file lists.
5. **ASF Bugzilla account** for httpd's historical bugs, or drop them.
6. **GraphQL heavy pages** can hit the 10 s timeout (a NumPy page returned a gateway error on 2026-11-14), so shrink page size adaptively and log every retry.
7. **Normalizer memory on the largest repos.** `lh normalize github` holds one repository's flattened rows in memory: roughly 2 GB for a Kubernetes-size repo (130k PRs), fine on a 16 GB machine. If Kibana-size repos (200k+ PRs) enter the census, stream rows to parquet per chunk instead.
8. **GH Archive as a fallback.** Whether GitHub's Events API (and therefore GH Archive) still carries full push and PR payloads after reported 2025 changes is unverified. Check before relying on it for anything. This doesn't affect the plan above, which doesn't use it.
