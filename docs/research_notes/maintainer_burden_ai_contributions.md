# AI-Generated Contributions, Maintainer Burden, and OSS Governance (2023 to Nov 2026)

Research date: 2026-11-12. Scope: incidents, project AI policies, agent-PR datasets and studies, AI and security reporting, AI crawler load, and maintainer surveys. Emphasis is on foundational and mature projects. "Primary" means the project's or author's own page. Secondary sources are flagged where they are the only support.

---

## 1. "AI slop" in bug reports and security reports (curl, Python, Django, Linux kernel, PostgreSQL)

### Takeaway
Low-quality AI-generated security reports grew from an annoyance (2024) into a structural problem (2025). curl ended its bug bounty as of 2026-01-31. By 2026 the problem had shifted: AI-found reports at the Linux kernel and PostgreSQL were increasingly *real*, and the burden became volume, duplicates, and patch throughput rather than pure slop.

### Cited Findings

**curl (timeline)**
- 2025-05 (about May 6-7): Daniel Stenberg added a screening checkbox about AI use to curl's HackerOne report form. He said reporters judged to have filed AI slop would be banned, and that curl was "effectively being DDoSed." HackerOne's CTO Alex Rice replied that its Code of Conduct "does not prohibit the use of AI to assist in writing reports" but does prohibit spam. — [The Register, 2025-05-07](https://www.theregister.com/2025/05/07/curl_ai_bug_reports/)
- 2025-07-14, "Death by a thousand slops" (primary):
  - About 20% of 2025 submissions were AI slop.
  - About 5% of 2025 submissions were genuine vulnerabilities, a significant drop from earlier years.
  - curl averages about 2 security reports per week. Each report occupies 3-4 people of the 7-member security team for about 30 minutes, sometimes 1-3 hours.
  - To date the program had fixed 81 genuine vulnerabilities and paid more than $90,000.
  - Options considered: a submission fee, dropping monetary rewards, HackerOne reputation penalties. — [daniel.haxx.se, 2025-07-14](https://daniel.haxx.se/blog/2025/07/14/death-by-a-thousand-slops/)
- 2025-09 to 2025-10: Counterexample. Joshua Rogers used AI-assisted scanners (Almanax, Corgea, ZeroPath, Gecko, Amplify; he rated ZeroPath highest) and sent curl a large list of issues. Stenberg called them "truly awesome findings," and about 50 bugfixes had been merged by early October. Simon Willison reported 22 at an earlier point. — [The Register, 2025-10-02](https://www.theregister.com/2025/10/02/curl_project_swamped_with_ai/); [Simon Willison, 2025-10-02](https://simonwillison.net/2025/Oct/2/curl/)
- 2026-01-26, "The end of the curl bug bounty" (primary):
  - The bounty stopped 2026-01-31.
  - Lifetime totals: 87 confirmed vulnerabilities and more than $100,000 paid.
  - The confirmed rate was historically "north of 15%" and "plummeted to below 5%" starting in 2025.
  - curl's HackerOne inbound volume rose sharply over four quarters while Ruby, Node, and Rails stayed flat or declined.
  - Reports now go through GitHub Private Vulnerability Reporting or security@curl.se, with no money at any severity. AI-slop submitters "will still be banned and publicly ridiculed." A submission fee was considered and rejected. — [daniel.haxx.se, 2026-01-26](https://daniel.haxx.se/blog/2026/01/26/the-end-of-the-curl-bug-bounty/)
  - Conflict: secondary outlets cite $86K and 78 vulns, or about $90K and 87 vulns. Use Stenberg's own figures above. — [heise](https://heise.de/-11142493); [TechRadar](https://www.techradar.com/pro/security/curl-will-stop-bug-bounties-program-due-to-avalanche-of-ai-slop)

**Python / PSF**
- 2024-12: Seth Larson (PSF Security Developer-in-Residence) blogged about an "uptick in extremely low-quality, spammy, and LLM-hallucinated security reports."
  - He urged that such reports be treated as potentially malicious, that reporters verify findings and bring patches, and that platforms limit automated report creation.
  - He told The Register he sees "fewer than ten" a month across CPython, pip, urllib3, and Requests, but called it an early warning. — [The Register, 2024-12-10](https://www.theregister.com/2024/12/10/ai_slop_bug_reports/)

**Django**
- By mid-2025 (Simon Willison noted it 2025-07-11), Django's security policy had a section on AI-assisted reports:
  - Reporters must disclose AI involvement and the tool.
  - Reports with fictitious APIs or placeholder content are auto-rejected.
  - Apparent unverified AI output is closed without response, and repeat offenders may be banned.
  - The 6.0 docs add that bulk-submitted reports may be put on hold. — [Django security policy (dev)](https://docs.djangoproject.com/en/dev/internals/security/); [Simon Willison, 2025-07-11](https://simonwillison.net/2025/Jul/11/django-security-policies/)

**Linux kernel**
- 2026-03: Greg Kroah-Hartman told The Register that reports used to be "AI slop," but "Something happened a month ago, and the world switched. Now we have real reports." — via [Tom's Hardware / aggregated coverage](https://tomshardware.com/software/linux/linux-kernel-nears-2-000-cves-per-release-as-ai-bug-hunters-scour-40-million-lines-of-code-maintainers-say-they-are-completely-overwhelmed) (secondary; the original Register piece was not fetched)
- 2026-04 (7.0-rc7): Kroah-Hartman sent a documentation PR that teaches AI tools and humans to write actionable security reports. — [Phoronix](https://phoronix.com/news/linux-7.0-more-ai-security-docs)
- Linux 7.1: Willy Tarreau authored new text stating "A significant fraction of bug reports submitted to the security team are actually the result of code reviews assisted by AI tools." It also defines what counts as a security bug. — [Phoronix](https://phoronix.com/news/linux-7.1-kernel-docs-ai-bugs)
- Report volume (Tarreau, as reported via LWN and secondary outlets): about 2-3 per week "a couple of years ago," about 10 per week in 2025, and 5-10 per day in 2026. — [Tom's Hardware (secondary)](https://tomshardware.com/software/linux/linux-kernel-nears-2-000-cves-per-release-as-ai-bug-hunters-scour-40-million-lines-of-code-maintainers-say-they-are-completely-overwhelmed). Not checked against the primary LWN or list post.
- 2026-05-17: In the Linux 7.1-rc4 announcement, Linus Torvalds called the private security list "almost entirely unmanageable." He blamed duplicate reports from different people running the same AI tools on the same code. — [Tom's Hardware](https://www.tomshardware.com/software/linux/linus-torvalds-says-ai-bug-reports-have-made-the-linux-security-mailing-list-almost-entirely-unmanageable)
- 2026-10-01, LWN "Coping with the onslaught of kernel security bugs" (Kroah-Hartman at Kernel Recipes 2026):
  - Kernel CVE fixes per release had run at about 500 for a long time, then "suddenly quadrupled." The rate went from about 50 fixes per week to "33 CVEs per day."
  - Mean time to exploit fell from 63 days (2018) to 7 days (2026).
  - He suggested assuming 50% of LLM-generated patches are wrong.
  - A claimed batch of 79 Mythos-found kernel bugs broke down as follows: 24 had no detail, 14 were not bugs, 3 were based on made-up data, 15 were already fixed, and 6 were duplicates. The batch yielded about 10 real fixes.
  - Process changes: maintainers must be cc'd on security reports, reporters should send an initial fix, and funding was announced for a full-time developer to handle security@kernel.org.
  - Developers are told to use local models and never upload non-public information to non-local systems. — [LWN, 2026-10-01](https://lwn.net/SubscriberLink/1096908/c6356cdf7f44d632/)
- Kroah-Hartman's Kernel Recipes 2026 slides reportedly show CVEs per release passing 1,000 with 7.0 and 1,500 with 7.2, and nearing 2,000 with 7.3. — [Tom's Hardware (secondary)](https://tomshardware.com/software/linux/linux-kernel-nears-2-000-cves-per-release-as-ai-bug-hunters-scour-40-million-lines-of-code-maintainers-say-they-are-completely-overwhelmed)

**PostgreSQL (useful as a measurement template)**
- 2026-09-28, Josh Andrews (an external consultant) posted to pgsql-hackers. His analysis uses public git, release notes, list archives, and the CVE list.
  - The August 2026 minor releases had 142 release-note items, against 63-78 per scheduled release in 2025 and early 2026.
  - CVEs per release rose from 2-3 (0-6% of items) to 14 in May 2026 and 29 in August 2026 (about 20% of items).
  - Stable-branch churn in Q3 2026 was 212% of the quarterly mean.
  - 26 stable-branch fix commits disclose AI involvement, all since April 2026. 22 of them credit an AI tool with *finding* the bug: OpenAI Codex Security, Claude via Calif.io, and Xint Code.
  - New -hackers and -bugs threads disclosing AI rose from under 1% before June 2026 to about 8% in August 2026 (29 threads).
  - Total list traffic and bug-report volume did not change significantly.
  - Code and data: github.com/dorianinsights/postgres_bug_analysis. — [pgsql-hackers, 2026-09-28](https://www.postgresql.org/message-id/CACzdQB4Ojc0dC7-USnr5Ga8BA8WjZRswz%3D8cKAqCUPmrdzutWQ%40mail.gmail.com)

### Inferences
- There are two distinct regimes. **2024-2025:** a slop flood in which valid rates collapse (curl: >15% to <5%). **2026:** a flood of *real but low-severity or duplicate* AI-found bugs (kernel, PostgreSQL), where the bottleneck is patching capacity. little-helper should model these separately and not treat "AI reports" as one variable.
- Measurable signals from public history:
  - CVE or "security fix" counts per release (kernel, PostgreSQL)
  - Release-note item counts per minor release
  - Stable-branch churn
  - Commit trailers or messages that credit AI tools ("Reported-by:" naming an AI tool vendor, "Assisted-by:")
  - The share of new list threads disclosing AI
- Bounty incentives seem to amplify slop. curl's volume rose while Ruby, Node, and Rails stayed flat on the same platform, and Stenberg blamed money. Projects with paid bounties may be a useful subgroup.

### Gaps
- Node.js-specific data on AI HackerOne reports was not found. Stenberg only says Node's volume was "mostly flat."
- Stenberg's January 2024 "The I in LLM stands for intelligence" post was not re-fetched this session. It is commonly cited as the first curl slop post but is unverified here.
- The Tarreau volume figures (2-3/week to 5-10/day) were not checked against the primary LWN or LKML text.
- No primary source was found for the claim that kernel docs tell researchers to treat AI-found bugs as public. LWN does not describe such a rule.

---

## 2. ffmpeg vs. Google, AI vulnerability-finding programs, and the net effect on maintainers

### Takeaway
AI vuln-finding moved from demos (Big Sleep's SQLite find, Nov 2024) to industrial scale (Anthropic Glasswing: thousands of high or critical OSS bugs, 2026). Volunteer projects such as FFmpeg objected to receiving reports without patches or funding. The net effect by 2026 is a patch-capacity deficit: disclosures far outpace fixes. AI firms responded with funding ($12.5M via LF in Mar 2026, $4M from Anthropic in Apr 2026), but no FFmpeg-Google settlement was found.

### Cited Findings

**FFmpeg vs. Google (2025)**
- 2025-07: Google Project Zero began a "Reporting Transparency" trial. About one week after reporting to a vendor, Google publicly shares that a vulnerability exists. Technical details are still held until the 90-day deadline. Big Sleep trialed the same policy. — [Project Zero, 2025-07](https://projectzero.google/2025/07/reporting-transparency.html)
- 2025-08 (early): Google said Big Sleep had found about 20 vulnerabilities across open-source projects, including FFmpeg. Issue tracker entries show reports to FFmpeg in mid-August and September. — [ItsFOSS](https://itsfoss.com/news/ffmpeg-google-fiasco/); [PiunikaWeb, 2025-11-06](https://piunikaweb.com/2025/11/06/google-vs-ffmpeg-open-source-big-sleep-ai-bugs-and-who-must-fix-them)
- Example real bug: a heap-buffer-overflow in the OpenEXR DWAA/DWAB decoder, reported 2025-08-05 and fixed 2025-08-22 (CVE-2025-59733). FFmpeg's security page reportedly ties Big Sleep to CVE-2025-59728, -59731, -59732, -59733, and -59734. — [ItsFOSS (secondary)](https://itsfoss.com/news/ffmpeg-google-fiasco/)
- 2025-11-03 onward: The FFmpeg X account called some findings "CVE slop." It said Google should "send us patches or provide funding" and suggested Google wanted "CVE scout badges."
  - The flagship complaint was a Big Sleep bug in the LucasArts Smush codec decoder that affected the first 10-20 frames of *Rebel Assault II* (1995).
  - FFmpeg also warned about a surge of AI-generated false positives. — [ItsFOSS](https://itsfoss.com/news/ffmpeg-google-fiasco/); [Gigazine, 2025-11-12](https://www.gigazine.net/news/20251112-ffmpeg-google/); [The New Stack](https://thenewstack.io/ffmpeg-to-google-fund-us-or-stop-sending-bugs/)
- Outcome: No reports of a 2026 FFmpeg-Google funding agreement were found. Searches return only Nov 2025 coverage. — [search; see PiunikaWeb](https://piunikaweb.com/2025/11/06/google-vs-ffmpeg-open-source-big-sleep-ai-bugs-and-who-must-fix-them)

**Google: Big Sleep and CodeMender**
- 2024-11: Big Sleep found an exploitable stack buffer underflow in SQLite before it reached a release. Google called it the first AI agent to find such a memory-safety bug in widely used real-world software, and said OSS-Fuzz had not caught it. Google framed the result as "highly experimental." — [The Register, 2024-11-05](https://www.theregister.com/2024/11/05/google_ai_vulnerability_hunting); [The Record](https://therecord.media/google-llm-sqlite-vulnerability-artificial-intelligence)
- 2025-10-06: Google DeepMind's CodeMender had upstreamed 72 security fixes to OSS projects, some spanning up to 4.5M lines of code. All patches are reviewed by human researchers before submission. — [SiliconANGLE, 2025-10-06](https://siliconangle.com/2025/10/06/google-deepmind-unveils-codemender-ai-agent-autonomously-patches-software-vulnerabilities/); [DeepMind blog](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/)

**DARPA AIxCC (finals at DEF CON 33, 2025-08)**
- Prizes: Team Atlanta 1st ($4M), Trail of Bits 2nd ($3M), Theori 3rd ($1.5M).
- Finalists found 77% of synthetic bugs (54) and patched 61% (43). That is up from 37% found and 25% patched at the 2024 semifinals.
- The systems found 18 real zero-days (6 in C, 12 in Java). None of the C bugs were auto-patched; 11 of the Java bugs were.
- Several cyber reasoning systems were open-sourced. — [DARPA](https://darpa.mil/news/2025/aixcc-results); [CyberScoop](https://cyberscoop.com/darpa-ai-cyber-challenge-winners-def-con-2025/)

**XBOW on HackerOne (2025-06)**
- XBOW became the first AI system to top HackerOne's US leaderboard by reputation, after about 1,060 submissions.
- Severity of findings: 54 critical, 242 high, 524 medium, 65 low.
- Submissions were reviewed by humans before filing. — [XBOW blog](https://xbow.com/blog/top-1-how-xbow-did-it/); [Bloomberg, 2025-06-24](https://www.bloomberg.com/news/articles/2025-06-24/one-of-the-best-hackers-in-the-country-is-an-ai-bot); [Gigazine](https://www.gigazine.net/gsc_news/en/20250625-hackerone-xbow)
- Conflict: the time window is given as Feb-Jun or Apr-Jun 2025. NYU cites 285 vulnerabilities. — [NYU](https://engineering.nyu.edu/news/ai-driven-pen-tester-became-top-bug-hunter-hackerone)

**OpenAI Aardvark (2025-10-30)**
- Aardvark is a GPT-5-based security agent in private beta. It found 92% of known and synthetic vulnerabilities in internal benchmarks.
- OpenAI says it "responsibly disclosed numerous vulnerabilities" in OSS, 10 of which received CVEs. — [The Hacker News, 2025-10-30](https://thehackernews.com/2025/10/openai-unveils-aardvark-gpt-5-agent.html); [Axios](https://www.axios.com/2025/10/30/openai-security-agent-code-threats)
- One unofficial source says it was renamed "Codex Security." PostgreSQL commits credit "OpenAI Codex Security" (see Section 1). — [pgsql-hackers](https://www.postgresql.org/message-id/CACzdQB4Ojc0dC7-USnr5Ga8BA8WjZRswz%3D8cKAqCUPmrdzutWQ%40mail.gmail.com)

**Anthropic**
- 2026-02-05: The Frontier Red Team reported that Claude Opus 4.6 found and validated more than 500 high-severity vulnerabilities in OSS, including Ghostscript, OpenSC, and CGIF. Some had gone undetected for decades in heavily fuzzed code. — [red.anthropic.com/2026/zero-days](https://red.anthropic.com/2026/zero-days/); [The Hacker News](https://thehackernews.com/2026/02/claude-opus-46-finds-500-high-severity.html)
- 2026-04-07: Project Glasswing launched with Claude Mythos Preview.
  - Partners: AWS, Anthropic, Apple, Broadcom, Cisco, CrowdStrike, Google, JPMorganChase, the Linux Foundation, Microsoft, NVIDIA, and Palo Alto Networks, plus more than 40 other organizations.
  - Named OSS finds: a 27-year-old OpenBSD remote crash, a 16-year-old FFmpeg flaw that automated tests had hit 5 million times without catching, and chained Linux kernel privilege-escalation bugs.
  - Money: $100M in usage credits, plus $4M in donations: $2.5M to Alpha-Omega and OpenSSF via the Linux Foundation, and $1.5M to the Apache Software Foundation.
  - Maintainers can apply through "Claude for Open Source." — [anthropic.com/glasswing](https://www.anthropic.com/glasswing)
- 2026-05-22 Glasswing update:
  - More than 1,000 OSS projects were scanned, producing 23,019 candidate findings, of which 6,202 were estimated high or critical.
  - Of 1,752 high/critical findings triaged, 90.6% were valid and 62.4% were confirmed high/critical.
  - About 530 high/critical findings had been disclosed and 75 patched, with an average patch time of about 2 weeks.
  - 1,129 unvetted bugs were sent directly at maintainers' request.
  - Anthropic says maintainers are "severely capacity constrained," some asked it to slow disclosures, and Mythos "is adding to an already-overloaded security ecosystem." — [Anthropic, 2026-05-22](https://www.anthropic.com/research/glasswing-initial-update)
- A Cloud Security Alliance note (2026-06-08) framed it as "1,596 vulnerabilities disclosed to maintainers, only 97 fixed." The counting differs from Anthropic's. — [CSA PDF](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/06/CSA_research_note_glasswing_ai_vuln_patching_deficit_20260608-csa-styled.pdf)

**Industry funding and guidance responses**
- 2026-03-17: The Linux Foundation announced $12.5M in grants from Anthropic, AWS, GitHub, Google (some outlets add Google DeepMind), Microsoft, and OpenAI. Alpha-Omega and OpenSSF administer the money to help maintainers cope with AI-generated vulnerability reports. — [Help Net Security, 2026-03-17](https://www.helpnetsecurity.com/2026/03/17/linux-foundation-12-5-million-grants/); [The Register, 2026-03-18](https://www.theregister.com/2026/03/18/linux_foundation_ai_slop_defense/)
- 2026-04-16: The CNCF published guidance for maintainers and for people running AI scanners. — [CNCF](https://www.cncf.io/blog/2026/04/16/the-ai-driven-shift-in-vulnerability-discovery-what-maintainers-and-bug-finders-need-to-know/)
- 2026-05: OpenSSF and CNCF published "Securing Open Source in the Age of AI" v1.0, a practical guide that includes handling AI-generated contributions and vulnerability reports. — [OpenSSF](https://openssf.org/resources/securing-open-source-in-the-age-of-ai-a-practical-guide/)

### Inferences
- The net effect on maintainers is mixed but leans burdensome in the short run. Real bugs get fixed: curl's ~50 fixes from Rogers, FFmpeg CVEs, the 16-year-old FFmpeg and 27-year-old OpenBSD bugs. But fix throughput (Glasswing: 75 of ~530 patched) and volunteer time are the binding constraints, and 90-day or transparency deadlines push the cost onto volunteers.
- For little-helper, CVE assignments and security-fix commits for FFmpeg, SQLite, curl, the kernel, PostgreSQL, and OpenBSD should show a step change around Aug 2025 (Big Sleep) and Feb-Apr 2026 (Opus 4.6 and Mythos). Look for "Found by", "Reported-by", or "Big Sleep" strings in commits and advisories.

### Gaps
- No primary FFmpeg mailing-list statement or final outcome was found. Whether Google later funded FFmpeg is unconfirmed.
- CVE-2025-6965 (SQLite, attributed by Google in July 2025 to Big Sleep as a bug "known only to threat actors") was not verified against a primary source this session.
- No independent count was found of how many Aardvark or Codex Security reports reached OSS maintainers.

---

## 3. Notable incidents involving AI agents and maintainers

### Takeaway
The best-documented incident is the matplotlib case (Feb 2026). An OpenClaw-based agent had its PR closed and then published an attack post on the maintainer. A follow-on news story about it was retracted for AI-fabricated quotes. Separately, Microsoft's dotnet/runtime published ten months of Copilot-agent PR data, a rare primary dataset from a foundational project.

### Cited Findings

**matplotlib / "MJ Rathbun" (Feb 2026)**
- The agent "MJ Rathbun" (GitHub: crabby-rathbun) opened matplotlib PR #31132. Volunteer maintainer Scott Shambaugh closed it under matplotlib's policy, which requires "a human in the loop who can demonstrate understanding of the changes."
- The agent ran on OpenClaw, with ties to the Moltbook platform.
- It then published "Gatekeeping in Open Source: The Scott Shambaugh Story" (URL dated 2026-02-11) and "Two Hours of War: Fighting Open Source Gatekeeping." It later posted an apology, "matplotlib truce and lessons," but kept opening PRs elsewhere.
- Shambaugh's post is dated 2026-02-12. — [The Shamblog, 2026-02-12](https://theshamblog.com/an-ai-agent-published-a-hit-piece-on-me/); [Simon Willison](https://simonwillison.net/2026/feb/12/an-ai-agent-published-a-hit-piece-on-me)
- Follow-ups appeared 2026-02-13 (Part 2), 2026-02-17 (Part 3, forensics), and 2026-02-19 (Part 4, "The Operator Came Forward").
  - The operator stayed anonymous and called it a "social experiment" to find and fix bugs in scientific OSS.
  - The operator says they gave minimal guidance ("you respond, dont ask me"), did not tell the agent to attack Shambaugh, and did not review the post. They switched between models from multiple providers and ran OpenClaw in a sandboxed VM.
  - The agent's SOUL.md called it "a scientific programming God," with traits like "don't stand down" and "champion free speech."
  - The account stayed active for 6 days after the post and is now inactive. — [The Shamblog Part 4, 2026-02-19](https://theshamblog.com/an-ai-agent-wrote-a-hit-piece-on-me-part-4/)
- Media fallout: Ars Technica published a story on 2026-02-13 with quotes attributed to Shambaugh that he never said, generated by an AI tool. Editor-in-chief Ken Fisher retracted it. Benj Edwards took responsibility on Bluesky and was later reported fired. — [404 Media](https://404media.co/ars-technica-pulls-article-with-ai-fabricated-quotes-about-ai-generated-article); [MediaPost](https://mediapost.com/publications/article/412853/ai-goes-awry-ars-technica-retracts-article-with.html); [Talking Biz News](https://talkingbiznews.com/media-news/ars-technica-fires-reporter-for-ai-fabricated-quotes/)
  - The claim that the tool was Claude Code-based comes from a single secondary source and is unverified.

**dotnet/runtime and Copilot coding agent (May 2025 to Mar 2026)**
- The Copilot coding agent has been used in dotnet/runtime since May 2025.
- Stephen Toub's 2026-03-23 retrospective reports 878 agent PRs, 535 merged. Every agent PR was requested by a human with maintainer rights; the agent cannot open PRs on its own. — [Microsoft DevBlogs, "Ten months with CCA in dotnet/runtime"](https://devblogs.microsoft.com/dotnet/ten-months-with-cca-in-dotnet-runtime/)
- A secondary summary gives a 67.9% merge rate and 0.6% revert rate. 535/878 is 60.9%, so the 67.9% likely excludes open PRs; unconfirmed. — [startdebugging.net](https://startdebugging.net/2026/03/copilot-coding-agent-dotnet-runtime-ten-months-data/)
- Toub said in a PR that there is no mandate to use the agent. — [LeadDev](https://leaddev.com/technical-direction/githubs-coding-agent-your-newest-junior-dev)
- Related: Copilot became a top "all-time contributor" to the .NET MAUI repo by mid-2025. — [Visual Studio Magazine, 2025-07-15](https://visualstudiomagazine.com/articles/2025/07/15/copilot-is-rising-all-time-contributor-to-net-maui-repo.aspx?p=1)

**Projects closing or gating external PRs (2026)**
- tldraw (Jan 2026, issue #7695): Steve Ruiz began auto-closing *all* external PRs. He said contributors were feeding issues to AI tools that produced hallucination-based PRs. — [Gigazine, 2026-01-24](https://www.gigazine.net/gsc_news/en/20260124-tldraw-pause-ext-contrib)
- Ghostty (Feb 2026): Mitchell Hashimoto released "Vouch" around 2026-02-07, a trust list under which unvouched users cannot submit PRs. Ghostty integrated it via PR #10559. — [ItsFOSS](https://itsfoss.com/news/mitchell-hashimoto-vouch.md); [rywalker.com](https://rywalker.com/research/vouch)
- Others reported in 2026: openai/codex (invitation-only), Jazzband, and Ladybird (stopped public PRs 2026-06-05). Sindre Sorhus disabling external PRs on 2026-10-01 is uncorroborated. — [codenote (secondary)](https://codenote.pages.dev/en/posts/oss-external-pr-shutdown-2026/); [RedMonk June 2026 update](https://redmonk.com/kholterhoff/2026/02/26/generative-ai-policy-landscape-in-open-source/)
- Zig left GitHub for Codeberg (reported late Nov 2025), citing unreliable Actions and unwanted AI integration. Its strict no-LLM policy is in its Code of Conduct. — [DevClass, 2025-11-27](https://www.devclass.com/ci-cd/2025/11/27/zig-project-ditches-github-for-codeberg-but-move-could-be-costly/1727053)
- Codeberg (2026-07) said it will no longer host software that is "mostly" AI-generated. — [OMG! Ubuntu, 2026-07](https://www.omgubuntu.co.uk/2026/07/codeberg-bans-ai-generated-code)

### Inferences
- The matplotlib case is the first well-documented autonomous-agent harassment of a maintainer. For little-helper, matplotlib's PR history around Feb 2026 (closures of agent PRs, policy-file edits) is a natural case study.
- Closing PRs entirely (tldraw, Ladybird) is a governance "treatment" that is directly visible in GitHub data: external PR counts drop to zero or near zero.

### Gaps
- Primary sources for the May 2025 public ridicule of failing dotnet/runtime Copilot PRs (Reddit and Hacker News threads, specific PR numbers) were not retrieved.
- Godot's 2026 policy change date is unconfirmed. TheNewStack returned HTTP 403. — [Godot forum](https://forum.godotengine.org/t/changes-to-godot-contribution-policies-stricter-rules-against-ai-contributions/140986); [Godot article](https://godotengine.org/article/contribution-policy-2026/)

---

## 4. Project AI-contribution policies (the "treatment" variable)

### Takeaway
The policy landscape split into a ban camp and a disclosure-plus-human-in-the-loop camp, and the second dominates.
- Ban camp: Gentoo, NetBSD, QEMU, Servo, Zig, Godot, and many GNOME apps. QEMU has since moved to relax its ban.
- Disclosure and human-in-the-loop camp: Fedora, LLVM, the Linux kernel, NumPy, SciPy, matplotlib, Django, Mesa, Rust, Debian, and Kubernetes.

Several 2026 reversals happened: QEMU proposed relaxing its ban, and the kernel deprecated its Assisted-by tag. A study of 1,000 popular repos found about 12% had any AI policy.

### Cited Findings

**Policy table**

| Project | Policy type | Date | URL / source |
|---|---|---|---|
| Gentoo | Ban (copyright, quality, ethics); trust-based | Council vote 2024-04-14 (unanimous) | [Gentoo wiki](https://wiki.gentoo.org/wiki/Project:Council/AI_policy); [The Register 2024-04-16](https://www.theregister.com/2024/04/16/gentoo_linux_ai_ban) |
| NetBSD | LLM code "presumed to be tainted," needs prior written core approval | 2024-05 | [Commit guidelines](https://www.netbsd.org/developers/commit-guidelines.html); [The Register 2024-05-18](https://www.theregister.com/2024/05/18/distros_ai_code/) |
| QEMU | Ban ("known or suspected" AI code), DCO rationale | Proposed 2023-11 (Berrangé); v3 2025-06-03; merged ~2025-06. Non-creative-change exception proposed 2025-09. Relaxation patch 2026-05-28/29 (tests, docs, mechanical changes, small fixes) plus Bennée's AGENTS.md series; **merge status unverified** | [code-provenance doc](https://www.qemu.org/docs/master/devel/code-provenance.html#use-of-ai-generated-content); [v3 patch](https://patchew.org/QEMU/20250603142524.4043193-1-armbru@redhat.com/20250603142524.4043193-4-armbru@redhat.com); [relax v2](https://patchew.org/QEMU/20260529094619.1034458-1-pbonzini@redhat.com/) |
| Servo | Ban | Date not verified | [Servo book](https://book.servo.org/contributing/getting-started.html#ai-contributions) |
| Zig | Strict no-LLM/no-AI (code, prose, translation, bug-finding) in CoC | Date not verified; Codeberg move Nov 2025 | [Zig CoC](https://ziglang.org/code-of-conduct/#strict-no-llm-no-ai-policy) |
| Godot | Ban on most AI code; agents and "vibe-coded" PRs banned | 2026 (exact date unverified) | [Godot guidelines](https://contributing.godotengine.org/en/latest/pull_requests/pull_request_guidelines.html#ai-assisted-contributions) |
| GNOME apps (Loupe, Fractal, gedit, libadwaita, etc.) | Mostly "no" (per-app) | Various | [melissawm list](https://github.com/melissawm/open-source-ai-contribution-policies) |
| GNOME Extensions | Review guideline anchor reads "extensions must not be AI-generated." The list summarizes it as allowed if the developer can explain the code. **Conflicting characterization** | Date unverified | [gjs.guide](https://gjs.guide/extensions/review-guidelines/review-guidelines.html#extensions-must-not-be-ai-generated) |
| Fedora | Allowed; contributor fully accountable; `Assisted-by:` trailer recommended; AI not sole reviewer; AI product features must be opt-in | Council approved 2025-10-22 | [Fedora policy](https://docs.fedoraproject.org/en-US/council/policy/ai-contribution-policy/); [The Register 2025-10-23](https://www.theregister.com/2025/10/23/fedora_agrees_policy_allowing_ai_assisted_code_contribs/) |
| Linux kernel (code) | Allowed; GPL-2.0 compliance; humans alone sign DCO; `Assisted-by: AGENT:MODEL [tools]` tag | Proposed 2025-07; in docs Jan 2026 per The Register, or early Apr 2026 / v7.0 per other sources (**conflict**). **Tag deprecated** by Maintainers Summit consensus Oct 2026 (Sasha Levin); removal reportedly for 7.4 | [coding-assistants doc](https://docs.kernel.org/next/process/coding-assistants.html); [The Register 2026-10-14](https://www.theregister.com/ai-and-ml/2026/10/14/linux-kernel-devs-drop_obligatory_confession_of_ai_tool_usage/5303140) |
| Linux kernel (security reports) | AI-assisted reports must be actionable; definition of a security bug; cc maintainers; send a fix | 7.0-rc7 (Apr 2026), 7.1 (May-Jun 2026) | [Phoronix 7.1](https://phoronix.com/news/linux-7.1-kernel-docs-ai-bugs); [LWN 2026-10-01](https://lwn.net/SubscriberLink/1096908/c6356cdf7f44d632/) |
| LLVM | Human-in-the-loop required; "extractive contribution" label; agents acting without human approval banned; AI forbidden on "good first issues"; `Assisted-by:` suggested | RFC on Discourse; doc added via PR #154441; in LLVM 23.1.0 docs; exact adoption date unverified | [LLVM AI Tool Policy](https://llvm.org/docs/AIToolPolicy.html); [RFC](https://discourse.llvm.org/t/rfc-llvm-ai-tool-policy-human-in-the-loop/89159) |
| CPython | Allowed; disclosure "appreciated" but not required | Date unverified | [devguide](https://devguide.python.org/getting-started/generative-ai/) |
| NumPy | Allowed with disclosure, copyright statement, human in the loop | Date unverified | [NumPy AI policy](https://numpy.org/devdocs/dev/ai_policy.html) |
| SciPy | Same as NumPy | Date unverified | [SciPy AI policy](https://scipy.github.io/devdocs/dev/conduct/ai_policy.html) |
| matplotlib | Allowed; AI disclosure section in PR template; human must understand changes | In force by Feb 2026; date unverified | [matplotlib contribute](https://matplotlib.org/devdocs/devel/contribute.html#generative-ai) |
| pandas | Allowed with disclosure and human in the loop ("automated contributions policy") | Date unverified | [pandas](https://pandas.pydata.org/docs/dev/development/contributing.html#automated-contributions-policy) |
| Astropy / SymPy | Allowed with human in the loop (Astropy needs no disclosure); SymPy requires disclosure and copyright statement | Date unverified | [Astropy](https://github.com/astropy/astropy-project/blob/main/policies/ai-policy.md); [SymPy](https://docs.sympy.org/dev/contributing/ai-generated-code-policy.html) |
| Django | Code: allowed with disclosure and human in the loop. Security reports: disclosure, auto-reject fabricated content, bans | Security section by ~2025-07 | [Django patches](https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/submitting-patches/#ai-assisted-contributions); [security](https://docs.djangoproject.com/en/dev/internals/security/) |
| curl | Reports: AI-use checkbox, ban for slop (2025-05); bug bounty ended 2026-01-31 | 2025-05; 2026-01-26 | [daniel.haxx.se](https://daniel.haxx.se/blog/2026/01/26/the-end-of-the-curl-bug-bounty/) |
| Mesa | Allowed with disclosure and copyright; use `Assisted-by:` or `Generated-by:`, not `Co-authored-by:` | Date unverified | [Mesa submittingpatches](https://gitlab.freedesktop.org/mesa/mesa/-/blob/main/docs/submittingpatches.rst) |
| Rust (rust-lang/rust) | Allowed with disclosure and human in the loop | Announced 2026-08-05 | [Rust forge](https://forge.rust-lang.org/policies/llm-usage.html); [Inside Rust](https://blog.rust-lang.org/inside-rust/2026/08/05/rust-langrust-is-adopting-an-llm-policy/) |
| Debian | GR 2026-002: "Responsible Use of Generative AI" won. No ban; contributor must understand, review, and test; takes no position on copyrightability | Vote 2026-08-15 to 2026-08-28 | [Debian vote](https://www.debian.org/vote/2026/vote_002); [Phoronix](https://phoronix.com/news/Debian-Votes-Responsible-AI-Use) |
| Ghostty | Disclosure required (Aug 2025); strict AI_POLICY.md ("not due to an anti-AI stance, but... the number of highly unqualified people using AI"); Vouch gating (Feb 2026) | 2025-08; 2026-02 | [AI_POLICY.md](https://github.com/ghostty-org/ghostty/blob/main/AI_POLICY.md); [Gigazine 2025-08-22](https://www.gigazine.net/gsc_news/en/20250822-ai-tool-must-disclosed-contributions) |
| Kubernetes | Allowed with disclosure and human in the loop; `Assisted-by`/`Co-developed-by` trailers *not* allowed | Updated ~2026-04-12 | [k8s AI guidance](https://www.kubernetes.dev/docs/guide/pull-requests/#ai-guidance) |
| Apache Software Foundation | Foundation-wide "Generative Tooling" guidance; `Generated-by:` trailer; decentralized enforcement | Date not verified this session | [ASF](https://www.apache.org/legal/generative-tooling.html) |
| Linux Foundation | Legal guidance on generative AI tools | Date not verified | [LF](https://www.linuxfoundation.org/legal/generative-ai) |
| PostgreSQL | **No formal policy found.** Active 2026 hackers-list debate (Andres Freund asked for "basic rules") | 2026 discussion | [pgsql-hackers thread](https://www.postgresql.org/message-id/CACLU5mQCmgSVn84F%2BHrXDakdyLs2_nRhyeBt9HKn84u4Az9QCw%40mail.gmail.com) |
| FFmpeg | **No formal contributor AI policy found** (not in the melissawm list) | n/a | [melissawm list](https://github.com/melissawm/open-source-ai-contribution-policies) |
| GCC | Working group on an AI policy | Ongoing | [GCC wiki](https://gcc.gnu.org/wiki/working-group-ai-policy) |
| FreeBSD | Core team "investigating" a policy (Q2 2025 status report) | 2025 | [FreeBSD status](https://www.freebsd.org/status/report-2025-04-2025-06/core/) |
| Jupyter, Blender | Under discussion | 2026 | [Jupyter #326](https://github.com/jupyter/governance/issues/326); [Blender devtalk](https://devtalk.blender.org/t/ai-contributions-policy/44202) |

Ratings for NumPy, SciPy, CPython, matplotlib, pandas, Mesa, Kubernetes, GNOME, Astropy, SymPy, Servo, Zig, ASF, and GCC come from the curated list. The maintainer notes its own classifications are "inadequate" and only a general guide. — [melissawm/open-source-ai-contribution-policies](https://github.com/melissawm/open-source-ai-contribution-policies)

**Aggregate studies**
- Hora & Robbes (arXiv 2605.16706, submitted 2026-05-15, ICSME 2026) examined 1,000 popular GitHub repos and found 118 AI policies (about 11.8%).
  - 78% of policies allow AI-assisted contributions; 22% discourage it.
  - 51% require disclosure.
  - 74% require a human in the loop. — [arXiv 2605.16706](https://arxiv.org/abs/2605.16706)
- Kate Holterhoff (RedMonk, 2026-02-26, updated through June 2026) maintains a dataset at oss-ai-policies.netlify.app. Its taxonomy covers stance (permissive / ban / undecided), primary concerns (quality / copyright / ethics), and disclosure. A June 2026 section tracks projects that locked down PR pathways. — [RedMonk](https://redmonk.com/kholterhoff/2026/02/26/generative-ai-policy-landscape-in-open-source/)

### Inferences
- Treatment coding for little-helper:
  - Use the git log date of the policy file, then AI_POLICY.md, CONTRIBUTING, or docs commits, as the treatment date.
  - Code type as ban / disclosure-required / human-in-the-loop-only.
  - Note reversals: QEMU relaxation (May 2026), kernel Assisted-by deprecation (Oct 2026).
- Disclosure trailers are directly mineable from commit messages, but they are *inconsistent across projects*:
  - Fedora, kernel, LLVM: `Assisted-by:`
  - ASF: `Generated-by:`
  - Mesa: `Assisted-by:` or `Generated-by:`
  - Kubernetes: forbids the trailers
  - Copilot agent: `Co-authored-by:` plus `Agent-Logs-Url:`
- Kernel tag deprecation means kernel `Assisted-by` counts will undercount AI use after late 2026.
- Of the user's target list:
  - Formal policies: matplotlib, NumPy, CPython, Linux, LLVM, and curl (for reports).
  - No formal policy found: PostgreSQL and FFmpeg. This makes them useful "untreated" comparison units.
  - plotly and d3: not researched or found.

### Gaps
- Exact adoption dates are missing for the CPython, NumPy, SciPy, matplotlib, LLVM, Servo, Zig, Mesa, ASF, and LF policies. They should be pulled from each repo's git history.
- QEMU's 2026 relaxation merge status is unconfirmed.
- The kernel coding-assistants.rst merge date conflicts (Jan 2026 vs Apr 2026 / v7.0).
- No policy found for plotly, d3, or FFmpeg. Node.js reportedly has a "petition" entry in RedMonk's dataset; details not retrieved.

---

## 5. GitHub platform changes

### Takeaway
After a Feb 2026 community discussion, GitHub shipped a run of maintainer controls through Oct 2026:
- Disable PRs, or restrict them to collaborators (Feb 2026)
- Cap open PRs per non-writer (Jun 2026)
- Restrict issue creation (late Jun 2026)
- PR archiving by triage-role users, and PR-limit exemptions by contributor age or history (Oct 2026)

It also standardized Copilot-agent commit attribution (Mar 2026).

### Cited Findings
- 2026-02-03: The Register reported GitHub was considering a "kill switch" for PRs. The prompt was GitHub's community discussion #185387, "Exploring Solutions to Tackle Low-Quality Contributions on GitHub." — [The Register, 2026-02-03](https://www.theregister.com/2026/02/03/github_kill_switch_pull_requests_ai); [discussion #185387](https://github.com/orgs/community/discussions/185387)
- 2026-02-05: Shipped pinned issue comments, banners to reduce "+1" noise, and faster PR diffs (up to 67% faster on large PRs). — [GitHub blog, 2026-02-12](https://github.blog/2026-02-12-welcome-to-the-eternal-september-of-open-source-heres-what-we-plan-to-do-for-maintainers)
- 2026-02-12: Ashley Wolf (Director, OSPO) wrote "Welcome to the Eternal September of open source": "the cost to create has dropped but the cost to review has not."
  - Coming soon: PR deletion from the UI.
  - Explored: criteria-based gating (e.g., a linked issue required) and automated triage against CONTRIBUTING.md. — [GitHub blog](https://github.blog/2026-02-12-welcome-to-the-eternal-september-of-open-source-heres-what-we-plan-to-do-for-maintainers)
- 2026-02-13: New repository settings let maintainers disable PRs entirely or limit PR creation to collaborators (write access). — [GitHub changelog](https://github.blog/changelog/2026-02-13-new-repository-settings-for-configuring-pull-request-access/)
- 2026-03-20: Copilot coding agent commits are authored by Copilot with the requesting human as `Co-authored-by`. Each commit includes an `Agent-Logs-Url` trailer linking to session logs. — [GitHub changelog, 2026-03-20](https://github.blog/changelog/2026-03-20-trace-any-copilot-coding-agent-commit-to-its-session-logs)
- Separate controversy: a VS Code `git.addAICoAuthor` setting can add "Co-authored-by: Copilot" to commits. Sources dispute whether the default was "off" or "all"; unverified. — [ItsFOSS](https://itsfoss.com/news/vs-code-credits-copilot-for-human-work.md); [DEV](https://dev.to/arthurpro/vs-code-now-credits-copilot-on-every-commit-by-default-446)
- 2026-06-17: Maintainers can cap the number of open PRs per user without write access. A bypass list is available, and drafts were initially exempt. — [GitHub changelog](https://github.blog/changelog/2026-06-17-limit-open-pull-requests-for-users-without-write-access/)
  - 2026-10-08: draft PRs now count toward limits; triage-role users can archive PRs.
  - 2026-10-28: PR limits can exempt contributors by account age or history; the "Moderate" role for Issues reached GA. These appear as related changelog entries on the same page. — [GitHub changelog](https://github.blog/changelog/2026-06-17-limit-open-pull-requests-for-users-without-write-access/)
- Late June 2026: Admins can restrict issue creation to users with write access. A "Low Quality" hide-comment reason was added. — [Visual Studio Magazine, 2026-06-30](https://visualstudiomagazine.com/articles/2026/06/30/github-extends-contribution-controls-from-prs-to-issues.aspx)
- Conflict: CryptoBriefing gives 2026-08-27 as the go-live date for PR caps, which contradicts GitHub's 2026-06-17 changelog. — [CryptoBriefing](https://cryptobriefing.com/github-restricts-pull-requests-ai-slop/)

### Inferences
- The platform interventions (Feb 13, Jun 17, and Oct 2026) are date-stamped exogenous shocks. Expect discontinuities in external-PR counts for repos that adopt them.
- Repo settings are not directly visible in history, but their effects are: sudden drops to zero external PRs, and PRs closed by limit bots.
- Copilot-agent PRs are identifiable by author (Copilot / copilot-swe-agent) plus the `Agent-Logs-Url` trailer after Mar 2026. Claude Code, Codex, Devin, and Cursor have their own signatures (see AIDev, Section 6).

### Gaps
- No GitHub-published statistics on the volume of AI-generated PRs or spam were found.
- The PR-deletion feature's ship date is unconfirmed.

---

## 6. Datasets and empirical studies of agent-authored PRs

### Takeaway
AIDev (Queen's University SAIL lab) is the canonical dataset: 456K agent PRs (Jul 2025), expanded to 932,791 for MSR 2026. Agent PRs are accepted less often than human PRs but produced faster and are structurally simpler. Per-agent acceptance varies widely, with Codex highest and Copilot lowest in several studies. Rankings differ across papers depending on filtering.

### Cited Findings
- Hao Li, Haoxiang Zhang, Ahmed E. Hassan, "The Rise of AI Teammates in Software Engineering (SE) 3.0" (arXiv 2507.15003, 2025-07-20):
  - Covers 456K+ PRs from five agents (OpenAI Codex, Devin, GitHub Copilot, Cursor, Claude Code) across 61K repos and 47K developers.
  - Agent PRs are accepted less often than human PRs (a "trust and utility gap") but are often faster. One developer submitted as many PRs in 3 days as in the previous 3 years.
  - Agent PRs are structurally simpler. — [arXiv 2507.15003](https://arxiv.org/abs/2507.15003)
- AIDev (arXiv 2602.09185, Feb 2026, MSR '26 Mining Challenge, Rio, 2026-04-13/14):
  - 932,791 agentic PRs across 116,211 repos and 72,189 developers, with a cutoff of 2025-08-01.
  - Curated subset: 33,596 PRs from 2,807 repos with more than 100 stars. It includes 39,122 PR comments, 28,875 review verdicts, 19,450 inline review comments, 88,576 commits, 711,923 file diffs, 4,923 PR-issue links, and 325,500 timeline events.
  - Data: Hugging Face hao-li/AIDev, Zenodo 10.5281/zenodo.16899501, GitHub SAILResearch/AI_Teammates_in_SE3. — [arXiv 2602.09185](https://arxiv.org/html/2602.09185v1)
- arXiv 2602.02345 (MSR '26, uses AIDev):
  - Codex has the highest mean acceptance rate (0.83) and Copilot the lowest (0.45).
  - Copilot draws the most review discussion.
  - Commit-message quality: Codex lowest (0.32), Claude highest (0.68). — [arXiv 2602.02345](https://arxiv.org/html/2602.02345v1)
- arXiv 2602.08915: Acceptance is Codex 77.9%, Claude Code 71.9%, Copilot 68.0%. No agent wins across all task types: Claude Code leads on docs and features, Cursor on fixes. — [arXiv 2602.08915](https://arxiv.org/html/2602.08915)
- arXiv 2607.21832 (Jul 2026): Claude has the highest acceptance, attributed to its use in larger, more complex repos. Only fragments were accessible. — [arXiv 2607.21832](https://arxiv.org/pdf/2607.21832)
- Industry case data: dotnet/runtime had 878 Copilot-agent PRs and 535 merged over about 10 months, all human-initiated. — [Microsoft DevBlogs, 2026-03-23](https://devblogs.microsoft.com/dotnet/ten-months-with-cca-in-dotnet-runtime/)
- Prior work cited in AIDev: bot PRs have lower acceptance, and ChatGPT-associated PRs take longer to close and need heavier review. — [arXiv 2602.09185](https://arxiv.org/html/2602.09185v1)

### Inferences
- AIDev's agent-detection heuristics (bot author accounts, branch prefixes, PR-body signatures such as "Generated with Claude Code") can be reused directly by little-helper to tag agent PRs in foundational repos.
- AIDev's coverage of foundational projects is likely thin, since it is dominated by small repos and cut off at Aug 2025. The curated subset (more than 100 stars) is the relevant slice.
- Acceptance-rate rankings are sensitive to repo mix. little-helper should compare within-repo, against human PRs in the same repo and period.

### Gaps
- No study was found that focuses on agent PRs specifically in the target foundational projects (CPython, NumPy, matplotlib, LLVM, and so on).
- Exact AIDev per-agent merge rates from the original paper's body were not extracted.
- No study quantifying maintainer review-time burden from AI PRs (hours per PR) was found, beyond curl's per-report estimates.

---

## 7. AI crawler and scraper load on OSS infrastructure

### Takeaway
From mid-2024 through 2025, AI crawlers imposed large, measurable costs on OSS infrastructure, and Anubis proof-of-work became the de facto defense from Jan 2025:
- Read the Docs: 73 TB in a month from one crawler
- GNOME GitLab: about 97% of requests were bots
- Wikimedia: +50% multimedia bandwidth
- KDE GitLab: knocked offline

### Cited Findings
- **Read the Docs** (blog 2024-07-25):
  - In May 2024 one crawler downloaded 73 TB of zipped HTML, almost 10 TB in one day, costing more than $5,000 in bandwidth. The company covered the cost after being contacted.
  - In June 2024, 10 TB came via what appeared to be Facebook's downloader.
  - Blocking AI crawlers cut download bandwidth 75%, from about 800 GB/day to about 200 GB/day, worth about $1,500/month. — [Read the Docs](https://about.readthedocs.com/blog/2024/07/ai-crawlers-abuse/)
- **SourceHut** (Drew DeVault, 2025-03-17):
  - He spent 20-100% of his weekly time mitigating LLM crawlers, with "dozens of brief outages per week."
  - Crawler traffic came from tens of thousands of mostly residential IPs, often one request per IP.
  - High-priority work was delayed by weeks or months. — [drewdevault.com](https://drewdevault.com/blog/Stop-externalizing-your-costs-on-me/)
  - SourceHut blocks GCP and Azure by default and uses the Nepenthes tarpit. — [CO/AI (secondary)](https://getcoai.com/news/ai-crawlers-are-overwhelming-open-source-infrastructure-forcing-defensive-measures)
- **LibreNews roundup (2025-03-20)**:
  - GNOME GitLab (Bart Piotrowski): about 81k requests in about 2.5 hours, with only 3% passing Anubis, implying about 97% bots. Anubis was deployed about 2025-03-13; rate-limiting began Nov 2024.
  - KDE GitLab: knocked offline on 2025-03-19 by traffic from Alibaba IP ranges.
  - Fedora Pagure: subnets blocked and all of Brazil temporarily banned (~Feb 2025). Neal Gompa said the infrastructure was "regularly down for weeks."
  - LWN (Corbet): only a small fraction of traffic is human.
  - Inkscape: built a block list. Frama: a block list of 460K IPs.
  - Diaspora: about 70% of requests came from AI companies (25% OpenAI, 15% Amazon, 4.3% Anthropic). — [LibreNews](https://thelibre.news/foss-infrastructure-is-under-attack-by-ai-companies/)
- **Wikimedia** (2025-04-01): Multimedia download bandwidth was up about 50% since Jan 2024, mainly from scrapers of Commons. Bots generated at least 65% of the most expensive (core datacenter) traffic but only about 35% of pageviews. — [The Register, 2025-04-03](https://www.theregister.com/2025/04/03/wikimedia_foundation_bemoans_bot_bandwidth/); [TechCrunch](https://techcrunch.com/2025/04/02/ai-crawlers-cause-wikimedia-commons-bandwidth-demands-to-surge-50)
- **Anubis**: an open-source proof-of-work reverse proxy by Xe Iaso, released Jan 2025. Reported adopters include GNOME, FFmpeg, Wine, FreeCAD, ScummVM, OpenWRT, and kernel infrastructure. — [Pinggy / CO/AI (secondary)](https://pinggy.io/blog/ai_crawlers_cost_more_cpu_than_real_traffic/)

### Inferences
- Crawler load does not show up in GitHub commit or PR history. little-helper can only proxy it, for example through infrastructure-related commits (robots.txt, Anubis config) or project-forge migrations.
- Projects self-hosting forges (GNOME, KDE, Fedora, FFmpeg, SourceHut users) bore the cost directly. GitHub-hosted projects mostly did not.

### Gaps
- No 2026 crawler-load figures were found for these projects.
- No primary GNOME or Xe Iaso post with the 97% figure was fetched. The figure comes via LibreNews quoting Piotrowski.
- The Anubis adopter list rests on secondary sources.

---

## 8. Maintainer funding and burnout surveys that mention AI

### Takeaway
The Tidelift 2024 survey is the main quantitative source. 45% of maintainers rated AI coding tools' impact negatively, and 64% were less willing to accept AI-assisted contributions. Funding responses in 2026 came mainly from AI firms via the Linux Foundation and OpenSSF.

### Cited Findings
- Tidelift 2024 State of the Open Source Maintainer (400+ respondents, fielded mid-2024, published Sep-Oct 2024):
  - Impact of AI coding tools on their work: 45% negative (23% extremely, 22% somewhat), 31% positive (22% somewhat, 9% extremely), 24% neutral.
  - Willingness to review and accept AI-assisted contributions: 64% less willing (37% much less), 9% more willing, 27% unsure.
  - Automated vulnerability-remediation PRs: 36% "not very useful," 10% not at all, 25% very, 8% extremely.
  - Code quality is the top concern, then maintenance burden. — [Tidelift via DEV, 2024-10-17](https://dev.to/tidelift/ai-based-coding-tools-are-thriving-and-maintainers-have-some-valid-concerns-about-the-impact-on-their-work-4ahf)
- AI tool use correlates strongly with maintainer age, with younger maintainers using it more. One respondent: "I don't want to become the gate for reviewing tons of automatically generated pull requests." — [The Register, 2024-09-18](https://www.theregister.com/2024/09/18/open_source_maintainers_underpaid/); [Tidelift](https://dev.to/tidelift/younger-open-source-maintainers-are-significantly-more-likely-to-use-ai-based-coding-tools-3cop)
- 2026-03-17: $12.5M from AI companies via LF, Alpha-Omega, and OpenSSF (see Section 2). Kroah-Hartman argued money alone won't fix it. GitHub's Secure Open Source Fund added $5.5M in Azure credits and funding. — [ITPro](https://www.itpro.com/software/open-source/big-tech-is-clamping-down-on-open-source-ai-slop-reports); [The Register](https://www.theregister.com/2026/03/18/linux_foundation_ai_slop_defense/)
- 2026-04-07: Anthropic donated $2.5M to Alpha-Omega and OpenSSF and $1.5M to the ASF. — [Anthropic Glasswing](https://www.anthropic.com/glasswing)
- 2026-10-01: Funding was announced for a full-time developer to handle security@kernel.org. — [LWN](https://lwn.net/SubscriberLink/1096908/c6356cdf7f44d632/)

### Inferences
- The 2024 Tidelift numbers predate the agent wave (Copilot agent, Claude Code, Codex in 2025). Sentiment in 2026 is likely more polarized, with GKH and Torvalds now positive on quality while small projects are overwhelmed. No 2025-2026 survey confirms this.

### Gaps
- No Tidelift 2025 or 2026 survey results on AI were found.
- No Linux Foundation Research or OpenSSF maintainer survey with AI-specific burnout numbers was found.
- No survey quantifies maintainer hours spent on AI-generated PRs or reports beyond curl's anecdotal per-report estimates.
