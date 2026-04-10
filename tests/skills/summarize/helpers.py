"""Summarize-specific test helpers. Parse the structured template output."""

import re

REQUIRED_SECTIONS = ["## TL;DR", "## Cliff Notes", "## Share", "## Comment"]


def starts_with_h1(text: str) -> bool:
    """Check that the output starts with '# ' (no preamble)."""
    return text.startswith("# ")


def h1_title(text: str) -> str | None:
    """Extract the H1 title text (everything after '# ' on the first line)."""
    match = re.match(r"^# (.+)", text)
    return match.group(1).strip() if match else None


def has_all_sections(text: str) -> list[str]:
    """Return list of required section headings missing from text. Empty = pass."""
    return [section for section in REQUIRED_SECTIONS if section not in text]


def _extract_section(text: str, heading: str, next_headings: list[str]) -> str | None:
    """Extract text between a heading and the next heading (or end of string)."""
    pattern = re.escape(heading) + r"\s*\n(.*?)(?="
    if next_headings:
        pattern += "|".join(re.escape(h) for h in next_headings) + r"|"
    pattern += r"\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    return match.group(1).strip()


def tldr_text(text: str) -> str | None:
    """Extract the TL;DR paragraph text."""
    return _extract_section(text, "## TL;DR", ["## Cliff Notes", "## Share", "## Comment"])


def cliff_notes_bullets(text: str) -> list[str]:
    """Extract Cliff Notes bullets as a list of strings."""
    section = _extract_section(text, "## Cliff Notes", ["## Share", "## Comment"])
    if not section:
        return []
    return [line.strip() for line in section.splitlines() if re.match(r"^\s*-\s", line)]


def share_text(text: str) -> str | None:
    """Extract the content inside the Share code fence."""
    section = _extract_section(text, "## Share", ["## Comment"])
    if not section:
        return None
    fence_match = re.search(r"```\s*\n(.*?)\n\s*```", section, re.DOTALL)
    return fence_match.group(1).strip() if fence_match else None


def comment_text(text: str) -> str | None:
    """Extract the content inside the Comment code fence."""
    section = _extract_section(text, "## Comment", [])
    if not section:
        return None
    fence_match = re.search(r"```\s*\n(.*?)\n\s*```", section, re.DOTALL)
    return fence_match.group(1).strip() if fence_match else None


def word_count(text: str) -> int:
    """Return total word count."""
    return len(text.split()) if text else 0
