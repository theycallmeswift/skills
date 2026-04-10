.PHONY: install lint format

install:
	uv sync

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .
