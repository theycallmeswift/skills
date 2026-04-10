"""Ghostwrite-specific test helpers. Not reused across skills."""

import re


def email_signoff(text: str) -> bool:
    """Check text ends with '- Swift' or 'Happy Hacking,\\nSwift'."""
    stripped = text.rstrip()
    return stripped.endswith("- Swift") or stripped.endswith("Happy Hacking,\nSwift")


def linkedin_hashtag_count(text: str) -> int:
    """Return count of hashtags (#word patterns)."""
    return len(re.findall(r"#\w+", text))
