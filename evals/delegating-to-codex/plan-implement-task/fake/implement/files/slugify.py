import re


def slugify(text: str, max_length: int | None = None) -> str:
    """Lowercase, replace runs of non-alphanumerics with one hyphen, trim hyphens.

    When max_length is set, truncate to at most that many characters without leaving a
    trailing hyphen.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if max_length is not None:
        slug = slug[:max_length].rstrip("-")
    return slug
