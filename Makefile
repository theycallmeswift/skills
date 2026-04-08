.PHONY: install test test-harness lint format

install:
	uv sync

test:
	uv run python -m tests.support.harness $(ARGS)

test-harness:
	uv run pytest -v

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .
