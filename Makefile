.PHONY: test test-unit

test:
	uv run python -m tests.support.harness $(ARGS)

test-unit:
	uv run pytest tests/support -v
