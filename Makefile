.PHONY: test

test:
	uv run python -m tests.support.harness $(ARGS)
