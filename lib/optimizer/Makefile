.PHONY: install lint format test

install:
	uv sync --group dev

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .

test:
	uv run pytest tests/ -v -p no:xdist -m "not integration"
