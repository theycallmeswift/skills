"""Payment submission endpoint."""


def create_payment(request, db):
    """Charge a payment, deduplicating on the Idempotency-Key header."""
    key = request.headers.get("Idempotency-Key")
    if key is None:
        return error(400, "Idempotency-Key is required")

    with db.transaction():
        existing = db.find_idempotency(request.merchant_id, key)
        if existing is not None:
            if existing.body_hash != hash_body(request.body):
                return error(409, "key reused with a different body")
            return existing.response

        db.insert_idempotency(request.merchant_id, key, hash_body(request.body))
        return charge(request, db)
