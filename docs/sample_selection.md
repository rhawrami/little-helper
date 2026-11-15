# Sample selection: the pilot 50

Status: pilot. Sources harvested 2026-11-13 (UTC); every raw response is listed with its URL, retrieval time and sha256 in `data/manifests/`. The sample itself is in [`config/selection/pilot.yaml`](../config/selection/pilot.yaml) (choices and reasons) and [`data/selection/pilot_sample.csv`](../data/selection/pilot_sample.csv) (one row per project with its evidence and data regime).

In one paragraph: we nominated 138 candidate projects across 11 layers of the software stack. We measured how much other software relies on each one through six independent channels: language package graphs, container images, the Debian dependency graph, Debian installs, packaging across OS distributions, and hyperscaler managed services. A project passes the significance gate if it dominates one channel and is corroborated by a second, or if it is high in three. 111 passed. We then chose 50 for coverage and analytic contrast, not by rank: 46 gate-passers, 1 entrant (first release 2020 or later) through a lag-adjusted gate, and 3 declared design picks that fail the gate. The rest of this document explains each choice, what we deliberately refused to use, and what the pilot exposed about the process.

## 1. What "workhorse" means here

**Definition.** A project is a workhorse if a large share of deployed software comes to rely on it, and that reliance is visible through at least two independent channels, or overwhelmingly through one.

Software comes to rely on a project in two ways, and a selection rule has to see both:

- **Built from it.** Libraries, compilers and build tools are linked, imported or invoked while other software is made: zlib, OpenSSL, numpy, GCC, CMake.
- **Runs on it.** Kernels, runtimes, databases and servers are what other software is deployed onto. Nothing "depends on" PostgreSQL or nginx in a package manifest, yet a large share of applications cannot run without them.

Separately, workhorses can be **quiet** or **loud**. Quiet ones are invisible to the developers who rely on them, such as zlib, libuv, ICU and xz. Loud ones are chosen deliberately and by name, such as PostgreSQL, React and Kubernetes. A good rule must not favor either kind. Popularity measures (stars, survey mentions) only see the loud ones; dependency graphs mostly see the quiet ones.

**Unit of analysis.** The unit is the *project*: one upstream development community. It is not a repository or a package. Plotly is two repositories, D3 is dozens, and protobuf is published under many package names. Every signal takes the **maximum** over a project's mapped identifiers, never the sum, so splitting a project into many packages cannot inflate it ([`config/selection/candidates.yaml`](../config/selection/candidates.yaml) is the crosswalk).

## 2. Where we look

| Source | What it measures | Channel | Snapshot | Known bias |
|---|---|---|---|---|
| [ecosyste.ms](https://ecosyste.ms) critical packages, 8 registries (npm, PyPI, crates, Maven, Go, RubyGems, NuGet, Packagist), 6,877 packages, plus per-package lookups | dependent packages, dependent repositories, downloads (registry-wide percentiles) | packages | 2026-11-13 | Sees only what is *declared* in manifests; rankings lag for fast-growing new packages (below) |
| ecosyste.ms Docker usage | number of container images that contain the package | containers | 2026-11-13 | Bundled browser code is mostly invisible |
| [Docker Hub official images](https://hub.docker.com/u/library) (181) | cumulative pulls | containers | 2026-11-13 | Cloud/server-side; CI pulls inflate counts |
| [Debian sid](https://snapshot.debian.org) archive metadata, two snapshots (2022-11-29, 2026-11-11) | PageRank over the source-package dependency graph (runtime `Depends`/`Pre-Depends` and `Build-Depends`) | distro_graph | both dates | Rewards what Debian itself uses (Perl, Python, debhelper); blind to Essential packages (handled below) |
| [Debian popcon](https://popcon.debian.org) | installs per source package | distro_installs | 2026-11-13 | Opt-in, desktop-heavy; under-counts servers |
| [Repology](https://repology.org) | number of OS distribution families packaging it (projects in ≥30 families harvested: 2,387) | distro_packaging | 2026-11-13 | Saturates near ~113 families, so it works as a threshold, not a ranking |
| Hyperscaler managed services (curated) | how many of AWS, Azure and GCP run the actual open-source engine as a managed service | managed | 2026-11 | Only applies to data services and orchestration; hand-coded |

Reported but deliberately **not** used for gating (section 4): OpenSSF Criticality Score (2025-07-25 snapshot, 585,594 GitHub repos), OSS-Fuzz enrolment (1,403 projects), GitHub stars.

Two sources we tried failed, and those failures are part of the record. The OpenSSF Criticality Score bucket refuses downloads (its billing account is disabled; checked 2026-11-12). Its repository still carries the 2025-07-25 snapshot, and that is what we used. Anonymous Docker Hub clients get HTTP 403 on page 2 of the official-image listing, so we fetch page 1 in both sort orders, which covers all 181 images.

## 3. The significance gate

Each source gives one or more *lenses*. Lenses are grouped into six *channels*: packages, containers, distro_graph, distro_installs, distro_packaging and managed. Each channel is an independent route by which other software comes to rely on a project, and a channel's tier is the maximum of its lenses. Grouping matters. ecosyste.ms's dependent-packages, dependent-repos and downloads lenses come from one aggregator and are strongly correlated. Counted separately, any popular npm package would "corroborate itself" three times.

| Lens | T1 (dominant) | T2 (high) |
|---|---|---|
| package dependents / dependent repos / downloads (registry-wide percentile) | top 0.1% | top 1% |
| Docker official-image pulls | ≥ 1B | ≥ 100M |
| container images containing the package | ≥ 20,000 | ≥ 2,000 |
| Debian PageRank (max of runtime, build) | top 0.5% of ~42k sources | top 2% |
| Debian popcon installs | top 0.5% | top 2% |
| Repology families | ≥ 100 | ≥ 70 |
| managed services | all 3 hyperscalers | 2 |

**Rule (dominance or breadth).** A project passes if it is

- **dominant** in one channel (T1) *and* corroborated by a second channel (T2 or better), or
- **broad**: T2 or better in at least three channels without dominating any. This is the quiet-engine path. libuv, nghttp2, libsodium, Abseil, GStreamer and Ninja pass only this way.

**Entrants** (first public release 2020 or later) cannot yet have been packaged by distributions, so the three distro channels lag by years. They get a lag-adjusted gate: T1 in packages, containers or managed. Vite passes the main gate anyway. uv and Ruff pass only the entrant gate.

**Why a gate and not a score.** The channels cannot be compared: there is no defensible exchange rate between 13.6B Docker pulls and a top-0.5% Debian PageRank. We believe these lenses can separate workhorses from non-workhorses. We do not believe they can rank zlib against xz, or nginx against Kubernetes. Passing the gate makes a project *eligible*. Choosing among eligible projects is a separate, declared step (section 6).

**Two corrections built into the rule.**

- **Essential packages.** Debian policy forbids packages from declaring dependencies on Essential packages (bash, coreutils, parts of glibc and util-linux, perl-base, ncurses-base), so the dependency graph cannot see them even though every package depends on them. Essential sources are treated as T1 on distro_graph. Without this, bash and coreutils fail the gate.
- **Stale rankings.** ecosyste.ms's percentile rankings lag behind fast-growing packages. On 2026-11-13, uv had 127.7M PyPI downloads in the past month yet sat at the 27th percentile of PyPI downloads, and it is absent from the "critical" set. If a package's raw downloads reach the median of its registry's critical set, it is treated as downloads-T1.

Result: of 138 candidates, **111 pass the main gate**, **2 more pass only the entrant gate** (uv, Ruff), and 25 fail. The full table is [`data/selection/candidate_signals.csv`](../data/selection/candidate_signals.csv).

## 4. What we refused to use as significance evidence, and why

- **The OpenSSF Criticality Score.** It is built from 2025 commit frequency, contributor counts, issue-update counts and recent releases. Those are the outcomes this project studies. Selecting on them would select on the dependent variable: projects whose activity grew after 2022 (possibly *because* of AI) would be over-sampled. It is also GitHub-only and noisy. Kernel forks and vendor trees (linux-xtensa, raspberrypi/linux, gregkh/linux) crowd its top 50. We report it for transparency only.
- **GitHub stars and forks.** They measure attention, can be gamed, and are biased toward hype cycles and toward GitHub-hosted projects.
- **Download counts alone.** CI systems and mirrors inflate them, and their rankings go stale (uv). Downloads enter only as one lens inside the packages channel.
- **Any activity measured after 2022.** The gate uses dependency, deployment and packaging evidence only. Activity is what we will measure, not how we choose.

## 5. Eligibility beyond significance

A project must also:

1. **Have an OSI-approved license today.** MongoDB (SSPL) is excluded. Licence changes during the window are recorded as events, not exclusions. Redis moved from BSD-3 to RSALv2/SSPL in 2024 and added AGPLv3 in 2025. Elasticsearch made similar moves.
2. **Expose its commit history publicly**, ideally back to inception (section 8.6 lists the artifacts).
3. **Expose commits plus at least one other public record**: change review or issue tracking. SQLite passes on commits plus its public Fossil tickets and forum, but review measures will be structurally missing (it does not accept outside code).
4. **Be an upstream project**, not a distribution, aggregate or packaging repository. Docker's top images include `alpine`, `ubuntu` and `debian`, and Criticality's top list includes `nixos/nixpkgs` and `gentoo/gentoo`. None of these are candidates.
5. **Not be a fork that merely tracks upstream.** Valkey is the declared exception (section 6).

At scale-up, a *substance* filter will also be needed to keep out micro-packages, the left-pad problem. Dependency graphs love tiny modules like `ms` or `inherits`, which have high centrality but no development history worth studying. A reasonable start is a minimum number of commits and distinct contributors *before 2022*, calibrated on the pool. It does not bind in this pilot because the pool was nominated by layer.

## 6. Stratification and choice within the gate

The 111 eligible projects cluster unevenly: 22 application frameworks and hubs, 19 core libraries, but only 3 ML frameworks. Taking the "top 50" would also need a ranking we have argued does not exist. Instead:

1. **Eleven layers with fixed quotas** cover the stack from kernel to frameworks: kernel/OS base 4, toolchains 5, runtimes 6, core libraries 5, security and networking 4, data stores 5, servers and infrastructure 5, media and graphics 3, scientific computing 6, ML frameworks 2, application frameworks 5.
2. **Within a layer, choice is for coverage, not rank.** At most two projects per niche (compression, TLS, HTTP servers and so on). We spread across languages (C, C++, Rust, Go, Java, Python, JS/TS, PHP, Ruby), governance models (foundation, company, consortium, volunteer) and data regimes (section 8.5). Between otherwise similar options, we prefer projects that already passed the Debian distro_graph tier in the 2022-11-29 snapshot, to reduce post-treatment selection.
3. **Design picks, capped at 10% of the sample.** Each one fails the gate, is declared, and has a stated analytic purpose.
   - **Plotly** (plotly.js + plotly.py) pairs with Matplotlib. Matplotlib is a SWE-bench source repository, so frontier models were trained and evaluated on it; Plotly is in no benchmark. It passes only the packages channel.
   - **D3** is a benchmark-unexposed JavaScript visualization foundation. Browser-side libraries are bundled into applications, so distribution and container channels cannot see them. That is a structural blind spot of the lenses, not evidence that D3 is minor.
   - **Valkey** is the 2024 licence fork of Redis, offered as a managed service by AWS ElastiCache and Google Memorystore. Redis versus Valkey is a natural experiment in governance and licensing that falls entirely inside the LLM era. It fails the gate only because distributions have not caught up.
4. **One entrant through the entrant gate.** uv (2024) tests whether a backbone born in the LLM era develops differently. Vite (2020) is a second entrant, but it passes the main gate on its own.

## 7. The pilot sample

Generated from `data/selection/pilot_sample.csv` by `lh selection render`. Verified hosting, review, issue, license, governance and AI-policy facts, with sources, are in [`config/selection/verification/`](../config/selection/verification/).

<!-- pilot-table:start -->
| Layer | Project | Basis | Gate evidence: **T1** / T2 | Regime | Review / issues | GitHub merged share | AI policy (first adopted) |
|---|---|---|---|---|---|---|---|
| Kernel & OS base | Linux kernel | gate | **dgraph** / dinst, dpack | D | mailing list / mailing list | — | conditions (2026-02-22) |
| Kernel & OS base | GNU C Library | gate | **dgraph, dinst** / dpack | D | mailing list / Bugzilla | — | none found |
| Kernel & OS base | systemd | gate | **dgraph, dinst** / dpack | A | GitHub PR / GitHub | 0.88 | conditions (2025-07-14) |
| Kernel & OS base | BusyBox ◦ | gate | **ctr** / dinst, dpack | D | mailing list / GitHub | 0.00 † | none found |
| Toolchains & build | GCC | gate | **dgraph, dinst, dpack** | D | mailing list / Bugzilla | 0.00 † | ban (2026-07-29) |
| Toolchains & build | LLVM / Clang | gate | **dgraph, dinst, dpack** | A | GitHub PR / GitHub | 0.89 | conditions (2024-09-10) |
| Toolchains & build | CMake | gate | **pkg, dgraph, dpack** | C | GitLab MR / GitLab | — | conditions (2026-03-14) |
| Toolchains & build | Git | gate | **dgraph, dinst** / dpack | D | mailing list / mailing list | 0.00 † | conditions (2025-11-04) |
| Toolchains & build | uv ◦ | entrant gate | **pkg** | A | GitHub PR / GitHub | 0.88 | conditions (2026-03-13) |
| Runtimes | CPython | gate | **ctr, dgraph, dinst, dpack** | A | GitHub PR / GitHub | 0.85 | conditions (2024-10-22) |
| Runtimes | Node.js | gate | **ctr, dgraph** / dpack | A | GitHub PR / GitHub | 0.33 | disclosure (2026-08-12) |
| Runtimes | OpenJDK | gate | **ctr, dgraph** / dpack | B | GitHub PR / Jira | 0.00 † | ban (2026-04-09) |
| Runtimes | Go | gate | **ctr** / dgraph, dpack | C | Gerrit / GitHub | 0.00 † | none found |
| Runtimes | Rust | gate | **dgraph** / ctr, dpack | A | GitHub PR / GitHub | 0.77 | conditions (2026-08-05) |
| Runtimes | PHP | gate | **ctr, dgraph** / dinst, dpack | A | GitHub PR / GitHub | 0.34 | disclosure (2026-03-24) |
| Core libraries | zlib | gate | **dgraph, dinst** / dpack | A | GitHub PR / GitHub | 0.01 † | none found |
| Core libraries | XZ Utils / liblzma | gate | **dgraph, dinst, dpack** | A | GitHub PR / GitHub | 0.24 † | none found |
| Core libraries | libxml2 | gate | **dgraph, dpack** / dinst | C | GitLab MR / GitLab | 0.00 † | ban (2026-05-29) |
| Core libraries | ICU | gate | **dgraph, dpack** / dinst | B | GitHub PR / Jira | 0.88 | none found |
| Core libraries | Protocol Buffers | gate | **pkg, dpack** / ctr, dgraph, dinst | A | GitHub PR / GitHub | 0.44 | conditions (2026-11-09) |
| Security & networking | OpenSSL | gate | **dgraph, dinst, dpack** | A | GitHub PR / GitHub | 0.01 † | disclosure (2026-06-18) |
| Security & networking | curl / libcurl | gate | **dgraph, dinst, dpack** | A | GitHub PR / GitHub | 0.01 † | conditions (2025-05-12) |
| Security & networking | OpenSSH | gate | **dinst, dpack** / dgraph | D | mailing list / Bugzilla | 0.00 † | none found |
| Security & networking | libuv | gate | dgraph, dinst, dpack | A | GitHub PR / GitHub | 0.49 | none found |
| Data stores | PostgreSQL | gate | **ctr, dgraph, mgd** / dpack | D | mailing list / mailing list | — | none found |
| Data stores | SQLite | gate | **dgraph, dinst, dpack** | E | none (closed) / forum | 0.00 † | none found |
| Data stores | Redis ◦ | gate | **ctr, mgd** / dpack | A | GitHub PR / GitHub | 0.64 | none found |
| Data stores | Valkey ◦ | design | mgd | A | GitHub PR / GitHub | 0.81 | conditions (2026-10-08) |
| Data stores | Apache Kafka ◦ | gate | **pkg, mgd** | B | GitHub PR / Jira | 0.62 | disclosure (2026-06-18) |
| Servers & infrastructure | nginx ◦ | gate | **ctr** / dgraph, dpack | A | GitHub PR / GitHub | 0.45 | none found |
| Servers & infrastructure | Apache HTTP Server | gate | **ctr, dinst** / dgraph, dpack | B | GitHub PR / Bugzilla | 0.11 † | conditions (2023-07-18) |
| Servers & infrastructure | Kubernetes ◦ | gate | **pkg, mgd** / ctr | A | GitHub PR / GitHub | 0.73 | disclosure (2025-11-08) |
| Servers & infrastructure | containerd ◦ | gate | **pkg** / ctr | A | GitHub PR / GitHub | 0.81 | conditions (2026-03-23) |
| Servers & infrastructure | QEMU ◦ | gate | **dinst** / dgraph, dpack | D | mailing list / GitLab | — | ban (2025-06-24) |
| Media & graphics | FFmpeg | gate | **dinst, dpack** / dgraph | C | Forgejo PR / Forgejo | — | ban (2026-09-13) |
| Media & graphics | Mesa 3D | gate | **dinst, dpack** / dgraph | C | GitLab MR / GitLab | — | disclosure (2026-04-06) |
| Media & graphics | FreeType | gate | **dgraph, dinst, dpack** | C | GitLab MR / GitLab | 0.00 † | none found |
| Scientific computing | NumPy | gate | **pkg, dgraph** / ctr, dpack | A | GitHub PR / GitHub | 0.82 | disclosure (2026-03-08) |
| Scientific computing | pandas | gate | **pkg** / ctr, dgraph | A | GitHub PR / GitHub | 0.77 | disclosure (2026-01-27) |
| Scientific computing | Matplotlib | gate | **pkg** / ctr, dgraph, dpack | A | GitHub PR / GitHub | 0.85 | disclosure (2024-11-25) |
| Scientific computing | scikit-learn ◦ | gate | **pkg** / ctr | A | GitHub PR / GitHub | 0.70 | disclosure (2024-06-19) |
| Scientific computing | Plotly (plotly.js + plotly.py) ◦ | design | **pkg** | A | GitHub PR / GitHub | 0.84 | conditions (2026-08-24) |
| Scientific computing | D3 ◦ | design | **pkg** | A | GitHub PR / GitHub | 0.41 | none found |
| ML frameworks | PyTorch ◦ | gate | **pkg** / ctr | A | GitHub PR / GitHub | 0.05 † | disclosure (2026-01-28) |
| ML frameworks | Hugging Face Transformers ◦ | gate | **pkg** / ctr | A | GitHub PR / GitHub | 0.73 | conditions (2026-03-22) |
| Application frameworks | React ◦ | gate | **pkg** / ctr | A | GitHub PR / GitHub | 0.66 | none found |
| Application frameworks | Vite ◦ | gate | **pkg** / ctr | A | GitHub PR / GitHub | 0.75 | conditions (2026-08-21) |
| Application frameworks | Django | gate | **pkg** / dgraph | B | GitHub PR / Trac | 0.50 | disclosure (2026-01-08) |
| Application frameworks | Spring Framework ◦ | gate | **pkg, ctr** | A | GitHub PR / GitHub | 0.18 † | conditions (2026-10-01) |
| Application frameworks | Ruby on Rails | gate | **pkg, dgraph** / ctr | A | GitHub PR / GitHub | 0.70 | none found |

Channels: pkg = language package graphs, ctr = containers, dgraph = Debian dependency graph, dinst = Debian installs, dpack = packaging across OS families, mgd = hyperscaler managed services. Regimes A–E as in section 8.5. † = under 30% of closed GitHub PRs are marked merged; accepted changes must be reconstructed from commits (section 8.4). ◦ = did not pass the Debian dependency-graph tier in the 2022-11-29 snapshot. This mostly marks language libraries and cloud platforms that Debian barely packages, not post-2022 risers. AI-policy dates are the first formal policy text; several projects have tightened theirs since (see `config/selection/verification/`).
<!-- pilot-table:end -->

## 8. What the pilot exposed (scrutiny of the process)

### 8.1 Every lens has a blind spot, and the gate's job is to cover them with each other

| Blind spot | Who it hides | How the rule copes |
|---|---|---|
| Package graphs see only what is declared | system libraries (zlib, OpenSSL), platforms (PostgreSQL), tools (git, uv) | distro and container channels |
| Distro graphs see only what distributions package and declare; Essential packages are invisible | front-end JS, cloud services, bash/coreutils | packages and containers channels; the Essential correction |
| Distro graphs reward Debian's own tooling | Perl and Python rank above Go and Rust | treat significance as a gate, not a ranking |
| Containers see server-side deployment only | desktop and browser software | distro and packages channels |
| Nothing sees **vendored or embedded copies** | SQLite amalgamations, zlib copies, ggml inside llama.cpp-based apps, stb headers | not handled yet. llama.cpp fails every lens even though Ollama and LM Studio are built on it. Fixing this needs SBOM or code-reuse data (Software Heritage file hashes, Census III composition data) |
| Platform software is depended on operationally, not declaratively | Redis, MySQL, Kafka, RabbitMQ | containers plus the curated managed channel. RabbitMQ, Elasticsearch and Cassandra still fail |

### 8.2 The candidate pool, not the rule, is the weakest link

The 138 candidates were nominated by hand from the top of each lens plus layer coverage. An audit compares each lens's own top list against the pool ([`selection/audit.py`](../src/little_helper/selection/audit.py), output in [`data/selection/pool_audit.json`](../data/selection/pool_audit.json)). It finds many clear workhorses missing:

- **Linux userland and desktop:** PAM, libselinux, libcap, GMP/MPFR, readline, GnuPG, D-Bus, systemd's neighbours (e2fsprogs, kmod), Qt, GTK, cairo/pango, fontconfig, libX11/xcb, Wayland, PipeWire.
- **Network services:** OpenLDAP, Samba, BIND, nftables.
- **JVM:** JUnit, SLF4J, Logback, Mockito, Apache Commons.
- **JavaScript tooling:** ESLint, Jest, Prettier.
- **Rust:** serde_json, clap, anyhow.
- **Go:** golang.org/x/*, testify.
- **.NET and PHP:** Newtonsoft.Json, Guzzle, PHPUnit.

The gate would likely pass many of them. **For scale-up, the pool must be generated mechanically** as the union of every lens's top N, mapped to projects, rather than by hand. Hand mapping should be limited to resolving package names to projects.

### 8.3 Selecting on 2026 significance is close to selecting on 2022 significance, for systems software

Debian runtime PageRank has a Spearman rank correlation of **0.90** between the 2022-11-29 and 2026-11-11 snapshots (on source packages present in both). **81%** of the top 400 are the same. For OS-level software, the gate is not materially contaminated by post-ChatGPT change. For language libraries and entrants we have no pre-period snapshot yet; the 2022 Census II or historical deps.dev data could supply one. In the pilot table, `passed_gate_pre_chatgpt_debian` marks which projects were already high in the 2022 snapshot.

### 8.4 On GitHub, "merged" does not mean "accepted"

Many projects land changes outside GitHub's merge button. Maintainers rebase and push, bots land them, or changes are imported from Gerrit or an internal monorepo, and the PR is then *closed*. On 2026-11-12:

| Project | merged | closed, not merged | how changes actually land |
|---|---|---|---|
| OpenJDK | 25 | 33,391 | Skara bot integrates, then closes |
| PyTorch | 6,680 | 130,838 | pytorchmergebot lands, then closes |
| OpenSSL | 153 | 19,046 | maintainers rebase and push |
| curl | 222 | 16,699 | maintainer rebases; commit says `Closes #N` |
| Go | 1 | 4,914 | gerritbot imports to Gerrit |
| zlib | 3 | 629 | maintainer applies by hand |
| Spring Framework | 1,062 | 4,927 | rebase and close, `Closes gh-N` |
| Git | 4 | 1,750 | GitGitGadget forwards to the mailing list |

The pattern also moves over time within a project, so a merged share that looks fine overall can hide a regime change:

- **PyTorch:** the merge bot adds a `Merged` label. Of PRs created in 2025, 410 are marked merged and 18,738 closed, yet 12,635 of the closed ones carry that label.
- **protobuf and gRPC:** switched to Copybara landing on 2022-11-11 and 2023-11-13. Landing commits carry `COPYBARA_INTEGRATE_REVIEW=<PR URL>`.
- **Node.js:** landed PRs show as closed until the commit queue began squash-merging on 2021-10-30.
- **pandas and Django:** accepted PRs were closed with "merged in <sha>" comments until roughly 2017–2018.
- **Kafka:** GitHub merges begin around 2017-12.
- **xz:** GitHub force-closed every PR on 2024-04-05, after the backdoor.
- **httpd:** none of its mirror-era PRs (2012–2026) is marked merged.

So "accepted versus rejected" must be **reconstructed by linking change proposals to commits**, not read off the platform. The links are:

- PR URLs and numbers in commit messages: `PR-URL:`, `Closes #N`, `Pull Request resolved:`, `COPYBARA_INTEGRATE_REVIEW=`, OpenSSL's `Merged-from:`
- bot labels and comments: PyTorch `Merged`, OpenJDK `integrated`, "Landed in <sha>"
- Gerrit `Change-Id` and status
- patchwork states and commitfest statuses

Section 9 defines the harmonized outcome. Every link pattern is project-specific and dated, so each project needs a validated linker, checked on a hand-labelled sample per era.

### 8.5 Issues and reviews live in at least ten different systems

GitHub issues are disabled for 17 of the 50 GitHub repositories in the pilot, and Mesa has no GitHub repository at all. After verification, the 50 split into five data regimes:

| Regime | Review | Issues | n | Projects |
|---|---|---|---|---|
| **A** | GitHub PRs | GitHub | 30 | systemd, LLVM, uv, CPython, Node.js, Rust, PHP, zlib, xz, protobuf, OpenSSL, curl, libuv, Redis, Valkey, nginx, Kubernetes, containerd, NumPy, pandas, Matplotlib, scikit-learn, Plotly, D3, PyTorch, Transformers, React, Vite, Spring, Rails |
| **B** | GitHub PRs | Jira, Bugzilla or Trac | 5 | OpenJDK, ICU, Kafka, httpd, Django |
| **C** | GitLab, Gerrit or Forgejo | same forge (Go: GitHub) | 6 | CMake, Go, libxml2, FFmpeg, Mesa, FreeType |
| **D** | mailing list (patchwork, patchew, commitfest at best) | Bugzilla, mailing list, GitLab or GitHub | 8 | Linux, glibc, BusyBox, GCC, Git, OpenSSH, PostgreSQL, QEMU |
| **E** | none for outsiders | forum | 1 | SQLite |

Regime is a column in the pilot table. Collectors need one adapter per system, and review metrics should be compared within a regime or with regime fixed effects. Verification turned up access problems that collectors must plan for:

- **Apache Bugzilla now refuses anonymous API and CSV access** (since about mid-2025), citing AI-scraper abuse. Bulk httpd bug data needs an account.
- **Anubis bot walls** blocked automated reading of the GCC and glibc wikis, git.kernel.org, FFmpeg's Trac and the sourceware forge. APIs and mirrors worked; scraping will not.
- **BusyBox's Bugzilla went offline in 2026.** Bugs now go to GitHub issues on `vda-linux/busybox_mirror`, created 2026-04-21, and the old `mirror/busybox` repo is archived.
- **FFmpeg's canonical repository is ambiguous.** The July 2025 announcement names code.ffmpeg.org (Forgejo); the download page still names git.ffmpeg.org. All copies had the same master on 2026-11-13. Since 2025, PRs merge on Forgejo, and Forgejo issues replaced Trac in 2025-07.

### 8.6 History artifacts that would corrupt a naive "inception to now" series

- Go's default branch begins on 1972-07-19, with joke commits reproducing Kernighan's "hello, world" lineage.
- Valkey's history begins in 2009 because it inherits Redis's history up to the fork (March 2024). Its own series must start at the fork point.
- Linux's git history starts at 2.6.12-rc2 (April 2005); earlier history lives in separate repositories.
- GCC (1988), glibc (1989), CPython (1990), PostgreSQL (1996), httpd (1996) and others include CVS/SVN imports whose commit granularity differs from native git.
- nginx's GitHub repository has existed since 2015 as a read-only mirror and carries history back to 2002. It became the development home on 2024-09-06. Mailing-list patches were accepted until 2024-12-31, and the Trac tickets were not migrated.
- zlib's history before 2011-09 is one commit per release (0.71 through 1.2.5), all dated 2011-09-10.
- systemd's oldest commits are udev history from 2005; systemd itself starts 2009-11-17. protobuf absorbed upb's history (2023-08-24) and containerd absorbed containerd/cri's (2020-10-07), so volume jumps at those dates.
- Spring's 17,962 issues imported from JIRA keep their original dates back to 2003, but their author is a bot account.
- D3's ~30 `d3-*` module repos were updated together on 2026-11-03, a coordinated maintenance spike rather than organic activity.
- In PostgreSQL the git author is usually the committer. Real authors appear in `Author:` lines in the commit message (26 of the latest 30 commits have one), so contributor counts must parse messages.

### 8.7 Dated breaks inside the window must be modelled, not discovered

Verification produced a list of structural breaks after 2022, each of which would otherwise load onto any "post-LLM" coefficient:

- **Review-platform moves.**
  - LLVM moved from Phabricator to GitHub PRs (2023-09).
  - nginx moved to GitHub (2024-09).
  - FFmpeg moved to Forgejo (2025-07).
  - BusyBox bug reports moved to GitHub (2026-04).
  - httpd left Subversion for GitHub PRs on **2026-10-26**.
- **Merge-tooling changes.**
  - Node.js commit queue switched to squash-merge (2021-10).
  - protobuf and gRPC moved to Copybara (2022-11, 2023-11).
  - Rust's merge bot switch (2025-12/2026-01).
  - PyTorch's AI reviewer "GreenLight" may approve PRs from listed authors with no human review (2026-09-01).
  - PyTorch's AI triage auto-closes PRs not linked to an actionable issue (2026-10-02).
- **Governance and ownership.**
  - The xz backdoor (2024-03).
  - Valkey forked from Redis (2024-03).
  - libxml2's maintainers changed (2025-12).
  - React moved from Meta to the React Foundation and the `react/react` org (2026-02 to 2026-06).
  - Astral (uv) announced it will join OpenAI (2026-03). Agent-reported; whether the deal has closed is unverified.
  - VoidZero, which employs Vite core members, joined Cloudflare (2026-06). Agent-reported.
- **Licences.**
  - Redis went to RSALv2/SSPL (2024-03-20), then added AGPLv3 (2025-05-01).
  - PHP relicensed to BSD-3-Clause (2026-04-12).
- **AI policies.** 34 of the 50 projects have adopted one. The earliest is the ASF's foundation-wide guidance covering httpd (2023-07-18), followed by scikit-learn (2024-06-19); the latest is protobuf (2026-11-09):
  - 5 restrictive or bans: OpenJDK, GCC, QEMU, libxml2, FFmpeg's security process.
  - 17 allow AI with conditions.
  - 12 require disclosure.
  - 16 have none found.

  These adoption dates are a ready-made staggered "treatment" calendar.

AI *disclosure* is itself policy-dependent, so marker-based AI measures are not comparable across projects:

- **Linux:** carried an `Assisted-by:` tag only from 7.0-rc1 (2026-02-22) to its removal (2026-10-14), and only about 10% of 7.3's 18,533 non-merge commits used it.
- **Kubernetes:** forbids AI trailers; disclosure goes in PR descriptions.
- **systemd:** has forbidden crediting AI as author or co-author since 2026-06-17.
- **Node.js:** discourages naming AI brands in commit messages.
- **Mesa, OpenSSL and GCC:** *require* an `Assisted-by:` tag.

## 9. Harmonizing the measures

| Measure | Harmonized definition |
|---|---|
| **Commits** | From the canonical git clone, not the API. Keep both all commits and first-parent commits on the default branch (squash-merge projects make these differ). Store author and committer timestamps with offsets. Apply `.mailmap`, flag bots, and exclude imports before each project's verified history start. |
| **Change proposals (CP)** | One abstraction over GitHub PRs, GitLab MRs, Forgejo PRs, Gerrit changes and mailing-list patch series (via patchwork, lore/public-inbox or commitfest). **Outcome**: *accepted* if the platform says merged **or** a commit on a release or default branch is linked to it; *rejected* if closed or abandoned with no linked commit; *withdrawn* where the platform distinguishes it (commitfest "Withdrawn", author-closed); *superseded* when replaced by a newer version of the same series; *pending* if open at the snapshot date. "Waiting" is pending with no activity for N days. |
| **Issues** | One abstraction over GitHub and GitLab issues, Bugzilla, Jira, Trac, Fossil tickets and mailing-list bug reports, with states open and closed and a resolution (fixed, won't fix, duplicate, invalid) where the tracker records it. |
| **Diff size** | Lines added and deleted and files changed per commit and per CP, excluding vendored, generated and lock files (per-project path rules). |
| **Diff breadth** | *Spatial*: number of top-level modules or directories touched and the entropy of the change across them. *Kind*: a category per commit or CP: feature, fix, **performance**, refactor, test, docs, build/CI, dependency bump, security, revert. Start from conventional prefixes, labels and keywords, then a classifier validated on a hand-labelled sample. Labelled performance commits already exist for numpy, pandas, matplotlib and scikit-learn in the GSO, SWE-Perf and SWE-fficiency datasets. |

Further attributes worth tracking:

- time to first non-author response and time to close, merge or land
- review rounds and reviewer count
- new contributors and their 6- and 12-month retention
- contribution concentration (truck factor)
- reverts and follow-up fixes within 30 days
- test-to-code share of changes
- security fixes and CVE references per release
- release cadence and backports
- dependency-bot share of changes
- PR and issue description length
- AI markers: bot authors, `Co-authored-by` trailers, branch prefixes, project disclosure tags
- dated AI-policy adoption, as a project-level event

## 10. Decisions (recorded 2026-11-14)

1. **Scale-up target: about 1,000 projects**, as a census of everything that passes the gate and eligibility. It is not a fixed number. The pool is nominated mechanically from each lens's top list, with per-registry caps so npm's size can't dominate, and a minimum-size rule measured before 2022. Layers become a classification, not quotas.
2. **No design picks.** Plotly, D3 and Valkey are in only if they pass the gate. The browser-library blind spot is addressed with a candidate seventh channel (sites that load the library, e.g. HTTP Archive), to be tested, rather than with exceptions.
3. **AI-domain projects stay in**, flagged; a finer classification of the final set comes later.
4. **The managed-service channel stays**, rebuilt as a sourced table: provider product page and date checked.
5. **Accepted/rejected/pending metrics only for regimes A–C.** Regime D contributes commits, issues and reviewer trailers.
6. **MySQL is out.**

Attributes added to the collection: review rounds and reviewer count, truck factor, test-to-code share, PR/issue description length, dated AI-policy and `AGENTS.md`-type adoption events, and security fixes and CVE references per release. See [`data_collection_plan.md`](data_collection_plan.md).

## 11. Reproduce

```bash
uv sync
uv run lh selection harvest     # raw sources -> $LH_DATA_DIR/raw/, manifests -> data/manifests/
uv run lh selection signals     # one table per lens -> $LH_DATA_DIR/derived/selection/
uv run lh selection score       # gate results per candidate -> data/selection/candidate_signals.csv
uv run lh selection audit       # pool coverage and 2022-vs-2026 stability -> data/selection/pool_audit.json
uv run lh selection probe       # GitHub-side PR/issue/history counts -> data/selection/github_probe.csv
uv run lh selection pilot       # data/selection/pilot_sample.csv
uv run lh selection render      # the table in section 9 of this document
uv run lh selection export      # config/projects/<id>.yaml, which the collectors read
```

`uv run lh selection rebuild` re-runs the offline steps (signals through render) from the archived raw files. On 2026-11-14 it reproduced `pilot_sample.csv` and `candidate_signals.csv` byte for byte. The pool audit's top-N lists now break ties by name; before that, which of two tied Repology projects made the top 100 could change between runs.

Live sources change daily. To reproduce the published numbers, use the archived raw files listed in `data/manifests/`; a re-run produces a new, separately timestamped snapshot.
