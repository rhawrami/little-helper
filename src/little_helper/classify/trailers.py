"""Parse git trailers (Signed-off-by:, Reviewed-by:, PR-URL:, ...) from commit messages.

Follows git's rule closely enough for research use: trailers live in the last
paragraph of the message, and that paragraph counts as a trailer block when at
least half of its lines look like `Key: value` (git requires 25% plus a known key;
we are stricter to avoid treating prose such as "Note: ..." as trailers).
Continuation lines that start with whitespace extend the previous value.
"""

from __future__ import annotations

import re

_TRAILER = re.compile(r"^([A-Za-z0-9][A-Za-z0-9-]{0,62})\s*:\s+(.+?)\s*$")
_KNOWN = {
    "signed-off-by", "reviewed-by", "acked-by", "tested-by", "reported-by", "suggested-by", "co-authored-by",
    "co-developed-by", "assisted-by", "generated-by", "helped-by", "cc", "fixes", "closes", "link", "pr-url",
    "pull-request", "change-id", "reviewed-on", "bug", "differential revision", "approved-by", "merged-from",
    "cherry-picked-from", "backport-pr-url", "refs", "see-also", "message-id",
}


def parse(message: str | None) -> list[tuple[str, str]]:
    """Return [(key_lowercase, value), ...] from the message's trailer block."""
    if not message:
        return []
    paras = re.split(r"\n\s*\n", message.strip())
    if len(paras) < 2:
        return []  # a one-paragraph message is a subject, not trailers
    block = paras[-1].splitlines()
    items: list[list[str]] = []
    matched = 0
    lines = 0
    for line in block:
        if not line.strip():
            continue
        if line[:1].isspace() and items:
            items[-1][1] += " " + line.strip()
            continue
        lines += 1
        m = _TRAILER.match(line)
        if m:
            matched += 1
            items.append([m.group(1).lower(), m.group(2)])
    if not items or matched * 2 < lines:
        # Commit-message prose such as "Note: ..." is not a trailer block unless the key is known.
        if not (items and all(k in _KNOWN for k, _ in items) and matched * 4 >= lines):
            return []
    return [(k, v) for k, v in items]
