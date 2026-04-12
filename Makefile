.PHONY: install lint format test benchmark

install:
	uv sync

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .

test:
	uv run pytest tests/ -v

benchmark:
	claude -p "/mechaswift:benchmark" --model sonnet --plugin-dir . --dangerously-skip-permissions --output-format text --verbose
