.PHONY: install lint format test

install:
	uv sync

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .

test:
	uv run pytest tests/ -v
