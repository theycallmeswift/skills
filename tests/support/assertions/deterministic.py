"""Deterministic assertion helpers for skill output validation.

Each function returns a list of violations (empty = pass) or a scalar value.
"""

import re

BANNED_PHRASES = [
    "synergy",
    "leverage",
    "ecosystem",
    "paradigm shift",
    "game-changer",
    "delve",
    "excited to share",
]


def no_em_dashes(text: str) -> list[str]:
    """Return lines containing em dashes. Empty list = pass."""
    return [line for line in text.splitlines() if "\u2014" in line]


def long_sentences(text: str, max_words: int = 25) -> list[str]:
    """Return sentences exceeding max_words. Empty list = pass."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.split()) > max_words]


def banned_words(text: str) -> list[str]:
    """Return banned words/phrases found in text. Empty list = pass."""
    lower = text.lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in lower]


def urls_preserved(source: str, output: str) -> list[str]:
    """Return URLs from source missing in output. Empty list = pass."""
    url_pattern = re.compile(r"https?://[^\s)\]>,]+")
    source_urls = set(url_pattern.findall(source))
    return [url for url in source_urls if url not in output]


def stats_preserved(source: str, output: str) -> list[str]:
    """Return numbers/stats from source missing in output. Empty list = pass.

    Accepts common abbreviations (e.g. 500K for 500,000).
    """
    stat_pattern = re.compile(r"\d[\d,]*(?:\.\d+)?")
    source_stats = set(stat_pattern.findall(source))
    output_lower = output.lower()
    missing = []
    for stat in source_stats:
        if stat in output:
            continue
        raw = stat.replace(",", "")
        if len(raw) >= 4 and _abbreviated_form(raw) in output_lower:
            continue
        missing.append(stat)
    return missing


def _abbreviated_form(raw_digits: str) -> str:
    """Convert a raw digit string to its abbreviated form (e.g. '500000' -> '500k')."""
    n = int(raw_digits)
    for threshold, suffix in [(1_000_000_000, "b"), (1_000_000, "m"), (1_000, "k")]:
        if n >= threshold and n % threshold == 0:
            return f"{n // threshold}{suffix}"
    return raw_digits
