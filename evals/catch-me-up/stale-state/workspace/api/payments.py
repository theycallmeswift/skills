"""Payment submission endpoint with idempotency-key deduplication."""


def create_payment(request, db):
    """Charge once per Idempotency-Key, replaying the first response on a retry."""
    key = request.headers.get("Idempotency-Key")
    if key is None:
        return error(400, "Idempotency-Key is required")

    with db.transaction():
        existing = db.find_idempotency(request.merchant_id, key)
        if existing is not None:
            if existing.body_hash != hash_body(request.body):
                return error(409, "key reused with a different body")
            return existing.response

        try:
            db.insert_idempotency(request.merchant_id, key, hash_body(request.body))
        except db.UniqueViolation:
            # A concurrent request inserted the same key first. Read back its
            # response rather than charging a second time.
            return db.find_idempotency(request.merchant_id, key).response

        return charge(request, db)
