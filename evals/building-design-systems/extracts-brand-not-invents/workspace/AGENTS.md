# Lumen

Flaky-test finder: a Python CLI (`lumen/`) and a static web dashboard (`web/`).

## Commands

- `make test` runs pytest; `make lint` runs ruff.
- `lumen serve` serves `web/` on port 7300.

## References

- `docs/scoring.md`: how flip scores are computed. Read before touching `lumen/score.py`.
