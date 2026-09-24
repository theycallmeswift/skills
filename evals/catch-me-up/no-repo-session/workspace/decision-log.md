# Decision log

- Working preference: the `Idempotency-Key` header, on convention grounds.
- Open: whether our CDN strips unknown headers. Cannot be checked from here.
  If it does, the body-field approach wins and this decision flips.
- Status: left open pending an answer from infra. No implementation started.
