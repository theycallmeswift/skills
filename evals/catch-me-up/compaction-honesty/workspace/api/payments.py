"""Payment submission endpoint with idempotency-key deduplication."""


def create_payment(request, db):
    """Charge once per Idempotency-Key, replaying the first response on a retry."""
    key = request.headers.get("Idempotency-Key")
    if key is None:
        return error(400, "Idempotency-Key is required")

    body_hash = hash_body(request.body)

    with db.transaction():
        existing = db.find_idempotency(request.merchant_id, key)
        if existing is not None:
            return _replay(existing, body_hash)

        # The insert is what makes this safe: the unique index rejects a second
        # writer, so only one request per key ever reaches db.charge().
        with db.savepoint():
            try:
                db.insert_idempotency(request.merchant_id, key, body_hash)
            except db.UniqueViolation:
                # Roll back to the savepoint before querying -- Postgres refuses
                # further statements in a transaction that hit an error.
                db.rollback_to_savepoint()
                winner = db.find_idempotency(request.merchant_id, key)
                return _replay(winner, body_hash)

        # Same transaction as the key: a retry blocked on the unique index only
        # sees the row after commit, by which point the response is stored.
        response = db.charge(request)
        db.store_response(request.merchant_id, key, response)
        return response


def _replay(record, body_hash):
    """Return the stored response, or 409 when the key was reused with a new body."""
    if record.body_hash != body_hash:
        return error(409, "key reused with a different body")
    return record.response
