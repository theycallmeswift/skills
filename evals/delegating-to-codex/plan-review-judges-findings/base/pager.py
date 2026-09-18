def page_slice(items: list, page: int, size: int) -> list:
    """Return the 1-indexed page of items."""
    start = (page - 1) * size
    return items[start:start + size]
