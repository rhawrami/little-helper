"""GitHub collector and normalizer against a fake GraphQL server."""

import json

import httpx
import polars as pl
import pytest

from little_helper import config, ghapi, paths, store
from little_helper.collect import github as ghc
from little_helper.normalize import github as ghn

RATE = {"cost": 1, "remaining": 4000, "resetAt": "2030-01-01T00:00:00Z"}


def conn(nodes, has_next=False, total=None):
    return {"totalCount": total if total is not None else len(nodes),
            "pageInfo": {"hasNextPage": has_next, "endCursor": "more" if has_next else None}, "nodes": nodes}


def pr(i, updated="2024-01-05T00:00:00Z", title=None):
    return {
        "id": f"PR{i}", "number": i, "title": title or f"t{i}",
        "body": "🤖 Generated with [Claude Code]" if i == 2 else "plain body", "state": "MERGED", "isDraft": False,
        "locked": False, "createdAt": f"2024-01-0{1 + i % 8}T00:00:00Z", "updatedAt": updated,
        "closedAt": "2024-01-09T00:00:00Z", "mergedAt": "2024-01-09T00:00:00Z", "authorAssociation": "MEMBER",
        "author": {"__typename": "User", "login": f"user{i}"}, "mergedBy": {"__typename": "User", "login": "m"},
        "mergeCommit": {"oid": f"m{i}"}, "baseRefName": "main", "headRefName": "codex/fix" if i == 3 else "f",
        "headRefOid": "h", "isCrossRepository": True, "headRepositoryOwner": {"login": "u"}, "additions": 3,
        "deletions": 1, "changedFiles": 1, "reviewDecision": "APPROVED", "reviewThreads": {"totalCount": 2},
        "labels": conn([{"name": "bug"}]),
        "reviews": conn([{"id": f"R{i}a", "state": "APPROVED", "submittedAt": "2024-01-08T00:00:00Z",
                          "authorAssociation": "MEMBER", "author": {"__typename": "User", "login": "rev"},
                          "commit": {"oid": "h"}, "body": "lgtm"}], has_next=(i == 1), total=2 if i == 1 else 1),
        "comments": conn([{"id": f"C{i}", "createdAt": "2024-01-07T00:00:00Z", "authorAssociation": "NONE",
                           "author": {"__typename": "Bot", "login": "coderabbitai"}, "body": "review"}]),
        "commits": conn([{"commit": {"oid": f"c{i}", "authoredDate": "2024-01-02T00:00:00Z",
                                     "committedDate": "2024-01-02T00:00:00Z"}}]),
        "files": conn([{"path": "tests/test_x.py", "additions": 3, "deletions": 1, "changeType": "MODIFIED"}]),
        "timeline": conn([{"__typename": "MergedEvent", "id": f"E{i}", "createdAt": "2024-01-09T00:00:00Z",
                           "actor": {"login": "m"}, "commit": {"oid": f"m{i}"}}]),
    }


class FakeGitHub:
    def __init__(self, prs, fail_first_page=False, break_after_pages=None):
        self.prs, self.fail_first_page, self.break_after_pages = prs, fail_first_page, break_after_pages
        self.page_calls = 0
        self.sizes = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        q, v = body["query"], body["variables"]
        if "node(id: $id)" in q:
            extra = [{"id": "R1b", "state": "COMMENTED", "submittedAt": "2024-01-08T01:00:00Z",
                      "authorAssociation": "NONE", "author": {"__typename": "User", "login": "rev2"},
                      "commit": {"oid": "h"}, "body": "nit"}]
            return httpx.Response(200, json={"data": {"node": {"id": v["id"], "conn": conn(extra, total=2)}},
                                             "rateLimit": RATE})
        if "page: pullRequests" in q:
            self.page_calls += 1
            if self.fail_first_page and self.page_calls == 1:
                return httpx.Response(502)
            if self.break_after_pages is not None and self.page_calls > self.break_after_pages:
                return httpx.Response(401)
            self.sizes.append(v["n"])
            start = int(v["after"] or 0)
            items = self.prs[start:start + v["n"]]
            end = start + len(items)
            page = {"totalCount": len(self.prs), "pageInfo": {"hasNextPage": end < len(self.prs), "endCursor": str(end)},
                    "nodes": items}
            return httpx.Response(200, json={"data": {"repository": {"page": page}, "rateLimit": RATE}})
        if "nameWithOwner createdAt pushedAt" in q:
            repo = {"id": "REPO", "nameWithOwner": "o/r", "createdAt": "2015-01-01T00:00:00Z", "pushedAt": None,
                    "isMirror": False, "isArchived": False, "isFork": False, "hasIssuesEnabled": True,
                    "diskUsage": 100, "defaultBranchRef": {"name": "main"}, "licenseInfo": None,
                    "pullRequests": {"totalCount": len(self.prs)}, "openPRs": {"totalCount": 0},
                    "mergedPRs": {"totalCount": len(self.prs)}, "closedPRs": {"totalCount": 0},
                    "issues": {"totalCount": 0}, "openIssues": {"totalCount": 0}}
            return httpx.Response(200, json={"data": {"repository": repo, "rateLimit": RATE}})
        raise AssertionError(f"unexpected query: {q[:80]}")


@pytest.fixture
def setup(lh_env):
    repo = config.Repo(key="github.com/o/r", clone_urls=[], github="o/r")
    project = config.Project(id="demo", name="Demo", regime="A", repos=[repo],
                             collect={"github_prs": True, "github_issues": False})
    return project, repo


def crawl(project, repo, fake, run_id):
    api = ghapi.GraphQL("test-token", transport=httpx.MockTransport(fake), sleep=lambda s: None, log=lambda m: None)
    c = ghc.RepoCrawler(api, project, repo, run_id, store.Manifest("github", run_id), log=lambda m: None)
    try:
        c.repo_facts()
        return c.crawl("prs")
    finally:
        c.finish()


def test_full_pass_with_timeout_and_overflow(setup):
    project, repo = setup
    fake = FakeGitHub([pr(i) for i in range(1, 6)], fail_first_page=True)
    out = crawl(project, repo, fake, "20260101T000000Z")
    assert out["mode"] == "full" and out["items"] == 5
    # macOS writes AppleDouble "._" files next to data on FAT/exFAT drives; they must be ignored.
    (paths.raw_dir("github", "github.com/o/r", "20260101T000000Z") / "._prs-00001.jsonl.zst").write_bytes(b"\x00\x05junk")
    assert fake.sizes[0] < 25  # page size shrank after the 502
    st = store.load_state(paths.state_dir("github", "github.com/o/r.json"))
    assert st["prs"]["complete"] and st["prs"]["watermark"]
    t = ghn.normalize_repo(project, repo)
    cps = t["change_proposals"]
    assert cps.height == 5 and cps["labels"].to_list()[0] == ["bug"]
    reviews = t["cp_reviews"]
    assert sorted(reviews.filter(pl.col("parent_id") == "PR1")["id"]) == ["R1a", "R1b"]  # overflow merged
    assert t["cp_files"]["is_test"].all()
    markers = {(r["object"], r["marker"]) for r in t["gh_ai_markers"].iter_rows(named=True)}
    assert {("pr_body", "sig_claude_code"), ("pr_branch", "branch_prefix"), ("comment_author", "bot_author")} <= markers
    assert t["gh_repo_facts"]["pullRequests"].item() == 5
    assert (paths.raw_dir("github", "github.com/o/r", "20260101T000000Z") / "queries.json").exists()


def test_resume_after_crash_then_refresh(setup, monkeypatch):
    project, repo = setup
    s = dict(ghc.settings(), pr_page_size=5, chunk_pages=1)
    monkeypatch.setattr(ghc, "settings", lambda: s)
    prs = [pr(i) for i in range(1, 31)]
    with pytest.raises(ghapi.GitHubError):
        crawl(project, repo, FakeGitHub(prs, break_after_pages=2), "20260101T000000Z")
    st = store.load_state(paths.state_dir("github", "github.com/o/r.json"))
    assert st["prs"]["cursor"] == "10" and not st["prs"].get("complete")

    fake = FakeGitHub(prs)
    out = crawl(project, repo, fake, "20260101T000100Z")
    assert out["mode"] == "full" and out["items"] == 20  # resumed after the 10 committed PRs
    assert ghn.normalize_repo(project, repo)["change_proposals"].height == 30

    prs[1] = pr(2, updated="2030-01-01T00:00:00Z", title="t2 edited")
    out = crawl(project, repo, FakeGitHub([prs[1]] + prs[:1] + prs[2:]), "20260101T000200Z")
    assert out["mode"] == "refresh" and out["pages"] == 1  # stopped at items older than the watermark
    t = ghn.normalize_repo(project, repo)
    cps = t["change_proposals"]
    assert cps.height == 30 and cps.filter(pl.col("id") == "PR2")["title"].item() == "t2 edited"
    assert t["cp_reviews"].filter(pl.col("parent_id") == "PR1").height == 2  # no duplicates across runs


def _api(responses: list[httpx.Response]):
    calls = []

    def handler(request):
        calls.append(request)
        return responses.pop(0)
    api = ghapi.GraphQL("test-token", transport=httpx.MockTransport(handler), sleep=lambda s: None, log=lambda m: None)
    return api, calls


OK = {"data": {"repository": {"id": "R"}, "rateLimit": RATE}}


@pytest.mark.parametrize("bad", [
    httpx.Response(200, content=b""),  # empty body
    httpx.Response(200, content=json.dumps(OK).encode()[:30]),  # truncated body
    httpx.Response(499, content=b""),
])
def test_cut_off_responses_are_retried(bad):
    api, calls = _api([bad, httpx.Response(200, json=OK)])
    body, _ = api.execute("query { x }", {})
    assert body == OK and len(calls) == 2


def test_repeated_cut_offs_shrink_the_page():
    api, calls = _api([httpx.Response(200, content=b"") for _ in range(3)])
    with pytest.raises(ghapi.HeavyQuery, match="cut off 3 times"):
        api.execute("query { x }", {})
    assert len(calls) == 3


def test_unexpected_status_is_a_github_error_not_a_crash():
    api, _ = _api([httpx.Response(418, content=b"teapot")])
    with pytest.raises(ghapi.GitHubError, match="HTTP 418"):
        api.execute("query { x }", {})
