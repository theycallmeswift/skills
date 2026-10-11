.PHONY: install test lint format

install:
	uv sync

# pytest exits 5 when it collects no tests, as in a new repo.
test:
	uv run pytest || [ $$? -eq 5 ]

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run ty check
	npx --yes markdownlint-cli2@0.23.3

format:
	uv run ruff check --fix .
	uv run ruff format .
