import re


def slugify(text: str) -> str:
    """Lowercase, replace runs of non-alphanumerics with one hyphen, trim hyphens."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
