"""GitHub GraphQL collection of pull requests and issues (regimes A and B).

Per repository, raw pages go to raw/github/github.com/<owner>/<repo>/<run_id>/:
  repo-NNNNN.jsonl.zst     repository facts and platform totals (for completeness checks)
  prs-NNNNN.jsonl.zst      PR pages, plus overflow pages for PRs whose reviews,
                           comments, commits, files, labels or timeline exceed the
                           first page of that connection
  issues-NNNNN.jsonl.zst   issue pages and their overflow pages

Each record keeps the query name and hash, variables, retrieval time, rate-limit cost
and the full response. Query texts are saved once per run in queries.json.

Modes, chosen per repo from its state file (state/github/<key>.json):
  full     first collection: CREATED_AT ascending, resumable from the last
           committed cursor after a crash or Ctrl-C
  refresh  after a complete full pass: everything updated since the last pass,
           with a safety margin (PRs: UPDATED_AT descending until older than the
           watermark; issues: the `since` filter)

Page size adapts: halve on server timeouts, grow back after a run of successes.
An item that still fails at page size 1 with reduced nested sizes is recorded as
"heavy" in the state file and skipped, so one pathological PR never stalls a repo.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from .. import config, ghapi, paths, store

SOURCE = "github"

ACTOR = "actor { login }"
_PR_TIMELINE_TYPES = ("HEAD_REF_FORCE_PUSHED_EVENT CLOSED_EVENT MERGED_EVENT REOPENED_EVENT READY_FOR_REVIEW_EVENT "
                      "CONVERT_TO_DRAFT_EVENT REVIEW_REQUESTED_EVENT CROSS_REFERENCED_EVENT LABELED_EVENT "
                      "UNLABELED_EVENT").split()
_ISSUE_TIMELINE_TYPES = ("CLOSED_EVENT REOPENED_EVENT CROSS_REFERENCED_EVENT CONNECTED_EVENT LABELED_EVENT "
                         "UNLABELED_EVENT MARKED_AS_DUPLICATE_EVENT TRANSFERRED_EVENT").split()
_SOURCE_REF = ("source { __typename ... on PullRequest { number repository { nameWithOwner } } "
               "... on Issue { number repository { nameWithOwner } } }")
_EVENT_FRAGMENTS = {
    "HeadRefForcePushedEvent": f"createdAt {ACTOR} beforeCommit {{ oid }} afterCommit {{ oid }}",
    "ClosedEvent": f"createdAt {ACTOR} stateReason closer {{ __typename ... on Commit {{ oid }} ... on PullRequest {{ number }} }}",
    "MergedEvent": f"createdAt {ACTOR} commit {{ oid }}",
    "ReopenedEvent": f"createdAt {ACTOR}",
    "ReadyForReviewEvent": f"createdAt {ACTOR}",
    "ConvertToDraftEvent": f"createdAt {ACTOR}",
    "ReviewRequestedEvent": (f"createdAt {ACTOR} requestedReviewer {{ __typename ... on User {{ login }} "
                             "... on Team { slug } ... on Bot { login } }"),
    "CrossReferencedEvent": f"createdAt willCloseTarget {_SOURCE_REF}",
    "LabeledEvent": f"createdAt {ACTOR} label {{ name }}",
    "UnlabeledEvent": f"createdAt {ACTOR} label {{ name }}",
    "ConnectedEvent": "createdAt subject { __typename ... on PullRequest { number } ... on Issue { number } }",
    "MarkedAsDuplicateEvent": "createdAt canonical { __typename ... on PullRequest { number } ... on Issue { number } }",
    "TransferredEvent": "createdAt fromRepository { nameWithOwner }",
}
_PR_EVENTS = ["HeadRefForcePushedEvent", "ClosedEvent", "MergedEvent", "ReopenedEvent", "ReadyForReviewEvent",
              "ConvertToDraftEvent", "ReviewRequestedEvent", "CrossReferencedEvent", "LabeledEvent", "UnlabeledEvent"]
_ISSUE_EVENTS = ["ClosedEvent", "ReopenedEvent", "CrossReferencedEvent", "LabeledEvent", "UnlabeledEvent",
                 "ConnectedEvent", "MarkedAsDuplicateEvent", "TransferredEvent"]


def _timeline_nodes(events: list[str]) -> str:
    frags = " ".join(f"... on {e} {{ {_EVENT_FRAGMENTS[e]} }}" for e in events)
    return f"nodes {{ __typename ... on Node {{ id }} {frags} }}"
WHO = "authorAssociation author { __typename login }"

# alias -> (field, first, node selection, extra arguments)
CONNECTIONS = {
    "prs": {
        "labels": ("labels", 20, "nodes { name }", ""),
        "reviews": ("reviews", 50, f"nodes {{ id state submittedAt {WHO} commit {{ oid }} body }}", ""),
        "comments": ("comments", 50, f"nodes {{ id createdAt {WHO} body }}", ""),
        "commits": ("commits", 100, "nodes { commit { oid authoredDate committedDate } }", ""),
        "files": ("files", 100, "nodes { path additions deletions changeType }", ""),
        "timeline": ("timelineItems", 50, _timeline_nodes(_PR_EVENTS), f", itemTypes: [{', '.join(_PR_TIMELINE_TYPES)}]"),
    },
    "issues": {
        "labels": ("labels", 20, "nodes { name }", ""),
        "comments": ("comments", 50, f"nodes {{ id createdAt {WHO} body }}", ""),
        "timeline": ("timelineItems", 30, _timeline_nodes(_ISSUE_EVENTS), f", itemTypes: [{', '.join(_ISSUE_TIMELINE_TYPES)}]"),
    },
}

PR_FIELDS = f"""id number title body state isDraft locked createdAt updatedAt closedAt mergedAt {WHO}
  mergedBy {{ __typename login }} mergeCommit {{ oid }} baseRefName headRefName headRefOid isCrossRepository
  headRepositoryOwner {{ login }} additions deletions changedFiles reviewDecision reviewThreads {{ totalCount }}"""
ISSUE_FIELDS = f"id number title body state stateReason locked createdAt updatedAt closedAt {WHO}"
PAGE_INFO = "totalCount pageInfo { hasNextPage endCursor }"
RATE = "rateLimit { cost remaining resetAt }"

REPO_QUERY = f"""query($owner: String!, $name: String!) {{
  repository(owner: $owner, name: $name) {{
    id nameWithOwner createdAt pushedAt isMirror isArchived isFork hasIssuesEnabled diskUsage
    defaultBranchRef {{ name }} licenseInfo {{ spdxId }}
    pullRequests {{ totalCount }} openPRs: pullRequests(states: OPEN) {{ totalCount }}
    mergedPRs: pullRequests(states: MERGED) {{ totalCount }} closedPRs: pullRequests(states: CLOSED) {{ totalCount }}
    issues {{ totalCount }} openIssues: issues(states: OPEN) {{ totalCount }}
  }}
  {RATE}
}}"""


def _connections(kind: str, scale: float) -> str:
    parts = []
    for alias, (field, n, nodes, extra) in CONNECTIONS[kind].items():
        first = max(1, int(n * scale))
        parts.append(f"{alias}: {field}(first: {first}{extra}) {{ {PAGE_INFO} {nodes} }}")
    return "\n    ".join(parts)


def page_query(kind: str, scale: float = 1.0) -> str:
    if kind == "prs":
        conn, fields, args = "pullRequests", PR_FIELDS, "orderBy: $order"
        params = "$order: IssueOrder!"
    else:
        conn, fields, args = "issues", ISSUE_FIELDS, "orderBy: $order, filterBy: $filter"
        params = "$order: IssueOrder!, $filter: IssueFilters"
    return f"""query($owner: String!, $name: String!, $n: Int!, $after: String, {params}) {{
  repository(owner: $owner, name: $name) {{
    page: {conn}(first: $n, after: $after, {args}) {{
      {PAGE_INFO}
      nodes {{ {fields}
    {_connections(kind, scale)}
      }}
    }}
  }}
  {RATE}
}}"""


def bare_query(kind: str) -> str:
    """Fetch only the next item's id and cursor, to step past a pathological item."""
    conn = "pullRequests" if kind == "prs" else "issues"
    filt = ", filterBy: $filter" if kind == "issues" else ""
    params = "$order: IssueOrder!" + (", $filter: IssueFilters" if kind == "issues" else "")
    return f"""query($owner: String!, $name: String!, $n: Int!, $after: String, {params}) {{
  repository(owner: $owner, name: $name) {{
    page: {conn}(first: $n, after: $after, orderBy: $order{filt}) {{ {PAGE_INFO} nodes {{ id number updatedAt }} }}
  }}
  {RATE}
}}"""


def overflow_query(kind: str, alias: str) -> str:
    field, _n, nodes, extra = CONNECTIONS[kind][alias]
    typ = "PullRequest" if kind == "prs" else "Issue"
    return f"""query($id: ID!, $n: Int!, $after: String) {{
  node(id: $id) {{ ... on {typ} {{ id conn: {field}(first: $n, after: $after{extra}) {{ {PAGE_INFO} {nodes} }} }} }}
  {RATE}
}}"""


def settings() -> dict:
    return config.study().get("github", {})


def _iso_minus(ts: str, hours: float) -> str:
    t = datetime.fromisoformat(ts.replace("Z", "+00:00")) - timedelta(hours=hours)
    return t.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class RepoCrawler:
    def __init__(self, api: ghapi.GraphQL, project: config.Project, repo: config.Repo, run_id: str,
                 manifest: store.Manifest, log=print):
        self.api, self.project, self.repo, self.run_id, self.manifest, self.log = api, project, repo, run_id, manifest, log
        self.owner, self.name = repo.github.split("/", 1)
        self.key = f"github.com/{repo.github}".lower()
        self.dir = paths.raw_dir(SOURCE, self.key, run_id)
        self.state_path = paths.state_dir(SOURCE, f"{self.key}.json")
        self.state = store.load_state(self.state_path)
        self.s = settings()
        self.queries: dict[str, str] = {}

    # -- helpers
    def _q(self, name: str, text: str) -> str:
        self.queries[name] = text
        return text

    def _record(self, kind: str, qname: str, query: str, variables: dict, meta: dict, body: dict, **extra) -> dict:
        return {"kind": kind, "repo": self.repo.github, "query": qname, "query_sha": ghapi.query_sha(query),
                "variables": variables, **meta, **extra, "response": body}

    def _save_state(self):
        self.state.update(repo=self.repo.github, project=self.project.id, updated_at=paths.utcnow())
        store.save_state(self.state_path, self.state)

    def finish(self):
        """Save the query texts used in this run, once per repository."""
        if self.queries and self.dir.exists():
            path = self.dir / "queries.json"
            store.atomic_write_json(path, {k: {"sha": ghapi.query_sha(v), "text": v} for k, v in self.queries.items()})
            self.manifest.add(path, kind="queries", repo=self.repo.github, project=self.project.id)

    # -- repository facts
    def repo_facts(self) -> dict:
        w = store.PageWriter(self.dir, "repo", self.manifest, repo=self.repo.github, project=self.project.id)
        q = self._q("repo", REPO_QUERY)
        v = {"owner": self.owner, "name": self.name}
        body, meta = self.api.execute(q, v)
        w.write(self._record("repo", "repo", q, v, meta, body))
        w.commit()
        self.facts = body["data"]["repository"]
        return self.facts

    # -- overflow
    def _overflow(self, kind: str, node: dict, writer: store.PageWriter):
        for alias in CONNECTIONS[kind]:
            c = node.get(alias)
            if not c or not c["pageInfo"]["hasNextPage"]:
                continue
            after, n = c["pageInfo"]["endCursor"], 100
            q = self._q(f"{kind}_overflow_{alias}", overflow_query(kind, alias))
            while True:
                v = {"id": node["id"], "n": n, "after": after}
                try:
                    body, meta = self.api.execute(q, v)
                except ghapi.HeavyQuery:
                    if n > 5:
                        n = max(5, n // 4)
                        continue
                    self.state.setdefault("heavy", []).append({"kind": kind, "id": node["id"], "connection": alias,
                                                               "after": after, "at": paths.utcnow()})
                    self.log(f"  [{self.repo.github}] gave up on {alias} overflow for {node.get('number')}")
                    break
                writer.write(self._record(f"{kind}_overflow", f"{kind}_overflow_{alias}", q, v, meta, body,
                                          parent=node["id"], connection=alias))
                cc = ((body.get("data") or {}).get("node") or {}).get("conn")
                if not cc or not cc["pageInfo"]["hasNextPage"]:
                    break
                after = cc["pageInfo"]["endCursor"]

    # -- pages
    def crawl(self, kind: str) -> dict:
        st = self.state.setdefault(kind, {})
        mode = "refresh" if st.get("complete") else "full"
        started = paths.utcnow()
        margin = float(self.s.get("refresh_margin_hours", 48))
        watermark = st.get("watermark")
        variables: dict = {"owner": self.owner, "name": self.name}
        if mode == "full":
            variables["order"] = {"field": "CREATED_AT", "direction": "ASC"}
            cursor = st.get("cursor")
        else:
            cursor = None
            if kind == "prs":
                variables["order"] = {"field": "UPDATED_AT", "direction": "DESC"}
            else:
                variables["order"] = {"field": "UPDATED_AT", "direction": "ASC"}
        if kind == "issues":
            variables["filter"] = {"since": _iso_minus(watermark, margin)} if mode == "refresh" and watermark else None

        max_n = int(self.s.get("pr_page_size" if kind == "prs" else "issue_page_size", 50 if kind == "prs" else 100))
        min_n = int(self.s.get("min_page_size", 5))
        chunk = int(self.s.get("chunk_pages", 50))
        n, scale, streak = max_n, 1.0, 0
        writer = store.PageWriter(self.dir, kind, self.manifest, repo=self.repo.github, project=self.project.id,
                                  mode=mode)
        pages = items = 0
        pages_before = st.get("pages_done", 0) if mode == "full" else 0
        items_before = st.get("items_done", 0) if mode == "full" else 0
        # Items and seconds of full passes, counted together across runs, for `lh status`.
        timed_before = (st.get("timed_items", 0), st.get("timed_seconds", 0.0)) if mode == "full" else (0, 0.0)
        facts = getattr(self, "facts", None) or {}
        st.update(mode=mode, run_started_at=started, run_items=0,
                  platform_total=(facts.get("pullRequests" if kind == "prs" else "issues") or {}).get("totalCount"))
        last_complete = cursor
        t0 = time.time()
        self.log(f"[github] {self.repo.github} {kind}: {mode} pass"
                 + (f" resuming after {st.get('pages_done', 0)} pages" if mode == "full" and cursor else "")
                 + (f" since {watermark}" if mode == "refresh" else ""))
        try:
            while True:
                q = self._q(f"{kind}_s{scale:g}", page_query(kind, scale))
                v = {**variables, "n": n, "after": last_complete}
                try:
                    body, meta = self.api.execute(q, v)
                except ghapi.HeavyQuery as e:
                    streak = 0
                    if n > min_n:
                        n = max(min_n, n // 2)
                    elif n > 1:
                        n = 1
                    elif scale > 0.2:
                        scale = 0.2
                    else:
                        last_complete = self._skip_heavy(kind, variables, last_complete, str(e), writer)
                        if last_complete is None:
                            break
                        n, scale = min_n, 1.0
                        continue
                    self.log(f"  [{self.repo.github}] {kind}: server timeout, page size -> {n}, nested x{scale:g}")
                    continue
                page = body["data"]["repository"]["page"]
                writer.write(self._record(kind, f"{kind}_s{scale:g}", q, v, meta, body, mode=mode))
                for node in page["nodes"]:
                    self._overflow(kind, node, writer)
                pages += 1
                items += len(page["nodes"])
                last_complete = page["pageInfo"]["endCursor"] or last_complete
                streak += 1
                if streak >= 5 and (n < max_n or scale < 1.0):
                    n, scale, streak = min(max_n, int(n * 1.5) + 1), 1.0, 0
                done = not page["pageInfo"]["hasNextPage"]
                if mode == "refresh" and kind == "prs" and watermark and page["nodes"]:
                    oldest = min(x["updatedAt"] for x in page["nodes"])
                    done = done or oldest < _iso_minus(watermark, margin)
                if writer.pending >= chunk or done:
                    writer.commit()
                    if mode == "full":
                        self._progress(st, last_complete, pages_before + pages, items_before + items,
                                       timed_before, items, time.time() - t0)
                    st["run_items"] = items
                    self._save_state()
                    rate = items / max(1.0, time.time() - t0) * 3600
                    self.log(f"  [{self.repo.github}] {kind}: {items:,} items in {pages} pages "
                             f"({rate:,.0f}/h; {self.api.remaining} points left)")
                if done:
                    break
        except BaseException:
            writer.commit()
            if mode == "full":
                self._progress(st, last_complete, pages_before + pages, items_before + items,
                               timed_before, items, time.time() - t0)
            st["run_items"] = items
            self._save_state()
            raise
        if mode == "full":
            st.update(complete=True, cursor=None, watermark=started, completed_at=paths.utcnow())
        else:
            st.update(watermark=started, refreshed_at=paths.utcnow())
        self._save_state()
        return {"kind": kind, "mode": mode, "pages": pages, "items": items, "seconds": round(time.time() - t0)}

    @staticmethod
    def _progress(st: dict, cursor, pages_done: int, items_done: int, timed_before: tuple, items: int,
                  seconds: float):
        st.update(cursor=cursor, pages_done=pages_done, items_done=items_done,
                  timed_items=timed_before[0] + items, timed_seconds=round(timed_before[1] + seconds, 1))

    def _skip_heavy(self, kind: str, variables: dict, after: str | None, err: str, writer) -> str | None:
        q = self._q(f"{kind}_bare", bare_query(kind))
        body, meta = self.api.execute(q, {**variables, "n": 1, "after": after})
        page = body["data"]["repository"]["page"]
        writer.write(self._record(f"{kind}_heavy", f"{kind}_bare", q, {**variables, "n": 1, "after": after}, meta, body))
        if not page["nodes"]:
            return None
        node = page["nodes"][0]
        self.state.setdefault("heavy", []).append({"kind": kind, "id": node["id"], "number": node["number"],
                                                   "error": err[:200], "at": paths.utcnow()})
        self.log(f"  [{self.repo.github}] {kind} #{node['number']} fails even alone; recorded as heavy and skipped")
        return page["pageInfo"]["endCursor"]


def run(projects: list[config.Project], *, only: str | None = None, log=print) -> list[dict]:
    run_id = paths.new_run_id()
    manifest = store.Manifest(SOURCE, run_id)
    api = ghapi.GraphQL(min_remaining=int(settings().get("min_remaining", 150)), log=log)
    results = []
    try:
        for p in projects:
            for r in p.repos:
                if not r.github:
                    continue
                kinds = [k for k, want in (("prs", p.wants("github_prs")), ("issues", p.wants("github_issues")))
                         if want and (only is None or only == k)]
                if not kinds:
                    continue
                crawler = RepoCrawler(api, p, r, run_id, manifest, log=log)
                try:
                    facts = crawler.repo_facts()
                    for k in kinds:
                        out = crawler.crawl(k)
                        total = facts["pullRequests" if k == "prs" else "issues"]["totalCount"]
                        results.append({"project": p.id, "repo": r.github, "status": "ok",
                                        "platform_total": total, **out})
                except ghapi.NotFound as e:
                    log(f"[github] {r.github}: not found ({e})")
                    results.append({"project": p.id, "repo": r.github, "status": "not found"})
                except ghapi.GitHubError as e:
                    # Committed pages and the cursor are saved; a re-run resumes this repo.
                    log(f"[github] {r.github}: FAILED, will resume on the next run: {e}")
                    results.append({"project": p.id, "repo": r.github, "status": "failed", "error": str(e)[:300]})
                finally:
                    crawler.finish()
    finally:
        log(f"[github] run {run_id}: {api.requests} requests, {api.points_used} points")
        api.close()
    return results
