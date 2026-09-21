# Plan: cents conversion

Run tests with `python3 -m unittest -q`.

## Task 1 — Write the tests for `to_cents` (done)

`./test_money.py` is committed and currently fails: it is the contract for Task 2, and no
task may edit it.

## Task 2 — Implement `to_cents`

- **Implementer:** Codex
- **Change:** `to_cents(amount)` converts a dollar amount to whole cents.
- **Named risks:**
  - A tie rounds up, never to even: `to_cents(0.125)` is `13`, not `12`. Python's built-in
    `round` rounds ties to even, so it does not satisfy this on its own.
  - Floating-point dollars like `1.236` must not round down.
- **Done when:** `python3 -m unittest -q` passes with `./test_money.py` unchanged.

## Task 3 — Use `to_cents` in the invoice exporter
