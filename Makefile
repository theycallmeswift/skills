.PHONY: install test eval test-harness lint format

install:
	uv sync

test:
	uv run python -m tests.support.harness --tier test $(ARGS)

eval:
	uv run python -m tests.support.harness --tier eval $(ARGS)

test-harness:
	uv run pytest -v

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .
