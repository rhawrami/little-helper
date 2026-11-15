"""Heuristic bot detection for git identities and platform logins.

GitHub reports `__typename: Bot` for app accounts; that is authoritative when present.
Everything else here is a pattern list: a lower bound that will miss some bots, and
it is kept small and explicit so it can be audited.
"""

from __future__ import annotations

import re

KNOWN_BOT_LOGINS = {
    "dependabot", "dependabot-preview", "renovate", "renovate-bot", "github-actions", "pre-commit-ci",
    "codecov", "codecov-commenter", "allcontributors", "mergify", "k8s-ci-robot", "k8s-triage-robot",
    "pytorchmergebot", "pytorchbot", "facebook-github-bot", "copybara-service", "google-oss-bot",
    "bors", "bors-servo", "rust-highfive", "rustbot", "rust-timer", "netlify", "vercel", "sonarcloud",
    "stale", "greenkeeper", "snyk-bot", "pyup-bot", "imgbot", "azure-pipelines", "gitter-badger",
    "elasticmachine", "kibanamachine", "nodejs-github-bot", "openjdk-notifier", "bridgekeeper",
    "gopherbot", "googlebot", "homu", "llvmbot", "github-merge-queue",
}

_LOGIN_RE = re.compile(r"(\[bot\]$|-bot$|^bot-|bot$)", re.I)
_EMAIL_RE = re.compile(
    r"(\[bot\]@|^(noreply|no-reply|bot|bots|ci|buildbot|autobuild|jenkins|travis)@|"
    r"dependabot|renovate|github-actions|actions@github\.com|copybara|bors@|bot@)", re.I)
_NAME_RE = re.compile(r"(\[bot\]$|^(dependabot|renovate|github-actions|copybara|bors|buildbot|"
                      r"pytorchmergebot|facebook github bot|gopherbot|llvmbot)\b)", re.I)


def is_bot_login(login: str | None, typename: str | None = None) -> bool:
    if typename == "Bot":
        return True
    if not login:
        return False
    low = login.lower()
    return low.removesuffix("[bot]") in KNOWN_BOT_LOGINS or bool(_LOGIN_RE.search(low))


def is_bot_identity(name: str | None, email: str | None) -> bool:
    return bool((email and _EMAIL_RE.search(email)) or (name and _NAME_RE.search(name)))


# Regex strings for vectorised use in polars.
EMAIL_PATTERN = _EMAIL_RE.pattern
NAME_PATTERN = _NAME_RE.pattern
