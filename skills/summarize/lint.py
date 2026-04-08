#!/usr/bin/env python3
"""Deterministic self-check for summarize outputs.

Usage:
    python skills/summarize/lint.py <path-to-draft.md>

Exit 0 = clean. Exit 1 = findings (one per line on stdout as "FAIL: <rule>: <evidence>").
No dependencies beyond the stdlib.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Phrases that indicate the agent leaked its internal monologue into the final output.
# Tight allowlist: we want to catch the known leak patterns, not reject legitimate prose.
NARRATION_PREFIXES = (
    "Let me",
    "Now I",
    "I'll draft",
    "I have the",
    "Here's the summary",
)
NARRATION_SCAN_CHARS = 200


def _lines(text: str) -> list[str]:
    return text.splitlines()


def check_title(text: str) -> str | None:
    """First non-empty line must look like a title."""
    for i, line in enumerate(_lines(text)):
        stripped = line.strip()
        if not stripped:
            continue
        # H1 markdown heading
        if stripped.startswith("# "):
            return None
        # Bold-wrapped line
        if stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
            return None
        # Short line followed by a blank line, not ending in a period
        if len(stripped) <= 120 and not stripped.endswith("."):
            next_line = _lines(text)[i + 1] if i + 1 < len(_lines(text)) else ""
            if not next_line.strip():
                return None
        return f"first non-empty line is not a title: {stripped[:80]!r}"
    return "output is empty"


def check_summary_paragraph(text: str) -> str | None:
    """Between the title and the first bullet list, there must be a non-list paragraph."""
    lines = _lines(text)
    # Find end of title block (first non-empty line, maybe preceded by blank lines)
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines):
        return "no title found"
    i += 1  # skip the title line itself

    paragraph_chars: list[str] = []
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            if paragraph_chars:
                # Found a paragraph, good enough
                break
            i += 1
            continue
        # A bullet or heading before we found a paragraph = missing summary
        if stripped.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+\.\s", stripped):
            return "no summary paragraph between title and first list"
        if stripped.startswith("#"):
            # Another heading (e.g. ## TL;DR) is acceptable — look inside it for prose
            i += 1
            continue
        paragraph_chars.append(stripped)
        i += 1

    if not paragraph_chars:
        return "no summary paragraph between title and first list"
    return None


def check_bullet_count(text: str, lo: int = 5, hi: int = 8) -> str | None:
    """There must be a contiguous bulleted list somewhere with lo..hi items."""
    lines = _lines(text)
    runs: list[int] = []
    current = 0
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(("- ", "* ", "+ ")):
            current += 1
        else:
            if current:
                runs.append(current)
            current = 0
    if current:
        runs.append(current)
    if not runs:
        return f"no bulleted list found (expected {lo}-{hi} items)"
    if any(lo <= r <= hi for r in runs):
        return None
    return f"no bulleted list with {lo}-{hi} items (found runs: {runs})"


def check_share_block(text: str) -> str | None:
    """Output must contain a Share block: heading, code fence, blockquote, or labeled."""
    # Accept "## Share", "**Share**", "SHARE", "Share:" etc.
    if re.search(r"(?im)^\s*(?:#+\s*share\b|\*\*share\*\*|share\s*:|SHARE)\s*$", text):
        return None
    if re.search(r"(?im)^\s*(?:#+\s*share\b|\*\*share\*\*|share\s*:|SHARE)", text):
        return None
    return "no Share block found"


def check_comment_block(text: str) -> str | None:
    """Output must contain a Comment block distinct from Share, with body <=20 words."""
    # Locate a comment label
    match = re.search(
        r"(?im)^\s*(?:#+\s*comment\b|\*\*comment\*\*|comment\s*:|COMMENT)\s*$",
        text,
    )
    if not match:
        match = re.search(
            r"(?im)^\s*(?:#+\s*comment\b|\*\*comment\*\*|comment\s*:|COMMENT)",
            text,
        )
    if not match:
        return "no Comment block found"

    # Extract body: everything after the label, strip code fences, stop at next heading or EOF
    after = text[match.end():]
    body_lines: list[str] = []
    for line in after.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        if stripped.startswith("#"):
            break
        body_lines.append(stripped)
    body = " ".join(s for s in body_lines if s).strip()
    if not body:
        return "Comment block is empty"
    word_count = len(body.split())
    if word_count > 20:
        return f"Comment block is {word_count} words (max 20)"
    return None


def check_no_em_dash(text: str) -> str | None:
    if "—" in text:
        idx = text.index("—")
        ctx = text[max(0, idx - 20) : idx + 20].replace("\n", " ")
        return f"em dash found: ...{ctx}..."
    return None


def check_no_narration_prefix(text: str) -> str | None:
    head = text[:NARRATION_SCAN_CHARS]
    for phrase in NARRATION_PREFIXES:
        if phrase in head:
            return f"agent narration leaked into output: {phrase!r} found in first {NARRATION_SCAN_CHARS} chars"
    return None


CHECKS: list[tuple[str, callable]] = [
    ("title", check_title),
    ("summary_paragraph", check_summary_paragraph),
    ("bullet_count", check_bullet_count),
    ("share_block", check_share_block),
    ("comment_block", check_comment_block),
    ("no_em_dash", check_no_em_dash),
    ("no_narration_prefix", check_no_narration_prefix),
]


def lint(text: str) -> list[str]:
    findings: list[str] = []
    for name, fn in CHECKS:
        result = fn(text)
        if result:
            findings.append(f"FAIL: {name}: {result}")
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python skills/summarize/lint.py <path>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.exists():
        print(f"FAIL: file not found: {path}")
        return 1
    text = path.read_text()
    findings = lint(text)
    for f in findings:
        print(f)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
