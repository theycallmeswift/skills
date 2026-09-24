"""Persistence helpers for payment idempotency records."""


class IdempotencyRecord:
    """A stored key, the hash of the body it was used with, and the response."""

    __slots__ = ("merchant_id", "key", "body_hash", "response", "created_at")
