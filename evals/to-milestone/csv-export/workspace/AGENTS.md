# ledger

A command-line ledger for small teams: import bank CSVs, categorize
transactions, report by account. Python 3.12, packaged with uv.

## Conventions

- Use conventional commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Before claiming work is done, run `make test` and `make lint`.
- Keep `docs/` current, and update it in the same PR as the code.

## Landing changes

- Open every PR as a draft from `.github/pull_request_template.md`.
- Every PR lands on `main` as one squash commit.

## Project structure

- `src/ledger/`: the package; `cli.py` is the command line.
- `tests/`: pytest, mirroring `src/ledger/`.
- `docs/specs/`: dated design specs, one per milestone.
- `docs/style/`: how code, tests, and docs are written.
