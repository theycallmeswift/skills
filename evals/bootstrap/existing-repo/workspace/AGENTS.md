# Ledger

Ledger reconciles bank exports against the general ledger and flags
mismatches for the finance team. Python 3.13, managed with uv.

## Conventions

- Run `make test` and `make lint` before claiming work is done.
- Never run migrations against the production database.

## Project structure

- `src/ledger/`: the reconciler.
- `docs/style/`: how code and tests are written.
