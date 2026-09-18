def page_slice(items: list, page: int, size: int) -> list:
    """Return the 1-indexed page of items."""
    start = (page - 1) * size
    return items[start:start + size]


def page_count(total: int, size: int) -> int:
    """Number of pages needed to show `total` items, `size` per page."""
    if size <= 0:
        raise ValueError("size must be positive")
    return -(-total // size)
