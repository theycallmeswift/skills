"""Write path for the widget service. Talks to the DB directly — no caching."""

from __future__ import annotations

from .db import execute


def write_widget(widget_id: str, data: dict) -> None:
    """Upsert a single widget straight to the database."""
    execute("INSERT OR REPLACE INTO widgets (id, data) VALUES (?, ?)", widget_id, data)
