"""Visible AI markers on commits and change proposals.

Every marker is a lower bound: it records disclosure or tooling that left a trace,
not AI use. Disclosure norms differ by project and over time (the Linux kernel
required `Assisted-by:` from 2026-02 and dropped it in 2026-10), so markers feed
event studies with care, never raw prevalence claims.

Each rule: (marker_id, tool, field, regex). Fields:
  message  commit message or PR/issue body
  login    platform login of the author
  branch   PR head branch name
"""

from __future__ import annotations

import re

_TOOLS = (r"claude|anthropic|copilot|chatgpt|gpt-?[345]|openai|codex|gemini|bard|cursor|devin|aider|jules|"
          r"amazon q|codewhisperer|windsurf|codeium|cline|roo ?code|cody|tabnine|qwen|deepseek|llama|kiro|"
          r"opencode|goose|junie|amp ?code|warp")

# Trailer values name people as often as tools: curl has used "Assisted-by: <person>"
# since 2013, and git used it for people before AI tools. So trailers count only when
# the value names a tool or model, and "Claude" must look like the model (Claude Opus,
# Claude:claude-..., Claude <...@anthropic.com>), not a person such as Claude Paroz.
_CLAUDE_MODEL = (r"claude(?:[\s:_-]+(?:opus|sonnet|haiku|fable|code|instant|claude|\d)"
                 r"|\s*<[^>]*anthropic\.com>|\s*$)")
_TRAILER_TOOLS = (_CLAUDE_MODEL + r"|\b(?:opus|sonnet|haiku|fable)\s*\d|anthropic|copilot|chatgpt|gpt-?\d|openai|"
                  r"codex|gemini|grok|kimi|glm-?\d|qwen|deepseek|llama|mistral|codestral|cursor|devin|aider|jules|"
                  r"amazon q|codewhisperer|windsurf|codeium|cline|tabnine|kiro|junie|\bai\b|\bllm\b")

RULES: list[tuple[str, str | None, str, str]] = [
    ("trailer_assisted_by", None, "message", rf"(?im)^assisted-by:[^\n]*?({_TRAILER_TOOLS})[^\n]*$"),
    ("trailer_generated_by", None, "message", rf"(?im)^generated-by:[^\n]*?({_TRAILER_TOOLS})[^\n]*$"),
    ("trailer_ai_assisted", None, "message", r"(?im)^(ai-assisted|ai-generated|llm-assisted)(-by)?:\s*(.+)$"),
    ("trailer_coauthor_ai", None, "message", rf"(?im)^co-authored-by:[^\n<]*?({_TRAILER_TOOLS})[^\n]*$"),
    ("sig_claude_code", "claude", "message", r"(?i)generated with \[?claude code\]?|🤖 generated with"),
    ("sig_cursor", "cursor", "message", r"(?i)(made|created|generated|written) (with|by|using) cursor\b"),
    ("sig_copilot", "copilot", "message", r"(?i)(generated|written|created) (with|by|using) (github )?copilot"),
    ("sig_devin", "devin", "message", r"(?i)devin run:|link to devin run|requested by: .* devin"),
    ("sig_codex", "codex", "message", r"(?i)(generated|created|written) (with|by|using) (openai )?codex|chatgpt\.com/codex"),
    ("sig_aider", "aider", "message", r"(?m)^aider: "),
    ("sig_generic", None, "message",
     rf"(?i)\b(generated|written|drafted|authored|created) (with|by|using) (the help of )?(an? )?(ai|llm|{_TOOLS})\b"),
    ("bot_author", None, "login",
     r"(?i)^(copilot-swe-agent|copilot|devin-ai-integration|google-labs-jules|claude|cursor|cursoragent|"
     r"openai-codex|chatgpt-codex-connector|codegen-sh|sweep-ai|sweep|mentatbot|tembo-io|factory-droid|"
     r"amazon-q-developer|qodo-merge|coderabbitai|gemini-code-assist|sourcery-ai|ellipsis-dev|"
     r"copilot-pull-request-reviewer|cubic-dev-ai|greptile-apps|graphite-app)(\[bot\])?$"),
    ("branch_prefix", None, "branch", r"(?i)^(codex|copilot|claude|cursor|devin|jules|aider|sweep|codegen-bot)[/-]"),
]

# Model families and vendors -> one tool name.
_CANON = [(re.compile(r"(?i)claude|opus|sonnet|haiku|fable|anthropic"), "claude"),
          (re.compile(r"(?i)codex"), "codex"),
          (re.compile(r"(?i)chatgpt|gpt-?\d|openai"), "openai")]

_COMPILED = [(mid, tool, fld, re.compile(rx)) for mid, tool, fld, rx in RULES]
_TOOL_RE = re.compile(_TRAILER_TOOLS + "|" + _TOOLS, re.I)


def find(field: str, text: str | None) -> list[dict]:
    """Return markers found in one field value."""
    if not text:
        return []
    out = []
    for mid, tool, fld, rx in _COMPILED:
        if fld != field:
            continue
        m = rx.search(text)
        if not m:
            continue
        evidence = m.group(0)[:200]
        t = tool
        if t is None:
            tm = _TOOL_RE.search(evidence.split(":", 1)[-1])
            t = tm.group(0).strip().lower() if tm else None
            for rx_, name in _CANON:
                if t and rx_.search(t):
                    t = name
                    break
        out.append({"marker": mid, "tool": t, "evidence": evidence})
    return out
