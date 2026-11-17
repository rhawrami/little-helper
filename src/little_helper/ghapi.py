"""Minimal GitHub GraphQL client: one token, polite pacing, typed failures.

Pacing rules:
- Every query asks for rateLimit { cost remaining resetAt }; when remaining drops
  below `min_remaining`, sleep until the reset.
- Secondary rate limits (403/429 with retry-after) sleep as instructed.
- Timeouts and 502/504 raise HeavyQuery so the caller can shrink the page.
- A response cut off in transit (an empty or truncated body, or HTTP 499) is retried
  as is twice, then raised as HeavyQuery: on 2026-11-16 these came in bursts on the
  largest pages and crashed the run ten times in seven hours.
- Any other unexpected status raises GitHubError, which the collector catches per
  repository, so one bad response never ends the whole run.
- One request at a time. GitHub's terms forbid spreading load over several accounts.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from . import paths

ENDPOINT = "https://api.github.com/graphql"
USER_AGENT = "oss-research-client/0.1"


class GitHubError(RuntimeError):
    pass


class HeavyQuery(GitHubError):
    """The query timed out server-side; retry with a smaller page."""


class NotFound(GitHubError):
    pass


def token() -> str:
    """GITHUB_TOKEN or GH_TOKEN, else a token file (LH_GITHUB_TOKEN_FILE or github_token_file
    in config/local.yaml, the setup on the droplet), else the gh CLI login."""
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    file = paths._setting("LH_GITHUB_TOKEN_FILE", "github_token_file")
    if file:
        path = Path(file).expanduser()
        if not path.exists() or not path.read_text().strip():
            raise GitHubError(f"the GitHub token file {path} is missing or empty")
        if path.stat().st_mode & 0o077:
            raise GitHubError(f"the GitHub token file {path} is readable by others: chmod 600 {path}")
        return path.read_text().strip()
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=20)
    except FileNotFoundError as e:
        raise GitHubError("set GITHUB_TOKEN or install and log in to the gh CLI") from e
    if out.returncode != 0 or not out.stdout.strip():
        raise GitHubError("no GitHub token: set GITHUB_TOKEN or run `gh auth login`")
    return out.stdout.strip()


def query_sha(query: str) -> str:
    return hashlib.sha256(query.encode()).hexdigest()[:16]


_HEAVY_MARKERS = ("timeout", "timed out", "something went wrong", "loading", "try again")


class GraphQL:
    def __init__(self, tok: str | None = None, *, min_remaining: int = 150, timeout: float = 60.0,
                 transport: httpx.BaseTransport | None = None, sleep=time.sleep, log=print):
        self.client = httpx.Client(
            headers={"Authorization": f"bearer {tok or token()}", "User-Agent": USER_AGENT},
            timeout=httpx.Timeout(timeout), transport=transport,
        )
        self.min_remaining, self.sleep, self.log = min_remaining, sleep, log
        self.remaining: int | None = None
        self.reset_at: str | None = None
        self.points_used = 0
        self.requests = 0

    def close(self):
        self.client.close()

    def _wait_until(self, reset_at: str, why: str):
        reset = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
        wait = max(5.0, (reset - datetime.now(timezone.utc)).total_seconds() + 5)
        self.log(f"  {why}; sleeping {wait:.0f}s until {reset_at}")
        self.sleep(wait)

    def _backoff(self, attempt: int, why: str):
        wait = min(300, 15 * 2 ** attempt)  # 15 s doubling to 5 min: rides out ~40 min of outage
        self.log(f"  {why}; retry {attempt + 1} in {wait}s")
        self.sleep(wait)

    def execute(self, query: str, variables: dict, *, tries: int = 12, cutoff_retries: int = 2) -> tuple[dict, dict]:
        """Run a query. Returns (response_json, meta). Raises HeavyQuery or NotFound."""
        cutoffs = 0

        def cut_off(attempt: int, why: str):
            nonlocal cutoffs
            cutoffs += 1
            if cutoffs > cutoff_retries:
                raise HeavyQuery(f"response cut off {cutoffs} times: {why}")
            self._backoff(attempt, f"response cut off ({why})")

        for attempt in range(tries):
            started = paths.utcnow()
            try:
                r = self.client.post(ENDPOINT, json={"query": query, "variables": variables})
            except httpx.TimeoutException as e:
                raise HeavyQuery(f"client timeout: {e!r}") from e
            except httpx.TransportError as e:  # network down, laptop asleep, DNS
                self._backoff(attempt, f"network error {type(e).__name__}")
                continue
            self.requests += 1
            if r.status_code in (502, 504):
                raise HeavyQuery(f"HTTP {r.status_code}")
            if r.status_code in (403, 429):
                retry_after = r.headers.get("retry-after")
                if r.headers.get("x-ratelimit-remaining") == "0" and r.headers.get("x-ratelimit-reset"):
                    reset = datetime.fromtimestamp(int(r.headers["x-ratelimit-reset"]), timezone.utc)
                    self._wait_until(reset.isoformat(), "primary rate limit exhausted")
                else:
                    wait = int(retry_after) if retry_after else 60 * (attempt + 1)
                    self.log(f"  secondary rate limit (HTTP {r.status_code}); sleeping {wait}s")
                    self.sleep(wait)
                continue
            if r.status_code == 401:
                raise GitHubError("GitHub rejected the token (HTTP 401)")
            if r.status_code == 499:
                cut_off(attempt, "HTTP 499")
                continue
            if r.status_code >= 500:
                self._backoff(attempt, f"HTTP {r.status_code}")
                continue
            if r.status_code >= 400:
                raise GitHubError(f"HTTP {r.status_code}: {r.text[:300]}")
            try:
                body = r.json()
            except ValueError as e:  # empty or truncated body
                cut_off(attempt, f"{len(r.content):,} bytes, {e}")
                continue
            if not isinstance(body, dict):
                cut_off(attempt, f"unexpected JSON {type(body).__name__}")
                continue
            errors = body.get("errors") or []
            types = {e.get("type") for e in errors}
            if "RATE_LIMITED" in types:
                rl = ((body.get("data") or {}).get("rateLimit") or {})
                self._wait_until(rl.get("resetAt") or paths.utcnow(), "GraphQL RATE_LIMITED")
                continue
            if "NOT_FOUND" in types and not (body.get("data") or {}).get("repository"):
                raise NotFound("; ".join(e.get("message", "") for e in errors))
            if errors and not body.get("data"):
                msg = "; ".join(e.get("message", "") for e in errors)
                if any(m in msg.lower() for m in _HEAVY_MARKERS):
                    raise HeavyQuery(msg)
                raise GitHubError(msg)
            if errors and any(m in "; ".join(e.get("message", "") for e in errors).lower() for m in _HEAVY_MARKERS):
                raise HeavyQuery("; ".join(e.get("message", "") for e in errors))
            rl = (body.get("data") or {}).get("rateLimit") or {}
            if rl:
                self.points_used += rl.get("cost") or 0
                self.remaining, self.reset_at = rl.get("remaining"), rl.get("resetAt")
            meta = {"retrieved_at": started, "status": r.status_code, "cost": rl.get("cost"),
                    "remaining": rl.get("remaining")}
            if self.remaining is not None and self.remaining < self.min_remaining and self.reset_at:
                self._wait_until(self.reset_at, f"{self.remaining} points left")
            return body, meta
        raise GitHubError(f"gave up after {tries} tries")
