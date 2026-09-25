# Idempotency: header vs body field

## Idempotency-Key header
- Orthogonal to the payload; one mechanism covers every endpoint.
- Matches what the major payment providers do, so clients already know it.

## Client-generated ID in the body
- Self-documenting in the schema.
- Survives proxies that strip unknown headers.
- Has to be added per-endpoint, one schema at a time.
