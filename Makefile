.PHONY: install test test-harness lint format

install:
	uv sync

test:
	uv run pytest tests/skills/ tests/core/ -n auto $(ARGS)

test-harness:
	uv run pytest tests/support/harness/tests/ $(ARGS)

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .
