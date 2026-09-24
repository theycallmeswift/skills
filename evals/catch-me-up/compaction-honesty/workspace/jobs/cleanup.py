"""Nightly sweep of expired idempotency keys."""

TTL_HOURS = 24


def sweep(db):
    """Delete idempotency records older than the TTL."""
    db.execute(
        "DELETE FROM payment_idempotency WHERE created_at < now() - interval '%s hours'",
        TTL_HOURS,
    )
