CREATE TABLE payment_idempotency (
    merchant_id BIGINT      NOT NULL,
    key         TEXT        NOT NULL,
    body_hash   TEXT        NOT NULL,
    response    JSONB,                  -- written once the charge completes
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT now() + interval '24 hours'
);

CREATE UNIQUE INDEX payment_idempotency_merchant_key
    ON payment_idempotency (merchant_id, key);

CREATE INDEX payment_idempotency_expires_at
    ON payment_idempotency (expires_at);
