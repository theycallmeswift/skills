"""Read path for the widget service. Talks to the DB directly — no caching."""

from __future__ import annotations

from .db import query_one


def read_widget(widget_id: str) -> dict:
    """Fetch a single widget by id straight from the database."""
    return query_one("SELECT * FROM widgets WHERE id = ?", widget_id)
