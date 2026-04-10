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
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.split()) > max_words]


def banned_words(text: str) -> list[str]:
    """Return banned words/phrases found in text. Empty list = pass."""
    lower = text.lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in lower]


def urls_preserved(source: str, output: str) -> list[str]:
    """Return URLs from source missing in output. Empty list = pass."""
    url_pattern = re.compile(r'https?://[^\s)\]>,]+')
    source_urls = set(url_pattern.findall(source))
    return [url for url in source_urls if url not in output]


def stats_preserved(source: str, output: str) -> list[str]:
    """Return numbers/stats from source missing in output. Empty list = pass."""
    stat_pattern = re.compile(r'\d[\d,]*(?:\.\d+)?')
    source_stats = set(stat_pattern.findall(source))
    return [stat for stat in source_stats if stat not in output]


def email_signoff(text: str) -> bool:
    """Check text ends with '- Swift' or 'Happy Hacking,\\nSwift'."""
    stripped = text.rstrip()
    return stripped.endswith("- Swift") or stripped.endswith("Happy Hacking,\nSwift")


def slack_word_count(text: str) -> int:
    """Return total word count."""
    return len(text.split())


def linkedin_hashtag_count(text: str) -> int:
    """Return count of hashtags (#word patterns)."""
    return len(re.findall(r'#\w+', text))
