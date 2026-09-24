"""Payment submission endpoint with idempotency-key deduplication."""


def create_payment(request, db):
    key = request.headers.get("Idempotency-Key")
    if key is None:
        return error(400, "Idempotency-Key is required")
    with db.transaction():
        existing = db.find_idempotency(request.merchant_id, key)
        if existing is not None:
            return existing.response
        db.insert_idempotency(request.merchant_id, key, hash_body(request.body))
        return charge(request, db)
