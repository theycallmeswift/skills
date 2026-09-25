"""Nightly sweep of expired idempotency keys."""


def sweep(db):
    """Delete idempotency records past their 24-hour expiry (set by the migration)."""
    db.execute("DELETE FROM payment_idempotency WHERE expires_at < now()")
