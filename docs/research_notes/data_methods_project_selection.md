# Data Infrastructure, Methods, and Project Selection for Longitudinal OSS Analysis (incl. Performance over Commit History)

Research date: 2026-11-12. Legend: items tagged **[bg]** come from the researcher's prior knowledge and point to the canonical primary URL, but that page was **not fetched in this session**. Verify them before relying on them in published text. Untagged items were checked against the cited page or search result in this session.

---

## 1. Data sources for mining repo history at scale, and their tradeoffs

### Takeaway
Use local `git` clones as the canonical source for commit-level history. They have no rate limits, they reach back before GitHub existed, and they are the only route for non-GitHub forges. Use the GitHub API only for things that exist nowhere else: PRs, reviews, issues, reactions, CI checks and release objects. GH Archive is the only practical source for *historical* event streams, because the live Events API covers just 30 days and 300 events. GHTorrent is dead. Software Heritage and World of Code are the cross-forge, "universe-scale" options.

### Cited Findings
**GitHub REST API limits (current docs)**
- Primary limits: 60 req/h unauthenticated (per IP); 5,000 req/h for an authenticated user (PATs, plus GitHub/OAuth app tokens acting for the user); 15,000 req/h for GitHub Apps owned by an Enterprise Cloud org; `GITHUB_TOKEN` in Actions gets 1,000 req/h per repo. GitHub App installations get at least 5,000/h, plus 50/h per repo beyond 20 and 50/h per org user beyond 20, capped at 12,500/h — [GitHub Docs: REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- Secondary limits, shared across REST and GraphQL: at most 100 concurrent requests; 900 points/min for REST and 2,000 points/min for GraphQL; 90 s of CPU time per 60 s of wall time (at most 60 s of it GraphQL); 80 content-creating requests/min and 500/h. A REST GET costs 1 point and a mutating call 5. There is "no way to check secondary limit status", and the limits "may change without notice" — [GitHub Docs: REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- Headers: `x-ratelimit-limit/remaining/used/reset/resource`. On a secondary-limit 403/429, honor `retry-after` if present. If it is absent, wait until `x-ratelimit-reset` when remaining is 0, otherwise wait at least 1 min, then back off exponentially. "Continuing to make requests while rate limited may result in your integration being banned." `GET /rate_limit` is free against the primary limit but counts against the secondary one — [GitHub Docs: REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- GraphQL: 5,000 points/h per user (10,000 for Enterprise Cloud-owned apps). Every connection needs `first`/`last` between 1 and 100. A single call is capped at 500,000 total nodes. Requests longer than 10 s are terminated with a 502/504, and each timeout deducts extra points from the next hour's primary limit — [GitHub Docs: GraphQL rate & query limits](https://docs.github.com/en/graphql/overview/rate-limits-and-query-limits-for-the-graphql-api)
- Events API: "The timeline will include up to 300 events. Only events created within the past 30 days will be included." Event latency runs "anywhere from 30s to 6h", and the API "is not built to serve real-time use cases." Pages hold at most 100 results — [GitHub Docs: Events](https://docs.github.com/en/rest/activity/events)
- Other pagination caps **[bg]**: the Search API returns at most 1,000 results per query, so you have to slice by date ranges ([Search docs](https://docs.github.com/en/rest/search/search)). Listing a PR's commits returns at most 250 commits, and the compare endpoint is similarly capped ([Pulls docs](https://docs.github.com/en/rest/pulls/pulls)).
- Data that exists only via the API **[bg]**: PR objects and their state transitions, review states, review and inline comments, issues and issue comments, reactions, labels and milestones, timeline/cross-reference events, check runs and statuses, GitHub "Release" objects (tags themselves are in git), stargazer timestamps (custom `star+json` media type), and Discussions (GraphQL only). One workaround: PR head commits can be fetched over plain git via `refs/pull/*/head`, with no API cost ([GitHub Docs: checking out PRs locally](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/checking-out-pull-requests-locally)).

**Local-clone tooling [bg]**
- PyDriller (Spadini, Aniche, Bacchelli, ESEC/FSE 2018 demo): a Python wrapper over GitPython that yields commits, modified files, diffs, churn, and DMM metrics. It is easy to use but slow on huge repos like Linux and LLVM — [github.com/ishepard/pydriller](https://github.com/ishepard/pydriller)
- pygit2 (libgit2 bindings) runs in-process and is faster than shelling out — [pygit2.org](https://www.pygit2.org/). gitoxide (`gix`, Rust) is very fast for traversal and statistics — [github.com/GitoxideLabs/gitoxide](https://github.com/GitoxideLabs/gitoxide)
- The cheapest bulk extraction is `git log --numstat --format=...` (or `--raw`) piped into polars. `git-of-theseus` produces code-survival cohort plots — [github.com/erikbern/git-of-theseus](https://github.com/erikbern/git-of-theseus)

**GH Archive [bg]**
- Hourly JSON dumps of the public GitHub event timeline since 2011, mirrored in BigQuery (`githubarchive` dataset). It is the de facto replacement for long-horizon event history, since the live Events API only reaches back 30 days (verified above) — [gharchive.org](https://www.gharchive.org/)

**GHTorrent: defunct**
- A 2022 practitioner write-up calls GHTorrent an offline mirror of the REST API that "doesn't have recent data", with data running only to about 2019–2020 — [levelup.gitconnected, 2022](https://levelup.gitconnected.com/how-to-mine-github-data-in-2022-e9c70b3f61d3). OpenHub marks the project Inactive — [openhub.net/p/ghtorrent](https://openhub.net/p/ghtorrent). Papers still cite the 2019-06-01 dump — [UMONS paper](https://orbi.umons.ac.be/bitstream/20.500.12907/51938/1/paper.pdf)
- When fetched on 2026-11-12, `ghtorrent.org` served an unrelated gambling (slot) promotion site, i.e., the domain has lapsed or been taken over — [ghtorrent.org (fetched 2026-11-12)](https://ghtorrent.org/). Do not link to or download from it.

**Software Heritage (SWH)**
- The archive is exported periodically as the SWH Graph Dataset. Sources include forges (GitHub, GitLab), distributions (Debian), and package managers (PyPI). The graph-only export suits metadata analysis, not textual analysis of code. It was the subject of the MSR 2020 Mining Challenge — [SWH Graph Dataset (arXiv 2011.07824)](https://arxiv.org/pdf/2011.07824); [SWH docs](https://docs.softwareheritage.org/devel/swh-export/graph/)
- License is CC BY 4.0 for the dataset as a compilation. Downloading means accepting the SWH ethical charter and the bulk-access terms. Files sit in public S3 and need no login. The terms disclaim any license-detection accuracy, are governed by French law, and recommend running a mirror for heavy use. Requested citation: Pietri, Spinellis, Zacchiroli, MSR 2019 — [Zenodo record](https://zenodo.org/record/2583978); [SWH dataset page](https://docs.softwareheritage.org/devel/swh-export/graph/dataset.html); [SWH bulk-access terms (mirror)](https://mirror.softwareheritage.enea.it/legal/access)
- Note: in this session, docs.softwareheritage.org returned an Anubis bot-challenge "Access Denied" page to automated fetching — [docs.softwareheritage.org](https://docs.softwareheritage.org/devel/swh-export/graph/). Automated pipelines may need to use the S3 buckets or the API instead.

**World of Code (WoC)**
- WoC is "an infrastructure that creates a very large and frequently updated collection of version control data in the entire FLOSS ecosystems". Its paper compares WoC against GHTorrent, SWH, Boa, and GH Archive — [WoC paper (arXiv)](https://bohrium.dp.tech/paper/arxiv/2011.07914)
- **[bg]** WoC (Mockus et al., UTK) offers cross-forge author-alias resolution, fork de-duplication ("deforking"), and maps from commits to projects, authors, and blobs. Access is by application, for accounts on its servers. The worldofcode.org homepage returned only a title to the fetcher, so access terms could not be verified — [worldofcode.org](https://worldofcode.org/)

**Other ecosystems/services [bg]**
- Boa: a DSL plus infrastructure over fixed snapshots of GitHub and SourceForge. It is good for reproducible queries but the snapshots are dated — [boa.cs.iastate.edu](https://boa.cs.iastate.edu/)
- ecosyste.ms: open APIs over packages, repos, dependents, and maintainers across dozens of registries — [ecosyste.ms](https://ecosyste.ms/). The founder says the same dependency graph exists for npm, RubyGems, Maven, Cargo, Go, Packagist, Hex and others (verified) — [nesbitt.io 2026-05-13](https://nesbitt.io/2026/05/13/showing-our-work)
- deps.dev (Google Open Source Insights): dependency graphs, dependents counts, Scorecard data. API plus BigQuery public dataset — [deps.dev](https://deps.dev/); [docs](https://docs.deps.dev/)
- libraries.io: SourceRank and dependents data. Its bulk open-data dumps are old (about 2020) — [libraries.io/data](https://libraries.io/data)
- OpenDigger / OpenRank (X-lab, East China Normal University): precomputed per-repo monthly metrics and OpenRank (a PageRank-style influence measure over GitHub collaboration networks), served as static JSON files. Useful as a cheap cross-check — [github.com/X-lab2017/open-digger](https://github.com/X-lab2017/open-digger)

**Licensing / ToS for publishing derived data**
- GitHub Acceptable Use Policies §7: API collection is not "scraping". Researchers may use "public, non-personal information" for research "only if any publications resulting from that research are" open access. Information may not be used for spam or unsolicited email, or sold (e.g., to recruiters). §8: personal information may be used only for the purpose the user authorized, must be reasonably secured, and complaints, removal and "do not contact" requests must be answered promptly — [GitHub Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)
- SWH: CC BY 4.0 compilation, but each component keeps its own license, and the user must determine it — [SWH bulk-access terms](https://mirror.softwareheritage.enea.it/legal/access)

### Inferences
- For little-helper, use a hybrid pipeline. Phase 1 commit history comes from `git clone --mirror` plus a `git log --numstat` parser into polars (or pygit2/gitoxide for speed); PyDriller is fine for small repos. The REST API is used only for PR, issue and review metadata. GraphQL is attractive for nested PR→reviews→comments pulls (one query instead of N REST calls), but the 10 s timeout and node limits force small pages (e.g., `first: 50` with nested `first: 20`).
- The 30-day Events window means retrospective "activity" series (stars, forks, issue events) must come from GH Archive or from per-object timestamps (`created_at`, `closed_at`, `merged_at`). The live Events API cannot supply them.
- Because the GitHub AUP requires open-access publication for research use of public data and restricts personal information, the published dataset should hash or pseudonymize author emails and names, and the paper or report should be open access.
- Searches for older code do not need GHTorrent. GH Archive (events), SWH (cross-forge commit graph), or WoC (author-resolved universe) cover that need.

### Gaps
- WoC's current version, update cadence, and access terms could not be verified because the site returned no content to the fetcher.
- I did not find a current statement on whether GH Archive event payloads changed after GitHub's 2025-era Events API changes. Check the gharchive.org changelog before relying on payload fields such as the PushEvent commit lists.
- I did not verify GH Archive's or ecosyste.ms's data license (believed CC-BY-SA-4.0 for ecosyste.ms) in this session.

---

## 2. Metrics frameworks and standard MSR measures

### Takeaway
CHAOSS gives standardized metric *definitions* and tooling (GrimoireLab, Augur) that also covers mailing lists, Gerrit and Bugzilla, which matters for non-GitHub projects. OpenSSF Scorecard and Criticality Score cover security and importance. Truck factor and standard MSR measures such as churn, turnover, newcomer retention, time-to-first-response and merge latency are well established and can be computed from git plus PR metadata.

### Cited Findings
- OpenSSF Criticality Score is a number between 0 and 1, "derived from various project usage metrics in a fully automated way". It combines signals using Rob Pike's weighted arithmetic mean with zipfian normalization, using default weights and max thresholds. Lists are published as CSV and as a BigQuery dataset — [ossf/criticality_score (via search summary)](https://packages.ecosyste.ms/registries/proxy.golang.org/packages/github.com%2Fossf%2Fcriticality_score%2Fv2); [Google OSS blog, 2020](https://opensource.googleblog.com/2020/12/finding-critical-open-source-projects.html?m=0)
- The Linux Foundation `critical-projects` repo exists to address limitations of the OpenSSF Criticality Score and cut false positives. It warns that signals measured inconsistently across projects bias rankings — [github.com/linuxfoundation/critical-projects](https://github.com/linuxfoundation/critical-projects); comparison: [OpenSSF blog, "Apples and apples?"](https://openssf.org/?p=2213)
- CHAOSS metrics catalog (Evolution, Risk, Value, Common, DEI working groups), with definitions for Time to First Response, Change Request Closure Ratio, Contributor Absence Factor (a bus-factor variant), New Contributors, Inactive Contributors and others **[bg]** — [chaoss.community/kb-metrics-and-metrics-models](https://chaoss.community/kb-metrics-and-metrics-models/)
- GrimoireLab **[bg]**: Perceval (data retrieval from git, GitHub, GitLab, Gerrit, Bugzilla, Jira, mbox/pipermail mailing lists, Discourse, and more), plus SortingHat (identity merging), ELK and Kibiter dashboards — [chaoss.github.io/grimoirelab](https://chaoss.github.io/grimoirelab/). Perceval paper: Dueñas et al., MSR 2018. Augur (PostgreSQL-backed collector of GitHub/GitLab data with CHAOSS metrics APIs) — [github.com/chaoss/augur](https://github.com/chaoss/augur)
- OpenSSF Scorecard **[bg]**: automated checks such as Code-Review, Maintained, Branch-Protection, CI-Tests, Signed-Releases and Dangerous-Workflow, scored 0–10. A weekly BigQuery dataset covers about 1M repos — [scorecard.dev](https://scorecard.dev/); [github.com/ossf/scorecard](https://github.com/ossf/scorecard). Scorecard is a *point-in-time* tool: historical scores exist only from the cron dataset's start, roughly 2021.
- Truck factor **[bg]**: Avelino, Passos, Hora, Valente, "A novel approach for estimating truck factors" (ICPC 2016), with tool [github.com/aserg-ufmg/Truck-Factor](https://github.com/aserg-ufmg/Truck-Factor). It uses degree-of-authorship over files and is computable per time window for longitudinal series.
- The Census III finding that "the most widely used FOSS is developed by only a handful of contributors" supports reporting truck factor or contributor concentration for selected projects — [Linux Foundation press release, Census III](https://linuxfoundation.org/press/open-source-usage-trends-and-security-challenges-revealed-in-new-study)

### Inferences
- A minimal, defensible metric set for phase 1 (monthly panel per project), most of it computable from git alone:
  - commits, distinct authors, and distinct committers
  - lines added/deleted (churn), with vendored and generated paths excluded
  - files touched per commit
  - newcomer count: first-ever commit in month m
  - newcomer retention: share of newcomers with another commit 6 or 12 months later
  - contributor turnover: authors active in m-12 but absent in m..m+11
  - truck factor and Gini/Herfindahl concentration of commits
  - message length (and, if wanted, `Co-authored-by` / AI-assistant trailers as a treatment-intensity proxy)
- For GitHub-native projects, add from the API: PR open-to-merge latency, time to first review or comment (excluding bots), review rounds, PR acceptance rate, and issue time to first response. For mailing-list projects, compute the equivalents from patch threads (see §4).
- Use CHAOSS names and definitions for metrics, so results map onto a recognized vocabulary.

### Gaps
- I did not re-fetch the CHAOSS metric pages or confirm GrimoireLab and Augur's current maintenance status in this session.

---

## 3. Defensible project selection

### Takeaway
Combine at least two independent "importance" signals: (a) usage or dependency centrality, from Census III, deps.dev or ecosyste.ms dependents, or Debian popcon for C/system software; and (b) the OpenSSF Criticality Score or the LF critical-projects list. Then filter on longevity (the project predates about 2015 and is still active) and on data availability (hosting regime, §4). Pre-register the rule and publish the candidate list with retrieval timestamps.

### Cited Findings
- **Census III** (published Dec 4, 2024) is a joint effort of the Linux Foundation, the Harvard Laboratory for Innovation Science and OpenSSF, by Frank Nagle, Kate Powell, Richie Zitomer and David A. Wheeler. It covers more than 12 million observations of FOSS libraries in production applications at more than 10,000 companies, using SCA data from FOSSA, Snyk, Sonatype and Black Duck. Licensed CC BY-ND 4.0 — [LF press release](https://linuxfoundation.org/press/open-source-usage-trends-and-security-challenges-revealed-in-new-study); [report PDF](https://www.linuxfoundation.org/hubfs/LF%20Research/lfr_censusiii_120424a.pdf)
  - Census III is at the *application-library* level (npm, Maven, PyPI and similar). It does not rank system software such as PostgreSQL or ffmpeg directly — [LF press release](https://linuxfoundation.org/press/open-source-usage-trends-and-security-challenges-revealed-in-new-study)
  - Census II (2022) is the predecessor, giving a cross-check for rank stability **[bg]** — [LF Census II](https://www.linuxfoundation.org/research/census-ii-of-free-and-open-source-software-application-libraries)
- **OpenSSF Criticality Score**: published CSV and BigQuery lists (see §2) — [Google OSS blog](https://opensource.googleblog.com/2020/12/finding-critical-open-source-projects.html?m=0)
- **LF critical-projects**: a curated list that tries to correct Criticality Score false positives — [github.com/linuxfoundation/critical-projects](https://github.com/linuxfoundation/critical-projects)
- **ecosyste.ms critical set**: the founder reports the PyPI "critical" set is currently 523 packages, chosen from the dependency graph "by a different method and for a different purpose" than other lists — [nesbitt.io, 2026-05-13](https://nesbitt.io/2026/05/13/showing-our-work)
- **[bg]** Other selection inputs:
  - deps.dev dependents counts — [deps.dev](https://deps.dev/)
  - Debian Popularity Contest install and vote counts per binary package, good for C/system tools such as libpq, ffmpeg and sqlite — [popcon.debian.org](https://popcon.debian.org/)
  - PyPI downloads (BigQuery `bigquery-public-data.pypi.file_downloads`, [pypistats.org](https://pypistats.org/))
  - npm downloads API — [github.com/npm/registry/blob/main/docs/download-counts.md](https://github.com/npm/registry/blob/main/docs/download-counts.md)
  - Sovereign Tech Agency (formerly Sovereign Tech Fund) investment portfolio, a public-funding signal of criticality — [sovereign.tech/tech](https://www.sovereign.tech/tech)
  - NumFOCUS sponsored and affiliated projects (matplotlib, numpy, pandas and others) — [numfocus.org/sponsored-projects](https://numfocus.org/sponsored-projects)
  - Apache top-level projects (machine-readable JSON at projects.apache.org) — [projects.apache.org](https://projects.apache.org/)
  - OpenDigger OpenRank as a network-centrality signal — [github.com/X-lab2017/open-digger](https://github.com/X-lab2017/open-digger)

### Inferences
- A defensible, pre-registerable selection recipe:
  1. Build a candidate union from Census III top lists, the LF critical-projects list, Criticality Score top-N, and ecosyste.ms critical packages, plus a hand-curated system-software list (DBs, codecs, compilers, kernels), justified by Debian popcon and deps.dev dependents.
  2. Keep projects whose first commit predates 2015 and that had at least 12 active months in 2019–2022, so pre-period trends can be estimated.
  3. Stratify by hosting regime (GitHub-native PR workflow vs. mirror plus mailing list vs. a 2023–2025 migration) and by language (to support language-based controls, §6).
  4. Record the list version, retrieval date, and score for each project.
- Download-count series (PyPI/npm) are heavily distorted by CI and mirrors. Use them only as ranks, never as effect outcomes.
- Census III's CC BY-ND license means rankings can be cited but not redistributed in modified form. Reference them; do not re-publish a modified table.

### Gaps
- I did not fetch the actual Census III top-package ranking (it sits in the PDF), the current Sovereign Tech Agency portfolio, or ecosyste.ms's methodology for its "critical" flag.

---

## 4. Hosting pitfalls for the example projects

### Takeaway
Several "foundational" projects are **not GitHub-native**. For them, the GitHub repo is a read-only mirror: commits are complete, but PR, issue and review data on GitHub is absent or meaningless. Review happens on mailing lists, patchwork, commitfest, Phabricator (LLVM before Sept 2023), Fossil (SQLite), or a new Forgejo forge (FFmpeg since mid-2025; a GCC experiment). Workflow migrations are themselves structural breaks that can masquerade as LLM effects.

### Cited Findings
- **PostgreSQL**: the GitHub repo is described as "Mirror of the official PostgreSQL GIT repository", with the note "this is just a *mirror* - we don't work with pull requests on github". Contributors are pointed to the wiki's Submitting_a_Patch page — [github.com/postgres/postgres](https://github.com/postgres/postgres); [wiki.postgresql.org/wiki/Submitting_a_Patch](https://wiki.postgresql.org/wiki/Submitting_a_Patch)
  - **[bg]** Review happens on the pgsql-hackers list and is tracked at [commitfest.postgresql.org](https://commitfest.postgresql.org/). The canonical repo is git.postgresql.org. History was converted from CVS and goes back to the 1996 Postgres95 import, so early author metadata is coarse: committers committed on behalf of authors, with credit given in commit messages.
- **FFmpeg**:
  - The FFmpeg 8.0 "Huffman" news entry (Aug 22, 2025) says the project "started to modernize its infrastructure" and "recently started to accept contributions via a new forge", code.ffmpeg.org, a Forgejo instance — [ffmpeg.org news](https://ffmpeg.org/index.html)
  - The current developer docs say: "All proposed code changes should be submitted for review to Forgejo or the development mailing list." Mailing-list patches should use `git send-email` and are tracked on patchwork.ffmpeg.org — [ffmpeg.org/developer.html](https://ffmpeg.org/developer.html)
  - The developer docs also let contributors add an LLM-based reviewer ("Forgejo Fairy") to a pull request, a direct, dated AI-tooling intervention inside the project — [ffmpeg.org/developer.html](https://ffmpeg.org/developer.html)
  - In July 2025 ffmpeg-devel polled Forgejo vs. GitLab. Proposals included turning the old main repo on git.videolan.org into a mirror. A list member called the dual mailing-list plus forge setup confusing — [ffmpeg-devel VOTE thread, July 2025](https://ffmpeg.org/pipermail/ffmpeg-devel/2025-July/346969.html); [announce patch](https://ffmpeg.org/pipermail/ffmpeg-devel/2025-July/347148.html)
  - Nov 10, 2026 news covers CI sponsorship from GitHub and Blacksmith (infrastructure, not a review-process change) — [ffmpeg.org news](https://ffmpeg.org/index.html)
- **LLVM**: PRs became the recommended review tool for all of llvm-project on Sept 1, 2023, with Phabricator planned read-only from Oct 1, 2023. Phabricator had been the review tool since 2012. The migration tracking issue closed on Sept 9, 2023 — [LLVM Discourse reminder](https://discourse.llvm.org/t/pull-request-migration-reminder-sept-1-oct-1/73043); [MaskRay reflections](https://maskray.me/blog/2023-09-09-reflections-on-llvm-switch-to-github-pull-requests); [GitHub issue #63295](https://github.com/llvm/llvm-project/issues/63295)
  - **Correction to the prompt's premise:** the *repository* moved to GitHub in 2019 **[bg]**, but *code review* moved to GitHub PRs only in Sept 2023. That puts a review-workflow break about 10 months after ChatGPT's release. **[bg]** LLVM issues moved from Bugzilla to GitHub Issues in early 2022.
- **GCC**:
  - Sourceware's Forgejo forge (forge.sourceware.org) launched as an experiment in autumn 2024. GCC's PR template says the forge is "a trial", that PRs "may be forgotten or ignored", and that patches meant for inclusion should use the email workflow. Sign-up was limited to sourceware.org and gcc.gnu.org addresses — [GCC wiki: ForgeExperiment](https://gcc.gnu.org/wiki/ForgeExperiment); [GCC PR template](https://gnu.googlesource.com/gcc/+/99cd28c4733c2f06594f5268276815545785a240/.forgejo/PULL_REQUEST_TEMPLATE.md); [Sourceware Q3 2025 update](https://gcc.gnu.org/pipermail/gcc/2025-October/246898.html)
  - **[bg]** GCC moved from SVN to git in January 2020, and its bug tracker is Bugzilla (gcc.gnu.org/bugzilla).
- **Linux kernel**: development runs on mailing lists. PaStA (Ramsauer, Lohmann, Mauerer, 2019, GPLv2) tracks patch revisions on lists and maps them to upstream commits, with high accuracy on LKML. Its authors note that commits are often squashed and amended on the fly, which breaks the direct list-to-commit link — [PaStA paper, arXiv 1902.03147](https://arxiv.org/pdf/1902.03147)
  - Jiang, Adams and Khomh (ESEM 2014) compared techniques for linking patch emails to each other and to commits — [ESEM 2014 paper](https://mcis.cs.queensu.ca/publications/2014/esem14jojo.pdf)
  - MSR 2018 Data Showcase: a multi-level Linux kernel patchwork dataset covering nine years of patches and discussion — [MSR 2018 Data Showcase](https://2018.msrconf.org/event/msr-2018-data-showcase-papers-a-multi-level-dataset-of-linux-kernel-patchwork)
  - Measuring kernel code review with PaStA plus gitdm — [Erdamar 2021, LPC](https://lpc.events/event/11/contributions/905/attachments/773/1795/Erdamar_2021_Measuring-Code-Review-in-the-Linux-Kernel.pdf); ignored-patches analysis — [Duda 2019, FAU thesis](https://osr.cs.fau.de/wp-content/uploads/2020/03/duda_2019.pdf)
  - **[bg]** public-inbox archives at [lore.kernel.org](https://lore.kernel.org/) can be cloned as git repositories of mail, which suits bulk mining. github.com/torvalds/linux is a mirror that does not take PRs.
- **[bg] Other projects:**
  - **CPython**: moved to GitHub in Feb 2017 (from Mercurial). Issues moved from bugs.python.org to GitHub in April 2022, so GitHub issue counts show a migration artifact in 2022 ([PEP 581](https://peps.python.org/pep-0581/)).
  - **SQLite**: developed in Fossil at [sqlite.org/src](https://sqlite.org/src/). The GitHub repo is a mirror, and the project does not accept outside code contributions ([sqlite.org/copyright.html](https://www.sqlite.org/copyright.html)).
  - **curl**: GitHub-native PR workflow ([github.com/curl/curl](https://github.com/curl/curl)).
  - **Git**: developed on the git@vger.kernel.org mailing list ([lore.kernel.org/git](https://lore.kernel.org/git/)). github.com/git/git is a mirror. GitGitGadget turns GitHub PRs into mail patches ([gitgitgadget.github.io](https://gitgitgadget.github.io/)).
  - **d3**: split into many `d3-*` module repos around v4 (2016). Longitudinal analysis of `d3/d3` alone misses most code after the split.
  - **plotly**: plotly.js and plotly.py are separate repos.
- **[bg]** Mailing-list mining tools: GrimoireLab Perceval (mbox/pipermail backends) and Kaiaulu (R) — [github.com/sailuh/kaiaulu](https://github.com/sailuh/kaiaulu)

### Inferences
- Classify each project into a **data regime**, and only compare like with like for PR- and review-based outcomes:
  - (A) GitHub-native PRs over the whole window: matplotlib, numpy, pandas, curl, plotly
  - (B) mirror plus mailing list or patchwork/commitfest: PostgreSQL, Linux, Git, GCC
  - (C) migrated mid-window: LLVM (Phabricator to PRs, Sept 2023), FFmpeg (list to Forgejo plus list, mid-2025), CPython issues (bpo to GitHub, 2022)
  - (D) non-git or closed contribution: SQLite (Fossil)
- Commit-based outcomes (activity, churn, authorship) are comparable across all regimes if they are computed from the canonical git repo, not the API.
- The README's "GitHub-hosted only" scope would exclude PostgreSQL's real review process, FFmpeg's after mid-2025, and Linux/Git/GCC entirely. Either relabel the scope as "git-hosted; review data from GitHub where native", or add an email/patchwork collector (public-inbox or mbox via Perceval).
- For regime (C), include the migration date as a separate dummy or break in the model. Otherwise, LLVM's Sept 2023 switch and FFmpeg's 2025 forge would load onto "post-ChatGPT" coefficients.
- FFmpeg's "Forgejo Fairy" LLM reviewer is a concrete, dated, in-project AI intervention. It is a candidate natural-experiment marker for FFmpeg-specific analyses.

### Gaps
- I could not confirm whether FFmpeg's git.videolan.org repo is now formally a mirror of code.ffmpeg.org, or which is canonical as of Nov 2026. I also did not verify whether the GitHub FFmpeg/FFmpeg mirror still exists.
- The current status (Nov 2026) of GCC's forge experiment beyond the Q3 2025 update is unknown.
- I did not verify whether a static archive of LLVM's Phabricator reviews (reviews.llvm.org) is still downloadable for pre-2023 review metrics.

---

## 5. Pitfalls in git history analysis

### Takeaway
Git timestamps and identities are unreliable without cleaning. Use author date for "when the work was written" and committer date for "when it landed", and know that rebases and squash-merges rewrite both. Bots, mailmap gaps, vendored or generated code, CVS/SVN imports and repo splits or merges all create artifacts large enough to fake a trend break.

### Cited Findings
- Commits are often squashed and amended "on the fly" in list-based workflows, which loses the direct link between list history and repository commits — [PaStA, arXiv 1902.03147](https://arxiv.org/pdf/1902.03147)
- **[bg]** Flint, Chauhan, Dobolyi, "Escaping the Time Pit: Pitfalls and Guidelines for Using Time-Based Git Data" (MSR 2021) catalogs author/committer date divergence, rebases, bogus dates (e.g., 1970 or future dates), and timezone misuse — [arXiv 2103.11339](https://arxiv.org/abs/2103.11339)
- **[bg]** Bird et al., "The Promises and Perils of Mining Git" (MSR 2009) — [IEEE](https://ieeexplore.ieee.org/document/5069475); Kalliamvakou et al., "The Promises and Perils of Mining GitHub" (MSR 2014; EMSE 2016) — [ACM DL](https://dl.acm.org/doi/10.1145/2597073.2597074)
- **[bg]** Bots:
  - BoDeGHa (Golzadeh et al.), a GitHub-activity bot classifier — [github.com/mehdigolzadeh/BoDeGHa](https://github.com/mehdigolzadeh/BoDeGHa)
  - BIMAN (Dey et al., MSR 2020, "Detecting and Characterizing Bots that Commit Code") — [arXiv 2003.03172](https://arxiv.org/abs/2003.03172)
  - RABBIT, a newer activity-based classifier — [github.com/natarajan-chidambaram/RABBIT](https://github.com/natarajan-chidambaram/RABBIT)
- **[bg]** Identity merging:
  - `.mailmap` (when the project maintains one)
  - gambit (Gote & Zingg, MSR 2021), a name-disambiguation tool — [arXiv 2103.05609](https://arxiv.org/abs/2103.05609)
  - GrimoireLab SortingHat
  - WoC's precomputed author aliases (§1)

### Inferences
Practical rules for little-helper:
1. Store both `author_date` and `committer_date` with their UTC offsets. Bucket on author date for "work produced", on committer date for "integration throughput", and normalize to UTC. Flag commits with author_date before the repo's first commit, after the retrieval date, or with author–committer gaps over 1 year.
2. Record whether a project squash-merges (PRs with one merged commit vs. many). Squash-merging inflates "lines per commit" and deflates "commit count". Count PRs, not commits, as the unit of contribution for GitHub-native projects, or use `--first-parent` on the main branch.
3. Remove or flag bots with a name regex (`[bot]`, dependabot, renovate, pre-commit-ci, github-actions), and then a BoDeGHa or RABBIT pass for PR/issue actors. Bot PRs (dependabot launched 2019, renovate) are a secular trend that overlaps the LLM window.
4. Apply `.mailmap`, then gambit-style disambiguation. For list-based projects, also parse `Signed-off-by`, `Reviewed-by`, `Co-authored-by` and `Reported-by` trailers (in PostgreSQL's older CVS-era commits, author credit sits in the message body).
5. Exclude vendored, third-party and generated paths from churn and LOC: `vendor/`, `third_party/`, `extern/`, lockfiles, `*.min.js`, generated parsers, test fixtures, and `.gitattributes` `linguist-vendored`/`linguist-generated` entries. Large one-off imports (e.g., relicensing or reformatting commits) should be dropped via an outlier rule (e.g., over 99.9th percentile of churn) and listed in `.git-blame-ignore-revs` where projects provide one.
6. CVS/SVN imports: early history (e.g., PostgreSQL 1996, matplotlib's SVN era) may have a single committer identity, synthesized merges, and missing branch topology. Start the analysis panel at a documented date (e.g., 2005 or later) or treat the import era separately.
7. Monorepo moves and splits: LLVM's 2019 monorepo merged many repos, and d3's split went the other way. Analyze at the "project" level, mapping several repos to one project.
8. Timezones: use UTC offsets for "time of day" or "weekend" outcomes only, and only after checking for bogus +0000 offsets from tooling.

### Gaps
- Tool-maintenance status for BoDeGHa, RABBIT and gambit was not verified in this session.

---

## 6. Statistical methods for before/after-LLM analyses

### Takeaway
The current standard is (i) event-study and difference-in-differences designs with heterogeneity-robust estimators (Callaway & Sant'Anna; Borusyak–Jaravel–Spiess; Sun & Abraham), (ii) synthetic or generalized synthetic controls when there are few treated units, and (iii) interrupted time series (ITS) with seasonality controls when no control group exists. Recent repo-level exemplars use less-AI-exposed languages (R vs. Python), Copilot-supported vs. unsupported languages, or matched non-adopter repos as controls.

### Cited Findings
**Methods exemplars on GitHub/OSS (methods only)**
- Batikas, "Generative AI and Market Structure in Open-Source Software: Evidence from GitHub Copilot" (NBER SI 2026 slides): Python (Copilot-supported) as treated, R as comparison, estimated with Callaway & Sant'Anna (2021), chosen for its handling of pre-treatment trends — [NBER slides](https://conference.nber.org/conf_papers/f242199/f242199.slides.pdf)
- arXiv 2510.10165: DiD on OSS projects grouped by primary language, with Copilot-endorsed languages as the treatment group. It reports effects concentrated in peripheral developers (the estimator was not confirmed) — [arXiv 2510.10165](https://arxiv.org/html/2510.10165v3)
- Song, Agarwal, Wen: exploit *staggered* Copilot adoption across projects, using the generalized synthetic control method — [search result summary](https://cn.linkedin.com/in/yukun-yang) (primary paper URL not retrieved)
- He, Miller, Agarwal, Kästner, Vasilescu, "Speed at the Cost of Quality: How Cursor AI Increases Short-Term Velocity and Long-Term Complexity in Open-Source Projects" (MSR '26): DiD of Cursor-adopting repos vs. a matched control group of similar non-adopters; outcomes are velocity, static-analysis warnings and code complexity; panel GMM for the dynamic feedback from quality to velocity — [arXiv 2511.04427](https://arxiv.org/abs/2511.04427). A search summary says this paper uses the Borusyak et al. imputation estimator, which the abstract does not state — [search result](https://www.arxiv.org/pdf/2511.04427)
- arXiv 2605.25438 (Claude Code adoption): staggered DiD with the Callaway & Sant'Anna estimator — [arXiv 2605.25438](https://arxiv.org/html/2605.25438)
- arXiv 2601.13597, "AI IDEs or Autonomous Agents? Measuring the Impact of Coding Agents on Software Development" — another recent exemplar of adoption-based designs — [arXiv 2601.13597](https://arxiv.org/pdf/2601.13597)

**Core econometric references [bg]**
- Callaway & Sant'Anna (2021), "Difference-in-Differences with multiple time periods", *J. Econometrics* — [doi:10.1016/j.jeconom.2020.12.001](https://doi.org/10.1016/j.jeconom.2020.12.001)
- Sun & Abraham (2021), event studies with heterogeneous effects, *J. Econometrics* — [doi:10.1016/j.jeconom.2020.09.006](https://doi.org/10.1016/j.jeconom.2020.09.006)
- Borusyak, Jaravel, Spiess (2024), imputation estimator, *REStud* — [arXiv 2108.12419](https://arxiv.org/abs/2108.12419)
- Goodman-Bacon (2021), decomposition of TWFE bias, *J. Econometrics* — [doi:10.1016/j.jeconom.2021.03.014](https://doi.org/10.1016/j.jeconom.2021.03.014)
- Abadie, Diamond, Hainmueller (2010), synthetic control, *JASA* — [doi:10.1198/jasa.2009.ap08746](https://doi.org/10.1198/jasa.2009.ap08746)
- Xu (2017), generalized synthetic control, *Political Analysis* — [doi:10.1017/pan.2016.2](https://doi.org/10.1017/pan.2016.2)
- Arkhangelsky et al. (2021), synthetic DiD, *AER* — [doi:10.1257/aer.20190159](https://doi.org/10.1257/aer.20190159)
- Rambachan & Roth (2023), "A More Credible Approach to Parallel Trends" (HonestDiD sensitivity), *REStud* — [doi:10.1093/restud/rdad018](https://doi.org/10.1093/restud/rdad018)
- Bernal, Cummins, Gasparrini (2017), ITS tutorial, *Int. J. Epidemiology* — [doi:10.1093/ije/dyw098](https://doi.org/10.1093/ije/dyw098)

**Python tooling [bg]**
- `pyfixest`: fast fixed effects, Sun–Abraham-style event studies, `did2s`, Gardner two-stage — [github.com/py-econometrics/pyfixest](https://github.com/py-econometrics/pyfixest)
- `differences`: Callaway–Sant'Anna in Python — [github.com/bernardodionisi/differences](https://github.com/bernardodionisi/differences); `csdid` port — [github.com/d2cml-ai/csdid](https://github.com/d2cml-ai/csdid)
- `pysyncon`: synthetic control — [github.com/sdfordham/pysyncon](https://github.com/sdfordham/pysyncon)
- `statsmodels` SARIMAX / segmented regression for ITS; `tfcausalimpact` for Bayesian structural time series

**Key dates [bg]**
- Copilot technical preview: June 29, 2021
- Copilot general availability: June 21, 2022, free for verified students and maintainers of popular OSS projects — [GitHub blog](https://github.blog/news-insights/product-news/github-copilot-is-generally-available-to-all-developers/)
- ChatGPT release: Nov 30, 2022 — [OpenAI](https://openai.com/index/chatgpt/)
- Later agentic tools (Cursor, Claude Code, Copilot agent mode) create additional, staggered "treatments" in 2024–2026.

### Inferences
- With a few dozen foundational projects, a common-shock design (one date, Nov 30, 2022) has no clean control. Every project is "exposed". Options:
  1. **ITS per project**, with project-specific linear or spline trends, month-of-year and holiday dummies (December dips; October Hacktoberfest PR spikes on GitHub), and a level-plus-slope change at the event. Fit with Newey–West or ARIMA errors, report pooled estimates with random effects, and add placebo break dates (e.g., Nov 2020, Nov 2021) to show the method does not "find" breaks everywhere.
  2. **Exposure-intensity DiD**: treat exposure as continuous or tiered. Candidates: language exposure (Python/JS high vs. R/Fortran/assembly-heavy C low, following Batikas and 2510.10165), observable AI-use markers (`Co-authored-by` AI trailers, AI-disclosure labels, tool config files such as `.cursorrules`, `CLAUDE.md`, `.github/copilot-instructions.md`), or dated project AI policies (e.g., the FFmpeg Forgejo Fairy LLM reviewer, §4).
  3. **Staggered adoption** (Callaway & Sant'Anna or Borusyak et al.) when adoption markers vary by project and date, with never- or not-yet-treated projects as controls. Avoid plain two-way fixed effects, which is biased under heterogeneous timing (Goodman-Bacon).
  4. **Synthetic control or generalized SCM** for single high-profile projects (e.g., one treated repo vs. a donor pool of comparable repos).
- Always show event-study leads (pre-trends) and run a HonestDiD-style sensitivity check. Account for secular trends: pre-2022 growth or decline, the COVID-19 2020 activity shock, dependabot and bot growth, and the 2022–2025 workflow migrations (§4).
- Use log or asinh transforms for counts (or Poisson PPML via pyfixest) because activity metrics are heavy-tailed.

### Gaps
- I did not retrieve the full texts to confirm estimator choices for 2510.10165 and the Song/Agarwal/Wen paper, or the matching details in He et al. (MSR '26).
- Python implementations of Callaway–Sant'Anna are less mature than the R `did` package. Many studies run R's `did`/`HonestDiD`, which may be a reproducibility consideration for a uv-based project.

---

## 7. Longitudinal performance-tracking infrastructure and research on performance over commit history

### Takeaway
Several foundational projects already publish *historical* benchmark series: asv dashboards for the scientific-Python stack, speed.python.org and pyperformance, perf.rust-lang.org, LLVM LNT and the compile-time tracker, Mozilla Perfherder, Chromium's perf dashboard, and OpenBenchmarking.org. Reusing these is far cheaper than re-benchmarking old commits. Old-commit rebuilds and cloud-noise control are the main reproducibility hazards. PostgreSQL has no confirmed standing performance farm.

### Cited Findings
**Project-run infrastructure**
- **PostgreSQL**: a pgbench run was added to the buildfarm in 2006, with developers suggesting per-machine longitudinal views rather than cross-machine comparisons (machine upgrades and background load skew results) — [pgsql-hackers 2006 thread](https://postgrespro.com/list/thread-id/1681184). A 2012 "performance-test farm" proposal by Tomas Vondra aimed "to find unexpected regressions"; Greg Smith suggested short-vs-long moving averages as the regression signal — [pgsql-hackers 2012](https://postgresql.org/message-id/4F7BC17C.1040908%402ndQuadrant.com). In 2020, Tom Lane noted the regression tests "are not really intended for performance testing" and buildfarm timings are often too noisy, though the buildfarm records per-step durations — [2020 thread](https://postgrespro.com/list/thread-id/2495919). Buildfarm: **[bg]** [buildfarm.postgresql.org](https://buildfarm.postgresql.org/)
- **[bg] Scientific Python (asv):**
  - airspeed velocity, which benchmarks across commit history and has `asv continuous`/`asv find` for regression bisection — [asv.readthedocs.io](https://asv.readthedocs.io/)
  - Public asv dashboards: numpy [pv.github.io/numpy-bench](https://pv.github.io/numpy-bench/); scipy [pv.github.io/scipy-bench](https://pv.github.io/scipy-bench/); pandas [asv-runner.github.io/asv-collection/pandas](https://asv-runner.github.io/asv-collection/pandas/); astropy [spacetelescope.github.io/bench/astropy-benchmarks](https://spacetelescope.github.io/bench/astropy-benchmarks/)
  - matplotlib keeps an asv suite in its repo, but I could not confirm a public dashboard.
- **[bg] CPython:**
  - [speed.python.org](https://speed.python.org/) (Codespeed)
  - [pyperformance](https://github.com/python/pyperformance)
  - Faster CPython results archive — [github.com/faster-cpython/benchmarking-public](https://github.com/faster-cpython/benchmarking-public)
- **[bg] Rust:** [perf.rust-lang.org](https://perf.rust-lang.org/), compile-time benchmarks per merged PR via rustc-perf ([github.com/rust-lang/rustc-perf](https://github.com/rust-lang/rustc-perf)).
- **[bg] LLVM:** [lnt.llvm.org](https://lnt.llvm.org/) and [llvm-compile-time-tracker.com](https://llvm-compile-time-tracker.com/), which tracks instructions retired per commit and is low-noise.
- **[bg] Browsers:** Mozilla Perfherder ([treeherder.mozilla.org/perfherder](https://treeherder.mozilla.org/perfherder/)) and Chromium ([chromeperf.appspot.com](https://chromeperf.appspot.com/)).
- **[bg] FFmpeg FATE** ([fate.ffmpeg.org](https://fate.ffmpeg.org/)) is a correctness or regression test farm, not a performance one. FFmpeg benchmarking is ad hoc (e.g., checkasm `--bench`).
- **[bg] Linux kernel:** Intel 0-day/LKP posts automated performance-regression reports to LKML ([github.com/intel/lkp-tests](https://github.com/intel/lkp-tests)).
- **[bg] Third-party:**
  - [OpenBenchmarking.org](https://openbenchmarking.org/) / Phoronix Test Suite: historical results across software versions and hardware
  - [CodSpeed](https://codspeed.io/): CI benchmarking with instruction-count simulation to reduce noise
  - [Bencher](https://bencher.dev/): continuous benchmarking with statistical thresholds

**Academic work**
- Method-level performance evolution in 15 Java projects (739 commits, 1,499 method-level changes, JMH): 32.7% of method-level changes had measurable performance impact; regressions were 1.3 times more frequent than improvements; a dataset is provided — [arXiv 2508.07084](https://arxiv.org/abs/2508.07084)
- Traini et al. (TOSEM 2022, incl. Cortellessa, Bavota, Lanza): mined 20 systems with in-repo benchmarks. About 55% of refactoring commits caused a statistically significant performance change in at least one benchmark — [USI PDF](https://www.inf.usi.ch/faculty/lanza/PUBS/J/Trai2022a.pdf)
- CppPerf: an automated pipeline (CPPPERF-MINE) and benchmark (CPPPERF-DB) of real-world performance-improving C++ commits — [arXiv 2605.10890](https://arxiv.org/pdf/2605.10890)
- Performance-mutation-style work: traces bug-fixing commits to microbenchmarks and measures time and memory before and after, to derive performance mutation operators — [arXiv 2504.05851](https://arxiv.org/pdf/2504.05851)
- RegMiner mined 1,035 regressions over 147 projects in 8 weeks from commit histories (functional regressions, but its build-and-replay methodology carries over) — [arXiv 2109.12389](https://arxiv.org/pdf/2109.12389.pdf)
- Performance regression root-causing across versions — [Chen/Shang et al., TSE 2020](https://ece.uwaterloo.ca/~wshang/pubs/Jinfu2020TSE.pdf)
- **[bg]** Perphecy (Oliveira et al., ICST 2017): performance regression test selection from cheap static and dynamic indicators. GSO (2025) and SWE-Perf (2025) build optimization benchmarks from performance-improving commits in Python repos such as numpy and pandas, which provides ready-made commit-pair lists.
- **[bg]** Measurement-noise literature:
  - Mytkowicz et al., "Producing Wrong Data Without Doing Anything Obviously Wrong!" (ASPLOS 2009): environment size and link order bias
  - Curtsinger & Berger, "Stabilizer" (ASPLOS 2013)
  - Laaber, Scheuner, Leitner, "Software microbenchmarking in the cloud. How bad is it really?" (EMSE 2019)
  - Kalibera & Jones, "Rigorous Benchmarking in Reasonable Time" (ISMM 2013)
- **[bg]** Buildability of old commits: Tufano et al., "There and Back Again: Can you compile that snapshot?" (JSEP 2017) found that a majority of historical snapshots of Apache Java projects failed to compile.

### Inferences
- **Phase 2, cheapest path:** first harvest existing series (asv JSON results for numpy, scipy, pandas and astropy; speed.python.org; perf.rust-lang.org; LLVM compile-time tracker) and analyze them with the §6 ITS/DiD toolkit before building any benchmark runner.
- **If benchmarking commits yourself:**
  - Use asv (Python projects) or hyperfine and pyperf for CLI tools.
  - Pin the toolchain per era: Nix or conda-lock environments keyed to commit date, or Docker images of contemporaneous distro releases. Measure with instruction counts (`perf stat -e instructions`, valgrind/cachegrind, as CodSpeed and the LLVM tracker do) in addition to wall-time.
  - Use dedicated bare-metal machines with turbo, SMT and frequency scaling disabled and CPU isolation. Interleave old and new commits (randomized A/B order) and report confidence intervals from repeated runs.
- **Sampling:** benchmark at release tags or monthly first-parent commits, then bisect only where change-point detection finds steps. asv's `find` and e-divisive or PELT change-point methods (`ruptures` in Python) support this.
- PostgreSQL has no ready-made historical perf series. You would need pgbench or TPC-H-like runs across release branches, where building old versions with modern compilers is a known hurdle.

### Gaps
- I did not verify which asv dashboards remain live in Nov 2026, or whether a matplotlib public dashboard exists.
- I found no confirmation of a currently operating PostgreSQL performance farm; the available sources are 2006–2020 mailing-list threads.
- I did not confirm whether the CppPerf and arXiv 2508.07084 datasets are publicly released.

---

## 8. Reproducibility best practices for MSR studies

### Takeaway
Pin everything that moves: clone SHAs (or SWHIDs), API retrieval timestamps, list versions for project selection, tool versions (uv lockfile), and raw API responses. Deposit a versioned dataset plus code with a DOI (Zenodo), with personal data pseudonymized, and publish open access as GitHub's AUP requires.

### Cited Findings
- GitHub's AUP conditions research use of public data on open-access publication and restricts reuse of personal information — [GitHub Acceptable Use Policies](https://docs.github.com/en/site-policy/acceptable-use-policies/github-acceptable-use-policies)
- SWH asks researchers to cite the MSR 2019 dataset paper and offers versioned graph exports, giving a stable, citable snapshot of commit graphs — [SWH dataset page](https://docs.softwareheritage.org/devel/swh-export/graph/dataset.html); [Zenodo record](https://zenodo.org/record/2583978)
- GitHub API values can vary between responses because requests are served from multiple regions. Response headers are authoritative over `/rate_limit`, so a crawler should log headers per request — [GitHub Docs: REST rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- **[bg]** Zenodo–GitHub integration mints a DOI per release — [GitHub Docs: referencing and citing content](https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content). SWHIDs give intrinsic, persistent identifiers for snapshots, revisions and directories — [SWHID spec](https://www.swhid.org/). Software Heritage "Save Code Now" archives a repo on demand — [archive.softwareheritage.org/save](https://archive.softwareheritage.org/save/)
- **[bg]** González-Barahona & Robles, "On the reproducibility of empirical software engineering studies based on data retrieved from development repositories" (EMSE 2012) — [doi:10.1007/s10664-011-9181-9](https://doi.org/10.1007/s10664-011-9181-9). The MSR conference's open-science policy expects replication packages — [MSR 2026 open science policy](https://2026.msrconf.org/track/msr-2026-technical-papers)

### Inferences
Checklist for little-helper:
1. A `projects.yaml` per project: canonical clone URL, mirror URL, hosting regime (§4), the selection-source list name, version and retrieval date, and the HEAD SHA analyzed.
2. Raw API responses cached as compressed JSONL with a `retrieved_at` UTC timestamp, query parameters, and `x-ratelimit-*` headers. Derived polars Parquet tables are always rebuilt from that cache.
3. A deterministic analysis window (e.g., data up to 2026-10-31) in config, so reruns are not silently extended.
4. Request each analyzed repo snapshot through SWH Save Code Now and record its SWHID, so the history can be re-obtained if the repo is rewritten or deleted.
5. Pseudonymize emails (salted hash) in published tables, keep the salt private, and document identity-merge rules.
6. Tag a release, mint a Zenodo DOI, and include `uv.lock`, the exact Python version, and a `make reproduce` style entry point. For phase 2, record hardware (CPU model, microcode, governor), kernel, and compiler versions alongside every benchmark result.
7. Pre-register the event dates, outcome definitions and placebo dates (e.g., an OSF preregistration or a dated commit in the repo) before looking at post-2022 data.

### Gaps
- I did not verify SWHID's current standardization status (believed to have become an ISO/IEC standard in 2025) or the MSR 2026 open-science policy wording in this session.
