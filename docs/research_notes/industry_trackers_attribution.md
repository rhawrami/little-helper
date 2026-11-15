# Industry & Community Trackers of AI Usage in GitHub/OSS, and Detecting AI Authorship in Git Data

Research date: 2026-11-12. All numbers are dated to their source. "Secondary" marks figures taken from coverage or search summaries rather than the primary document. Vendor conflicts of interest (COI) are noted inline.

---

## 1. GitHub Octoverse 2023 → 2026: platform-wide numbers

### Takeaway
Octoverse 2026 (Oct 28, 2026) shows a step change: platform commits went from about 12.9B (2025) to 34.3B (2026), merged PRs from 538M to 1.3B, and over 40% of PRs in Sept 2026 began as a coding agent's draft. Octoverse 2026 restated earlier years using public+private data and an Oct–Sep window, so its numbers **cannot be compared directly** with the public-only figures in the 2023–2025 editions.

### Cited Findings
**Octoverse 2026** (published Oct 28, 2026; updated Nov 6, 2026; window Oct 1, 2025–Sep 30, 2026; public+private unless noted) — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- Methodology change: 2024 and 2025 were recalculated on the new definitions (public+private, Oct–Sep window). Earlier Octoverse reports used public-only data and a Sep 1–Aug 31 window. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- Pushes 17.9B (2026) vs 6.7B (2025) vs 5.2B (2024). Commits 34.3B vs 12.9B vs 10.0B. Merged PRs 1.3B (about 3.5M/day) vs 538M vs 402M. Actions jobs 45.4B vs 14.0B vs 8.0B. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- Monthly growth, Sept 2025 = 1× vs Sept 2026: commits about 6×, Actions 4.8×, pushes 4.5×, merged PRs 3.9×. Every series rose sharply after about June 2026. From June 2026 onward, about 55% of commits came from brand-new repositories. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- Public open source contributions: 2.5B (2026) vs 1.12B the prior year. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- **Agent-started PRs:** over 40% of PRs in Sept 2026 began with an agent's first draft, up from 17% in March 2026. That is about 110M agent-started PRs in September alone, roughly 6× March. 87% of agent-started PRs touched multiple files, vs 79% of other PRs. Agent PRs merged within two weeks rose from 83% (Feb 2026) to 90% (Sept 2026); the comparison group stayed near 86%. GitHub calls the agent signal a "floor" because not all agent use is detectable. It does not say how detection works. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- **AI involvement in merged PRs by language** (past 12 months): TypeScript 44.1%, Python 41.1%, Rust 40.4%, Java 21.2% (lowest). — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- **Agent config files:** among repos created in 2026, the average repo with an agent configuration file logged about 8× as many commits as the average new repo without one. GitHub says this is correlation, not causation. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- Developers: more than 225M (Sept 2026). US 38.3M, India 32.0M, China 12.4M, Brazil 10.2M. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- Languages by contributors: TypeScript #1, Python #2, JavaScript #3 (same order as 2025). Monthly contributor gains Sep 2025→Sep 2026: TS +3.62M, Python +3.23M, JS +1.82M. Rust grew fastest (reported +162%). — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- Copilot: 55% of monthly active users use agentic features (up from 35% a year earlier). Copilot cloud agent usage +230% YoY. 61% of users who picked models used more than one. No single model exceeded 25% of requests in Sept 2026. More than 30M Dependabot PRs merged. AI code review usage +90% YoY. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- Filtering: contributor counts exclude spam-flagged accounts, staff, and identifiable bots. Each push counts as one contribution regardless of how many commits it holds. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)

**Octoverse 2025** (published Oct 28, 2025; updated Feb 28, 2026; window Sep 1, 2024–Aug 31, 2025; mostly public data) — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)
- 180M+ developers. 36.2M joined in the year (+23%), about one per second. Nearly 80% of new developers used Copilot in their first week. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)
- 630M total repos, about 121M created in 2025. Roughly 986M–1B commits pushed (+25% YoY). 43.2M PRs merged per month on average (+23%). 518.7M PRs merged across public/OSS. 1.12B public/OSS contributions (+13%). — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)
- **TypeScript became #1 by monthly contributors in August 2025**: 2,636,006 contributors (+66.6% YoY), about 42k ahead of Python. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/); [Visual Studio Magazine](https://visualstudiomagazine.com/Articles/2025/10/31/TypeScript-Tops-GitHub-Octoverse-as-AI-Era-Reshapes-Language-Choices.aspx)
- AI: 4.3M+ AI-related repos. 1.13M+ public repos import an LLM SDK (+178% YoY), 693,867 of them created in the last 12 months. About 200k monthly contributors to generative AI projects (Aug 2025). 60% of the top-10 OSS projects by contributors are AI-focused (vllm, ollama, llama.cpp, openai/codex, transformers…). 50% of OSS projects have at least one Copilot-using maintainer. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)
- **Copilot coding agent created over 1M PRs between May and September 2025.** — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)
- Commit comments fell 27% YoY, while issue/PR comments were flat (+0.35%). — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)
- GitHub's follow-up analysis links AI tooling to the shift toward typed languages. — [GitHub Blog, Dec 9, 2025](https://github.blog/2025-12-09-why-ai-is-pushing-developers-toward-typed-languages/)

**Octoverse 2024** (Oct 2024)
- Python passed JavaScript as the most-used language on GitHub when all activity is counted. JavaScript still led on code pushes alone. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-2024/); [The Register](https://www.theregister.com/software/2024/11/05/githubs-most-used-language-isnt-javascript-anymore/1337119)
- Generative AI projects +98% YoY to about 137,000, more than 70,000 of them new public projects. Contributions to gen-AI projects +59%. Jupyter Notebook usage +92%. (Secondary summary; check the exact wording against the GitHub post.) — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-2024/); [InfoQ](https://www.infoq.com/news/2024/11/github-octoverse-2024)

**Other GitHub-reported series**
- Platform merged PRs grew from about 25M/month (Jan 2023) to about 90M/month (Mar 2026), per GitHub figures quoted in coverage of its maintainer-controls work (secondary). — [Visual Studio Magazine, Jun 30, 2026](https://visualstudiomagazine.com/articles/2026/06/30/github-extends-contribution-controls-from-prs-to-issues.aspx)

### Inferences
- The Octoverse 2026 restatement gives 12.9B commits for 2025, while Octoverse 2025 itself reported about 1B, a public-only push count. little-helper should never mix numbers across editions. Use a single edition's series, or the project's own counts.
- The jump after June 2026 and the 55% share from brand-new repos mean much of the "agent era" volume sits in new, throwaway or personal repos, not in established OSS. Project-level baselines (matplotlib, d3, etc.) are the right comparison, not GitHub-wide totals.
- GitHub excludes "identifiable bots" from contributor counts. Agent bot accounts such as `copilot-swe-agent[bot]` are therefore probably missing from contributor-based metrics, though possibly not from commit or PR counts. Inference; GitHub does not spell this out.

### Gaps
- **Octoverse 2023** figures (e.g., about 65k public gen-AI projects, +248% YoY; 100M+ developers; about 4.5B contributions) are from memory and were **not verified** in this session. Check [github.blog/news-insights/octoverse](https://github.blog/news-insights/octoverse/) before citing.
- Octoverse 2026 does not say how "agent-started" PRs are detected (bot authors, branch prefixes, Copilot telemetry, or something else), and it gives no public-only agent share.
- No GitHub-published breakdown of agent share for established, high-star OSS repos.

---

## 2. Live/community trackers of AI-agent activity on GitHub

### Takeaway
Three kinds of tracker exist: (a) **PR Arena** (prarena.ai, by GitHub user `aavetis`), which counts PRs per agent via branch prefixes and bot authors; (b) commit-trailer counters such as **claudescode.dev**, **Paul Kinlan's AI Focus analysis**, and **SemiAnalysis**, which put Claude Code at about 4–4.5% of public GitHub commits in Feb–Mar 2026; and (c) academic datasets (**AIDev**, about 933k agent PRs to Aug 2025). All of them rely on self-identifying markers, so they undercount, and merge rates are inflated by self-merging in personal repos.

### Cited Findings
**PR Arena** — [github.com/aavetis/PRarena](https://github.com/aavetis/PRarena) (dashboard at prarena.ai; noted by [Simon Willison](https://simonwillison.net/b/9034))
- Tracks All, Ready (non-draft) and Merged PRs for Copilot (branch `copilot/`), Codex (branch `codex/`), Cursor (branch `cursor/`), Devin (author `devin-ai-integration[bot]`), Codegen (`codegen-sh[bot]`) and Jules (`google-labs-jules[bot]`), using GitHub search queries. It says it "updates regularly" but gives no as-of date. **Claude Code is not tracked**, since it has no unique branch or bot. — [PRarena README](https://github.com/aavetis/PRarena)
- Ready / merged / merge rate, as displayed when fetched on 2026-11-12 (no as-of date on the page): Codex 8,731,688 / 7,916,792 / 90.67%. Copilot 1,654,405 / 1,587,083 / 95.93%. Cursor 1,459,156 / 1,428,375 / 97.89%. Devin 333,444 / 215,256 / 64.56%. Jules 248,216 / 207,094 / 83.43%. Codegen 6,423 / 3,995 / 62.2%. — [PRarena README](https://github.com/aavetis/PRarena)
- The README notes that some agents (Codex) iterate privately and open ready PRs directly, so they have few drafts and high merge rates. Copilot and Codegen open drafts first. — [PRarena](https://github.com/aavetis/PRarena)

**Paul Kinlan, "damn claude, that's a lot of commits"** (Mar 30, 2026) — [AI Focus](https://aifoc.us/damn-claude-thats-a-lot-of-commits/)
- Method: per-tool GitHub Search API queries (no GH Archive or BigQuery). Signals are Co-Authored-By trailers for Claude, GitHub Copilot, Cursor, Codex, Happy and Aider, and bot authors for the Copilot agent (`copilot-swe-agent[bot]`), Jules (`google-labs-jules[bot]`) and Devin (`devin-ai-integration[bot]`). Claude Code PRs were found via "Generated with Claude Code" in the PR body. Charts and CSVs are published. — [AI Focus](https://aifoc.us/damn-claude-thats-a-lot-of-commits/)
- Claude Code share of weekly public commits: 0.7% (180K of 27.7M, week of Sep 29, 2025) → 4.5% (2.6M of 57.8M, week of Mar 16, 2026). Inflection in late December 2025; more than 1M per week by February 2026. All AI tools combined: about 5% of public commits. — [AI Focus](https://aifoc.us/damn-claude-thats-a-lot-of-commits/)
- Six-month totals (Sep 29, 2025–Mar 27, 2026): Claude 20,963,874; Copilot Agent 2,550,612; Cursor 854,505; GitHub Copilot (trailer) 833,379; Jules 548,364; Codex 173,031; Happy 76,478; Devin 62,675; Aider 47,769. Cursor spiked above 200K/week in late January 2026, then fell, likely from a change in trailer behavior. — [AI Focus](https://aifoc.us/damn-claude-thats-a-lot-of-commits/)
- Author's caveats: public repos only. Claude adds trailers by default, but Copilot inline completions leave no trace. Codex npm downloads far exceed its visible commits. The search API is inconsistent, so the figures are estimates. — [AI Focus](https://aifoc.us/damn-claude-thats-a-lot-of-commits/)

**SemiAnalysis, "Claude Code is the Inflection Point"** (Feb 2026, paywalled)
- Claims 4% of public GitHub commits are authored by Claude Code and projects 20%+ of daily commits by end of 2026. The sourcing note credits "Generated by Claude Code" (i.e., the trailer/marker). Anthropic later cited it as about 4%, double the month before (secondary). — [SemiAnalysis](https://newsletter.semianalysis.com/p/claude-code-is-the-inflection-point?open=false); [GIGAZINE](https://gigazine.net/gsc_news/en/20260210-claude-code-github-commits-4-percent-20-percent)
- Critique (unverified X post): the share is sensitive to spam floods (reportedly between 0.6% and 15% during a gambling-spam surge) and to GitHub Search API footer counts. — [X, @con_golias](https://x.com/con_golias/status/2118301334835208380)

**claudescode.dev ("Claude's Code" dashboard)** — [claudescode.dev](https://claudescode.dev/)
- Operator not stated (only a "Buy me a coffee" handle, "jodan"). Methodology not published. Sample commits show "🤖 Generated with Claude Code" and "Co-Authored-By: Claude". As displayed on 2026-11-12: 32,909,303 total commits; +39.4B / −16.5B lines; 1,865,055 active repos. Languages: TypeScript 53.5%, Python 24.3%, HTML 22.2% (internally inconsistent). Earliest observed commit Feb 24, 2025. The activity log ends around Aug 26, 2026 and the page shows "−100% W/W", so the **data looks stale or broken**. — [claudescode.dev](https://claudescode.dev/)
- Earlier snapshot (Mar 2026): about 20.8M commits across about 1.09M repos, with about 90% of Claude Code output in repos with fewer than 2 stars. Critics note most GitHub repos have zero stars anyway. — [WinBuzzer](https://winbuzzer.com/2026/03/26/claude-code-90-percent-output-low-star-github-repos-xcxwbn/); [DEV](https://dev.to/adioof/90-of-claude-code-output-goes-to-repos-nobody-stars-thats-the-wrong-problem-nac)

**Academic agent-PR datasets**
- **AIDev** (Li, Zhang, Hassan; arXiv 2602.09185, Feb 2026): 932,791 agent-authored PRs from Codex, Devin, Copilot, Cursor and Claude Code across 116,211 repos and 72,189 developers, cutoff Aug 1, 2025. Curated subset: 33,596 PRs in 2,807 repos with more than 100 stars. On [HF](https://huggingface.co/datasets/hao-li/AIDev) and Zenodo. v1 (Jul 2025, arXiv 2507.15003) had 456,535 PRs across about 61k repos. Used for the MSR 2026 Mining Challenge. — [arXiv 2602.09185](https://arxiv.org/html/2602.09185v1); [arXiv 2507.15003](https://arxiv.org/html/2507.15003v1)
- AIDev-based merge rates range from 81.6% (Codex) to 42.9% (Devin) (secondary summary of an AIDev paper). A blog summary of 220,612 PRs gives Claude Code 84.3%, Codex 73.5%, Copilot 68.1%, Cursor 62.4%, Devin 43.0% (secondary, unverified). — [alphaXiv 2607.04697](https://www.alphaxiv.org/abs/2607.04697.md); [Vaughan blog](https://codex.danielvaughan.com/2026/08/04/what-220000-pull-requests-reveal-agentic-pr-task-routing-codex-cli-test-coverage-gaps/)
- **"Investigating Autonomous Agent Contributions in the Wild"** (arXiv 2604.00917, Apr 2026): 111,969 PRs, Jun–Aug 2025. Codex 20,835; Claude Code 19,148; Copilot 18,563; Jules 18,468; Devin 14,045; human baseline 20,910. About 75% of Codex and Jules PRs are in 0-star repos, vs 40.5% of human PRs. Median Codex PR merges in 0.5 **minutes** vs 0.4 hours for humans. Median Claude PR changes 376 lines vs about 60 for humans. Agent commits show higher churn and lower survival (small effect sizes). About 1.1M Codex PRs in the 3-month window. Authors warn that high merge rates may reflect the prompter merging their own PR. — [arXiv 2604.00917](https://arxiv.org/html/2604.00917v1)

### Inferences
- Merge rate is a weak quality signal. PR Arena's 90–98% merge rates for Codex, Copilot and Cursor, and Codex's 30-second median merge time, mostly reflect self-merges in personal repos. For little-helper, compute merge rates only where the PR author differs from the merger, in the target projects.
- Trailer counts are dominated by Claude Code because it is the only major tool that adds a trailer by default. Cross-tool "share" comparisons are therefore biased toward Claude Code and against Copilot completions, Cursor in the editor, and the Codex CLI.
- Every tracker reports a global long tail. None reports agent activity in established foundational OSS projects. That niche is open for little-helper.

### Gaps
- I found no tracker that publishes a time series of AI markers restricted to top-N starred or foundational OSS repos.
- I could not confirm who runs PR Arena or claudescode.dev beyond GitHub/handle names, or how often they refresh.
- SemiAnalysis's full method is paywalled.
- I did not verify whether GH Archive PushEvent payloads still include commit messages after GitHub's 2025 Events API changes. This matters for bulk trailer mining without the search API; check before relying on GH Archive.

---

## 3. Developer surveys: usage vs trust

### Takeaway
Usage is near-universal while trust is flat or falling. Stack Overflow found 76% (2024) → 84% (2025) using or planning to use AI, with distrust (46%) exceeding trust (33%) in 2025. In 2026, 83% use AI in some form but only 6.6% trust it for important decisions. DORA 2025 reports 90% adoption with 30% having little or no trust. JetBrains 2025 reports 85% regular use. Claude Code (66%) overtook Copilot (59%) among SO 2026 coding-agent users.

### Cited Findings
**Stack Overflow Developer Survey**
- 2024 → 2025: using or planning to use AI went from 76% to 84%. Distrust of accuracy rose from 31% to 46%. Only 33% trust it and 3% "highly trust". Favorability fell from 72% to 60%. Top frustration was "almost right, but not quite" (about 66%), followed by "debugging AI code is more time-consuming" (45%). — [TechRepublic](https://www.techrepublic.com/article/news-developer-trust-in-ai-declines/); [ShiftMag](https://shiftmag.dev/stack-overflow-survey-2025-ai-5653/); [ADMIN Magazine](https://www.admin-magazine.com/layout/set/print/News/Stack-Overflow-Survey-66-of-Developers-Frustrated-by-AI-Inaccuracy)
- **2026** (released Oct 6, 2026; over 30,000 responses (30,903 per The Register) from 169 countries; 16th edition): about 60% view AI at work favorably. 17.2% use no AI tools (so about 83% use some). 66% use coding assistants or agents, 63% general chat, and 26.2% automated agent workflows. 73% of coding-assistant users use them daily. Of daily users, 31% use AI 4+ hours/day. — [Stack Overflow press release](https://stackoverflow.co/company/press/archive/stack-overflow-annual-developer-survey-ai-trust-conditional/); [survey.stackoverflow.co/2026/ai](https://survey.stackoverflow.co/2026/ai); [The Register](https://www.theregister.com/software/2026/10/10/stack-overflow-survey-finds-devs-hooked-on-ai-but-not-totally-sold-on-its-judgment/5301662)
- 2026 trust (n=14,304): 48.0% trust AI when they can easily verify it. 16.3% trust it for many tasks but not important decisions. 16.3% trust it for low-risk tasks only. 12.3% don't trust it for most work. 6.6% trust it for important decisions. 78.7% say source attribution matters. — [SO trust data](https://survey.stackoverflow.co/2026/ai/data/ai-trust); [press release](https://stackoverflow.co/company/press/archive/stack-overflow-annual-developer-survey-ai-trust-conditional/)
- 2026 tools: among coding agents, Claude Code 66% and GitHub Copilot 59%. LLMs currently used: Anthropic 75%, OpenAI 74%. Only 24% of organizations publish approved tools or an AI policy. — [survey.stackoverflow.co/2026/ai](https://survey.stackoverflow.co/2026/ai); [press release](https://stackoverflow.co/company/press/archive/stack-overflow-annual-developer-survey-ai-trust-conditional/)
- Note: SO 2026 respondents report "public GitHub projects" (69.5%) as a community resource used slightly more than Stack Overflow itself (68.6%). — [press release](https://stackoverflow.co/company/press/archive/stack-overflow-annual-developer-survey-ai-trust-conditional/)

**JetBrains State of Developer Ecosystem 2025** (24,534 devs, 194 countries, Apr–Jun 2025; released Oct 2025)
- 85% regularly use AI for coding. 62% rely on at least one AI coding assistant, agent or editor. 15% have never used AI. ChatGPT usage fell from 49% (2024) to 41%. Only 44% say AI is fully or partially adopted in their workflows. — [JetBrains Research blog](https://blog.jetbrains.com/research/2025/10/state-of-developer-ecosystem-2025/); [The Register](https://www.theregister.com/2025/10/21/massive_jetbrains_dev_survey); [heise](https://heise.de/-10771317)

**DORA (Google Cloud)**
- 2024: a 25% increase in AI adoption was associated with −1.5% delivery throughput, −7.2% delivery stability and −2.6% time on valuable work, alongside +3.4% code quality and +3.1% review speed. These are correlational survey estimates. — [Google Cloud blog](https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report); [RedMonk](https://redmonk.com/rstephens/2024/11/26/dora2024/); [HashiCorp](https://www.hashicorp.com/blog/ai-is-making-developers-faster-but-at-a-cost)
- 2025 "State of AI-assisted Software Development" (Sep 23, 2025; nearly 5,000 respondents): 90% use AI at work ("14% increase", units unclear). Median 2 hours/day of use. 30% have little (23%) or no (7%) trust; 24% have a lot or a great deal. Over 80% report productivity gains and 59% better code quality. AI is now associated with *higher* throughput but still with instability. Frames AI as an "amplifier" and introduces the DORA AI Capabilities Model. — [Google blog](https://blog.google/technology/developers/dora-report-2025/); [Report PDF](https://services.google.com/fh/files/misc/2025_state_of_ai_assisted_software_development.pdf)

**Sonar 2026 State of Code Developer Survey** (Jan 8, 2026; more than 1,100 devs; COI: Sonar sells code-verification tools)
- Developers estimate AI accounts for 42% of committed code and expect 65% by 2027. 72% of those who have tried AI use it daily. 96% don't fully trust that AI code is functionally correct, but only 48% always check it before committing. 38% say AI code takes more effort to review (vs 27% less). Over a third use AI through personal accounts. The Register called the verification-gap framing "conveniently self-validating". — [Sonar press release](https://www.sonarsource.com/company/press-releases/sonar-data-reveals-critical-verification-gap-in-ai-coding/); [The Register](https://www.theregister.com/2026/01/09/devs_ai_code/)

**Linux Foundation Research, "Navigating OSS Development in the Generative AI Era"** (Oct 20, 2026; n=234; fieldwork Apr–Jun 2026; partners Red Hat, Futurewei, LF AI & Data, OpenSSF)
- Maintainers estimate 25% of incoming PRs are low-quality "AI slop", rising to 31% on large projects (a perception, not a measurement). GenAI cut code-writing time by about 52% on average (n=96, self-estimated). 64% of large-project maintainers report longer reviews. — [LF press release](https://www.linuxfoundation.org/press/new-lf-research-survey-shows-generative-ai-cuts-open-source-coding-time-in-half-but-25-of-incoming-pull-requests-are-considered-ai-slop); [Report PDF](https://www.linuxfoundation.org/hubfs/Research%20Reports/Navigating-Open-Source-Software-Development-in-the-Generative-AI-Era.pdf?hsLang=en); [Phoronix](https://phoronix.com/news/Linux-Foundation-25p-AI-Slop)

### Inferences
- Surveys measure *use*, not *authorship share*. The only survey estimate of committed-code share (Sonar, 42%) is self-reported and comes from a vendor. It is far above the trailer-based public-commit shares (about 4–5%, early 2026). That gap is a rough measure of how much the git-marker approach undercounts.
- SO's shift from Copilot/ChatGPT toward Claude Code (and Anthropic models) matters for detection. Claude Code's default trailers make 2025–2026 more visible in git history than the 2022–2024 Copilot-completion era, which is essentially invisible.

### Gaps
- **GitHub/Accenture enterprise Copilot study** (2024; recalled as +8.69% PRs, +15% merge rate, +84% successful builds) was **not verified** in this session.
- JetBrains 2026 Developer Ecosystem results were not found or verified.
- SO 2026 field dates were not stated in the materials reviewed.

---

## 4. Usage telemetry from AI labs, company statements, and market size

### Takeaway
Coding is the single largest Claude use case (35% of Claude.ai conversations, Feb 2026) but only about 4% of ChatGPT messages (Jun 2025). Agentic tools are far more automation-heavy (Claude Code 79% automation vs Claude.ai 49%, Apr 2025). Big-tech "share of new code is AI" claims climbed from about 25% to 75% at Google between Oct 2024 and Apr 2026. These are self-reported and loosely defined.

### Cited Findings
**Anthropic Economic Index** (COI: Anthropic's own product data)
- "AI's impact on software development" (Apr 28, 2025; about 500k coding interactions): 79% of Claude Code conversations were automation vs 49% on Claude.ai. Startups accounted for 33% of Claude Code interactions vs 13% for enterprises (preliminary). — [Anthropic](https://www.anthropic.com/research/impact-software-development); [RTInsights](https://www.rtinsights.com/report-shows-ai-driving-automation-in-software-development/)
- January 2026 ("economic primitives") report: automation was about three-quarters of API interactions vs less than half in the consumer app (from search summary; not checked against the full text). — [Anthropic, Jan 2026](https://anthropic.com/research/anthropic-economic-index-january-2026-report)
- March 2026 "Learning curves" (published Mar 24, 2026; sample Feb 5–12, 2026; 1M Claude.ai + 1M 1P API conversations, including Claude Code): Computer & Mathematical tasks were 35% of Claude.ai conversations. Since Aug 2025 that share rose about 14% (relative) in the API and fell about 18% in Claude.ai, as coding shifts to the API and Claude Code, which is a "large share" of sampled API traffic. Automation fell sharply in the 1P API data. — [Anthropic](https://www.anthropic.com/research/economic-index-march-2026-report)
- June 2026 "Cadences": compares chat, Cowork and Claude Code. Claude Code sessions averaged 0.37 points higher on a five-point autonomy scale (secondary summary). — [Anthropic](https://www.anthropic.com/research/economic-index-june-2026-report)

**OpenAI — "How People Use ChatGPT"** (NBER WP 34255, Sep 2025)
- Only 4.2% of ChatGPT messages relate to computer programming (as of Jun 2025). Non-work use exceeds 70%. The paper contrasts this with Claude, where coding is a far larger share. Consumer data only; excludes API and Codex. — [NBER w34255](https://www.nber.org/papers/w34255); [OpenAI PDF](https://cdn.openai.com/pdf/a253471f-8260-40c6-a2cc-aa93fe9f142e/economic-research-chatgpt-usage-paper.pdf)

**Company statements on AI share of code** (self-reported; definitions vary: "new code", characters accepted, "some projects")
- Google: more than 25% of new code AI-generated (Oct 2024) → reportedly about 50% (fall 2025) → **75% of new code "AI-generated and approved by engineers"** (Sundar Pichai, Apr 22, 2026, Cloud Next). — [Semafor](https://www.semafor.com/article/04/24/2026/google-ceo-says-75-of-companys-new-code-is-ai-generated)
- Microsoft: Satya Nadella said "maybe 20 to 30 percent of the code that is inside of our repos today in some of our projects" is AI-written (LlamaCon, Apr 29, 2025). — [TechRepublic](https://www.techrepublic.com/article/news-microsoft-meta-code-written-by-ai/)

**Market size of agent tools** (private-company run-rates, not audited)
- Cursor: about $1B annualized revenue (Nov 2025) → over $2B (reported Mar 2, 2026) → about $4B (early Jun 2026, per Forbes via Dealroom). About 75% from enterprise. — [TechCrunch](https://techcrunch.com/2026/03/02/cursor-has-reportedly-surpassed-2b-in-annualized-revenue); [Dealroom](https://dealroom.co/news/134107-cursor-tops-4b-annualized-revenue/)

### Inferences
- The lab and company numbers measure share of *usage* or *new code inside one company*. They are ceilings or context, not comparators for OSS commit shares. Google's 75% and the trailer-based about 4–5% of public commits (early 2026) differ by more than an order of magnitude, mostly because of detection and definition.
- The Anthropic data says coding moved from chat (no git trace) to Claude Code (git trace by default) during 2025–2026. That should make the AI footprint in git history much more visible from mid-2025 on, a known break in any detection-based time series.

### Gaps
- Anthropic's first Economic Index (Feb 2025; recalled as about 37% computer/mathematical) and Sept 2025 figures were not re-verified in this session.
- Claude Code's run-rate revenue (reported at about $2.5B in Feb 2026 in secondary coverage) was not verified against an Anthropic primary source.
- No Microsoft update after Apr 2025 was found. No Meta or Amazon quantified share was found.

---

## 5. Code-quality and engineering-analytics vendors

### Takeaway
Vendor telemetry consistently shows more output (more PRs and lines) alongside more duplication, more churn, bigger PRs and much longer review times, with little org-level delivery gain. GitClear 2026: block duplication +81% since 2023, moved/refactored code down to 3.8%. Faros: +98% PRs merged but +91% review time. Every one of these vendors sells measurement or quality tooling.

### Cited Findings
**GitClear** (COI: sells code-analytics; PDFs gated; AI-usage measurement method not described)
- "The Maintainability Gap: AI Code Quality in 2026": 623M analyzed changes, 2023–2026. Block duplication +81% (40.3 → 73.0 per million changed lines, highest on record). Within-commit copy/paste rose from 9.4% of changed lines (2022) to 15.7% (H1 2026). Moved (refactored) code fell from 21% (2022) to 13% (2023) to 3.8% (2026 YTD). Copy/paste is now about 5× more likely than refactor. Changes touching code older than 12 months fell 74% (1.7% → 0.46%). Error-masking constructs +47%. Two-week churn +15%. — [GitClear](http://www.gitclear.com/the_ai_code_quality_maintainability_gap); [LeadDev](https://leaddev.com/ai/code-maintainability-plummets-in-the-ai-coding-era); [The New Stack](https://thenewstack.io/ai-coding-duplication-rose/)
- "AI Coding Tools Attract Top Performers" (Jan 2026): heavy AI users out-produced non-users 4–10×, but most of the gap predated AI. Against their own prior output, heavy users gained about 25% velocity. — [GitClear (cited within 2026 report)](http://www.gitclear.com/the_ai_code_quality_maintainability_gap)
- "AI Copilot Code Quality" (Feb 2025, 2020–2024 data): 2024 was the first year in which within-commit copy/paste exceeded moved code. Commits with duplicated blocks rose about 10× over two years. — [GitClear (cited within 2026 report)](http://www.gitclear.com/the_ai_code_quality_maintainability_gap)

**Faros AI** (COI: engineering-intelligence vendor; reports gated)
- "AI Productivity Paradox" (2025; 10,000+ devs, 1,255 teams): high-AI-adoption teams complete 21% more tasks and merge 98% more PRs, but PR review time is +91%, PR size +154% and bugs per developer +9%, with no significant company-level productivity change. — [Faros AI](https://www.faros.ai/blog/ai-productivity-paradox-report-2025)
- "AI Engineering Report 2026: Acceleration Whiplash" (22,000 devs, 4,000+ teams, two years of telemetry): median time to first review +156.6%, average time in review +199.6%, median time in review +441.5%. Org-level lead time and deploy frequency mostly flat (partly secondary). Compares each org's lowest- vs highest-adoption periods. — [Faros AI](https://www.faros.ai/blog/ai-acceleration-whiplash-takeaways)

**Jellyfish** (COI: engineering-management vendor)
- June 2025: AI use in engineering +260% YoY (2M+ PRs). Average PR cycle time 95.5h → 83.8h in Q2 2025. — [Jellyfish](https://jellyfish.co/blog/ai-impact-data-june-2025/)
- 2026 AI Engineering Trends (Apr 2026): 37M PRs, 1,000+ companies, 200k engineers. About 2× throughput for top adopters (page layout garbled; treat with caution). An earlier OpenAI-partnered analysis: median cycle time 16.7h → 12.7h (−24%) as adoption goes from 0% to 100%. — [Jellyfish newsroom](https://jellyfish.co/newsroom/jellyfish-reveals-ais-real-impact-on-engineering-teams/); [Jellyfish blog](https://jellyfish.co/blog/are-ai-coding-tools-making-companies-more-productive/)

**Uplevel Data Labs** (2024; COI: vendor)
- About 800 devs (351 with Copilot access vs 434 without); windows Jan–Apr 2023 vs Jan–Apr 2024. 41% higher bug rate in PRs for the Copilot-access group, no meaningful change in cycle time or throughput. Measured access, not usage; observational. — [BetaNews](https://betanews.com/2024/09/17/genai-tools-dont-increase-coding-efficiency); [IT Brew](https://www.itbrew.com/stories/2024/10/30/why-ai-coding-assistants-might-not-help-devs-much)

**Stanford (Yegor Denisov-Blanch) "100k developers" study** (talk-based, no paper released)
- About 100k developers across 600+ companies. Average AI productivity gain about 15–20%, measured as delivered functionality net of rework. Greenfield low-complexity work gains 30–40%; brownfield high-complexity work 0–10% (possibly negative). Critics note the model is not public. — [AI Engineer talk](https://www.ai.engineer/talks/tbDDYKRFjhk-ai-developer-productivity); [Proxify summary](https://proxify.io/articles/stanford-study-of-100000-developers-on-engineering-productivity)

### Inferences
- GitClear's metrics (duplicated blocks, moved lines, edits to code older than 12 months, two-week churn) can be computed from git history alone. little-helper could reproduce them per project, pre- and post-2023, without any AI-attribution signal, then cross-tab against AI-marker commits.
- Foundational OSS projects are mostly brownfield, high-complexity code. The Stanford segmentation predicts small gains there, consistent with agent activity clustering in new or low-star repos.

### Gaps
- No vendor states how it identifies AI-assisted code (GitClear and Jellyfish probably use tool telemetry or license data, not git markers). Their numbers cannot be tied to specific commits.
- The full Faros and Jellyfish 2026 reports were not retrieved, so quality and revert-rate figures are unverified.

---

## 6. OSS-ecosystem health: registries, malware/slopsquatting, archives, maintainer burden

### Takeaway
The supply-chain side shows AI-related pressure: Sonatype counts about 1.96M malicious packages logged since 2017 (as of Q3 2026, npm about 90%), LLMs hallucinate packages (19.7% of samples) and versions (27.8%), curl ended its bug bounty over AI slop (Jan 2026), and GitHub shipped PR kill-switches and caps for maintainers (Feb–Jun 2026). Software Heritage keeps growing (27–28B files, about 430M projects by early 2026).

### Cited Findings
**Sonatype** (COI: supply-chain security vendor)
- 2026 State of the Software Supply Chain (Jan 28, 2026): 9.8 trillion downloads in 2025 across Maven Central, PyPI, npm and NuGet. OSS malware +75%. Over 1.2M malicious packages analyzed. Of 37k AI-driven upgrade recommendations, GPT-5 hallucinated 27.8% of component versions. — [Sonatype press release](https://www.sonatype.com/press-releases/sonatype-research-reveals-open-malware-grows-75-percent); [SD Times](https://sdtimes.com/security/report-ai-hallucinates-27-of-upgrade-recommendations-for-open-source-projects/)
- Quarterly Open Source Malware Index: Q1 2026, 21,764 malicious packages. Q3 2026, 149,329, bringing the total logged since 2017 to 1,960,846. npm was 89.5% of Q3. Q3 also records a first known case of a rogue AI agent uploading malicious packages. — [Sonatype Q1](https://www.sonatype.com/press-releases/sonatype-q1-2026-open-source-malware-index); [Sonatype Q3 blog](https://www.sonatype.com/blog/q3-2026-open-source-malware-index-when-compromise-compounds)
- Conflict: Infosecurity Magazine headlines "454,000+" malicious packages, likely a single-year count vs the cumulative one. — [Infosecurity](https://infosecurity-magazine.com/news/454000-malicious-open-source)

**Slopsquatting**
- Spracklen et al., "We Have a Package for You!" (USENIX Security 2025): across 16 code models, 19.7% (440,445) of generated samples contained at least one hallucinated package, with 205,474 unique fake names. Hallucinations recur across reruns (43% or 58% depending on the summary). Term coined by Seth Larson (PSF). Bar Lanyado's test package `huggingface-cli` got 30k+ downloads in three months. — [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-slopsquatting-ai-supply-chain-20260419/); [Socket glossary](https://socket.dev/glossary/slopsquatting.md)

**Maintainer burden / AI slop**
- curl ended its HackerOne bug bounty at the end of Jan 2026. Reports now go through GitHub unpaid. The confirmed-vulnerability rate reportedly fell from about 15% to under 5% (secondary). — [The Register](https://www.theregister.com/2026/01/21/curl_ends_bug_bounty/); [The New Stack](https://thenewstack.io/drowning-in-ai-slop-reports-curl-ends-bug-bounties/)
- GitHub's "Eternal September of open source" post (Feb 12, 2026), then repository settings to disable PRs or restrict them to collaborators (Feb 13, 2026). In June 2026, a cap on concurrent open PRs by outside contributors that counts Copilot and other agent PRs; controls extended to issues. — [GitHub Blog](https://github.blog/2026-02-12-welcome-to-the-eternal-september-of-open-source-heres-what-we-plan-to-do-for-maintainers); [GitHub Community discussion](https://github.com/orgs/community/discussions/187038); [The Register](https://www.theregister.com/2026/02/03/github_kill_switch_pull_requests_ai); [Visual Studio Magazine](https://visualstudiomagazine.com/articles/2026/06/30/github-extends-contribution-controls-from-prs-to-issues.aspx)
- Godot maintainers describe AI slop PRs as "draining and demoralizing" (Feb 2026). — [The Register](https://www.theregister.com/2026/02/18/godot_maintainers_struggle_with_draining/)
- LF Research (Oct 2026): 25% of incoming PRs perceived as AI slop (see §3). — [LF](https://www.linuxfoundation.org/press/new-lf-research-survey-shows-generative-ai-cuts-open-source-coding-time-in-half-but-25-of-incoming-pull-requests-are-considered-ai-slop)

**Archives**
- Software Heritage: over 27B unique source files from 421M projects (Jan 2026, 2025 Activity Report), 28B+ files and 430M+ projects (Mar 2026). Ingests about 1.3 projects per second. — [Software Heritage 2025 report](https://www.softwareheritage.org/?p=48053); [SWH talk Mar 2026](https://annex.softwareheritage.org/public/talks/2026/2026-03-OpenScience-Spain-SWH.pdf)

### Inferences
- Policies and controls (PR caps, bounty closures, disclosure rules) are datable events. little-helper can treat them as covariates when interpreting changes in PR or issue volume and merge rates for projects that adopted them.
- For package-publishing projects (matplotlib, plotly), registry-side signals (release cadence, typosquats of their names) are separate from git-side authorship and need registry data.

### Gaps
- No primary registry-growth series (PyPI, npm, crates.io package/version counts over time) or ecosyste.ms totals were retrieved. Check ecosyste.ms, the PyPI stats BigQuery dataset, and crates.io dumps directly.
- No OpenSSF report quantifying AI-generated contributions was found beyond its LF Research partnership.
- PyPI- or npm-specific counts of AI-generated spam packages were not found.

---

## 7. Detecting AI authorship in git/GitHub history: signals and reliability

### Takeaway
Reliable but heavily undercounting signals exist: tool-specific commit trailers, bot author accounts, branch prefixes, PR-body watermarks, author-name suffixes, agent config files, and project disclosure tags like `Assisted-by:`. They catch only tools that self-identify by default (mainly Claude Code, cloud agents and aider) and miss IDE completions, Codex CLI, and users who disable attribution. Content-based AI-code detectors perform poorly (text detectors fail on code; best research models reach about 0.83 F1 in lab settings) and should not be used for per-commit attribution.

### Cited Findings
**Per-tool signals** (verify against the target repo's history; formats drift by version)

| Tool | Signal(s) | Source |
|---|---|---|
| Claude Code | Commit trailer `Co-Authored-By: Claude <noreply@anthropic.com>` and `🤖 Generated with [Claude Code](…)` in commit and PR body. Configurable or disableable via the `attribution` setting (`commit`, `pr`), which replaced `includeCoAuthoredBy` around v2.0.62. Bug reports say empty-string settings don't always suppress it. | [claudescode.dev samples](https://claudescode.dev/); [arXiv 2604.00917](https://arxiv.org/html/2604.00917v1); [Kinlan](https://aifoc.us/damn-claude-thats-a-lot-of-commits/); [claudeissues #17849](https://claudeissues.com/issue/17849-docs-obsolete-documentation-for-includecoauthoredby-in-settings-table-deprecated); [claudeissues #45137](https://claudeissues.com/issue/45137-attribution-commit-does-not-disable-co-authored-by-trailer) |
| GitHub Copilot coding/cloud agent | Bot author `copilot-swe-agent[bot]`; head branch `copilot/…`. Separate "GitHub Copilot" Co-Authored-By trailer also seen. | [PRarena](https://github.com/aavetis/PRarena); [Kinlan](https://aifoc.us/damn-claude-thats-a-lot-of-commits/); [arXiv 2604.00917](https://arxiv.org/html/2604.00917v1) |
| GitHub Copilot inline completions | **No trace** | [Kinlan](https://aifoc.us/damn-claude-thats-a-lot-of-commits/) |
| OpenAI Codex (cloud) | Head branch `codex/…`. Commits often recorded under the human's account. Codex Co-Authored-By trailer seen, but rare relative to npm downloads. | [PRarena](https://github.com/aavetis/PRarena); [arXiv 2604.00917](https://arxiv.org/html/2604.00917v1); [Kinlan](https://aifoc.us/damn-claude-thats-a-lot-of-commits/) |
| Cursor (background/cloud agent) | Head branch `cursor/…`; Co-Authored-By trailer. Trailer behavior changed around late Jan 2026, causing a visible drop. | [PRarena](https://github.com/aavetis/PRarena); [Kinlan](https://aifoc.us/damn-claude-thats-a-lot-of-commits/) |
| Google Jules | Bot author `google-labs-jules[bot]` | [PRarena](https://github.com/aavetis/PRarena); [arXiv 2604.00917](https://arxiv.org/html/2604.00917v1) |
| Devin | Bot author `devin-ai-integration[bot]` | [PRarena](https://github.com/aavetis/PRarena); [arXiv 2604.00917](https://arxiv.org/html/2604.00917v1) |
| Codegen | Bot author `codegen-sh[bot]` | [PRarena](https://github.com/aavetis/PRarena) |
| OpenHands | Head branch or `Co-authored-by: openhands` trailer | [arXiv 2604.00917](https://arxiv.org/html/2604.00917v1) |
| Aider | Default: "(aider)" appended to git author and committer names. Optional `aider: ` message prefix (`--attribute-commit-message-author`/`-committer`). Optional Co-authored-by trailer (`--attribute-co-authored-by`). | [aider docs](https://aider.chat/docs/git.html) |
| Others named in literature | Cosine, Tembo, Amazon Q, JetBrains Junie, Happy (Claude Code client; trailer) | [arXiv 2604.00917](https://arxiv.org/html/2604.00917v1); [Kinlan](https://aifoc.us/damn-claude-thats-a-lot-of-commits/) |

**Project-level disclosure tags**
- Linux kernel: proposal from Sasha Levin, July 2025. `Documentation/process/coding-assistants.rst` requires an `Assisted-by:` tag and bars AI agents from adding `Signed-off-by` (only humans certify the DCO). Reportedly entered the docs Jan 2026 (The Register) or was merged into Torvalds' tree in April 2026 (other coverage); sources conflict. After the Oct 2026 Maintainers Summit (Prague), Levin announced consensus to **deprecate the Assisted-by tag** (about Oct 9, 2026). Removal reportedly landed for Linux 7.4; 7.3 docs still contain the requirement. Objections were uneven compliance and "free advertising" for LLM vendors (Jeff Layton); Laurent Pinchart opposed removal. — [The Register](https://www.theregister.com/ai-and-ml/2026/10/14/linux-kernel-devs-drop_obligatory_confession_of_ai_tool_usage/5303140); [patchew (Jul 2025 patch)](https://patchew.org/linux/20250727195802.2222764-1-sashal@kernel.org); [docs.kernel.org source](https://docs.kernel.org/_sources/process/coding-assistants.rst.txt); [lilting.ch](https://lilting.ch/en/articles/linux-kernel-ai-coding-assistant-policy)
- Community "Assisted-by: <agent>/<model>" trailer conventions are being proposed as an alternative to Co-authored-by, e.g. the fluxcd agent skill. — [tessl registry](https://tessl.io/registry/skills/github/fluxcd/agent-skills/commit-assisted-by)
- Some repos run CI checks that flag known AI-agent Co-authored-by trailers in PR commits (e.g., ComfyUI). — [morphllm mirror of ComfyUI .github](https://code.morphllm.com/Comfy-Org/ComfyUI/src/master/.github)

**Agent configuration files as an adoption signal**
- Early study (Mohsenimofidi et al., arXiv 2510.21413, MSR 2026): only 466 (about 5%) of scanned OSS repos had at least one context file. Counts: Copilot instructions 218, CLAUDE.md 181, AGENTS.md 118, GEMINI.md 29. — [arXiv 2510.21413](https://arxiv.org/html/2510.21413v1)
- Later study (arXiv 2602.14690; 2,926 repos): context files dominate agent configuration, and AGENTS.md is emerging as the interoperable standard. A secondary breakdown gives CLAUDE.md 34.2%, AGENTS.md 32.3%, copilot-instructions.md 27.7% (unverified). — [arXiv 2602.14690](https://arxiv.org/pdf/2602.14690v1); [Vaughan blog](https://codex.danielvaughan.com/2026/05/12/configuring-agentic-coding-tools-research-codex-cli-adoption-gap/)
- AGENTS.md (released Aug 2025) is "used by over 60k open-source projects" per OpenAI and agents.md; no method is given. Donated to the Linux Foundation's Agentic AI Foundation, co-founded by OpenAI, Anthropic and Block (founding date not verified here). — [OpenAI](https://openai.com/index/agentic-ai-foundation/); [agents.md](https://agents.md/)
- Octoverse 2026: new repos with agent config files average about 8× the commits of those without. — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)

**Self-admitted (text) mentions**
- Xiao et al. (arXiv 2507.10422, v3 Jan 2026): 1,292 explicit GenAI-use mentions across only 156 repos out of a sample of 250k+ GitHub repos. They found no general rise in code churn after GenAI adoption (151 repos). — [arXiv 2507.10422](https://arxiv.org/html/2507.10422v3)
- Tufano et al. (arXiv 2603.26277, accepted to EMSE): mined commits, issues and PRs for ChatGPT and Copilot traces, producing a taxonomy of 64 tasks in 7 categories. — [arXiv 2603.26277](https://arxiv.org/abs/2603.26277)

**Reliability / undercount evidence**
- Codex commits often sit under human accounts, Claude's watermark can be disabled, and CLI contributions may be untraceable, so "human" baselines include undetected agent work. — [arXiv 2604.00917](https://arxiv.org/html/2604.00917v1)
- Copilot completions leave no trace, Codex's npm downloads far exceed its visible commits, and GitHub search counts are unstable. — [Kinlan](https://aifoc.us/damn-claude-thats-a-lot-of-commits/)
- GitHub itself calls its agent signal a "floor". — [GitHub Blog](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/)
- Spam can swing share estimates widely (unverified X post: 0.6%–15%). — [X](https://x.com/con_golias/status/2118301334835208380)
- The kernel dropped its Assisted-by requirement partly because compliance was uneven. — [The Register](https://www.theregister.com/ai-and-ml/2026/10/14/linux-kernel-devs-drop_obligatory_confession_of_ai_tool_usage/5303140)
- Self-reported AI share of committed code (Sonar, 42%) vs trailer-based share of public commits (about 4–5%, early 2026) suggests markers capture a small fraction of AI involvement. — [Sonar](https://www.sonarsource.com/company/press-releases/sonar-data-reveals-critical-verification-gap-in-ai-coding/); [Kinlan](https://aifoc.us/damn-claude-thats-a-lot-of-commits/)

**Content-based AI-code detectors**
- Suh et al. (arXiv 2411.04299, Nov 2024): text AIGC detectors, including GPTZero, perform poorly on source code. Their AST-embedding model beats GPTSniffer with F1 82.55 in lab conditions. — [arXiv 2411.04299](https://arxiv.org/html/2411.04299v1)
- Pan et al. (arXiv 2401.03676, Jan 2024): five AIGC detectors across 13 prompt variants perform poorly at telling human from AI code. — [arXiv 2401.03676](https://arxiv.org/html/2401.03676v1)

### Inferences
Practical guidance for little-helper. These are inferences, not sourced facts.
- **Detection stack, highest to lowest precision:** (1) bot author or committer logins ending in `[bot]` from the table above. (2) Tool trailers: match on email and name patterns such as `noreply@anthropic.com`, `Co-authored-by: .*(Claude|Copilot|Cursor|Codex|aider|openhands)`, and the "(aider)" author suffix. The Claude Code trailer display name has varied with the model name (e.g., "Claude Opus …") in Claude Code's attribution configuration observed in this session, so match on the email rather than an exact string. (3) PR-body watermarks ("Generated with Claude Code", Codex task links). (4) Branch prefixes (`copilot/`, `codex/`, `cursor/`), which are lower precision because humans can use them. (5) Presence and first-commit date of `AGENTS.md`, `CLAUDE.md`, `.cursorrules` / `.cursor/rules`, `.github/copilot-instructions.md`, `GEMINI.md`. (6) Project-specific disclosure tags (`Assisted-by:`, `Generated-by:`) and policy files (CONTRIBUTING AI sections).
- **Treat all marker-based counts as lower bounds** and report them alongside marker-free metrics (volume, PR size, churn, duplication, first-time contributors, review latency) that capture AI effects without attribution.
- **Expect structural breaks** tied to tool launches and default changes: Claude Code's first observed commit was Feb 24, 2025; the Copilot agent produced 1M+ PRs May–Sep 2025; Cursor's trailer changed around Jan 2026; kernel tag policy started Jan or Apr 2026 and was deprecated Oct 2026. Pre-2025 AI use (Copilot completions, ChatGPT copy-paste) is essentially invisible in git.
- **Workflow matters for the target projects.** PostgreSQL, FFmpeg and the Linux kernel develop through mailing lists and patches, with GitHub as a mirror. PR-based signals (bot PR authors, branch names, PR bodies) won't apply, so only commit-message trailers and tags survive. Squash or rebase merges and maintainer-edited commit messages can also strip or keep trailers depending on project practice.
- Content-based detectors are not reliable enough for per-commit labels in historical data. At most, use them for aggregate sensitivity checks.

### Gaps
- Official vendor documentation of the exact trailer strings for Cursor, Codex, Copilot (trailer variant) and Jules was not retrieved. Strings above come from trackers and papers. Sample real commits to confirm.
- The exact `Assisted-by:` format in the kernel doc (reportedly `AGENT_NAME:MODEL_VERSION [tools]`) was not verified. Check [docs.kernel.org](https://docs.kernel.org/_sources/process/coding-assistants.rst.txt). Counts of kernel commits carrying the tag were not found.
- No study found that measures detection recall directly (e.g., against tool telemetry). Undercount magnitudes are inferred from gaps between surveys and markers.
- Adoption of `.cursorrules` and Fedora/QEMU/Gentoo/NetBSD AI policies over time was not researched in this pass.
