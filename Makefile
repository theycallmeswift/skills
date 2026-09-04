.PHONY: help install test lint format evals evals\:lint clean
.DEFAULT_GOAL := help

help:  ## Show this help
	@awk '/^[a-zA-Z_:\\-]+:.*## / {t=$$0; sub(/:[ \t]*##.*/,"",t); gsub(/\\/,"",t); d=$$0; sub(/^.*## /,"",d); printf "  \033[36m%-15s\033[0m %s\n", t, d}' $(MAKEFILE_LIST)

install:  ## Create the venv and install dev dependencies (uv sync)
	uv sync

test:  ## Run the unit test suite (skill scripts). Plugin autoload is off so harnessbench stays out of unit runs
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest

lint:  ## Lint Python with ruff
	uv run ruff check .

format:  ## Format Python with ruff
	uv run ruff format .

# Evals need the opt-in `evals` dependency group (harnessbench, a private git dep) — `uv run --group`
# syncs it on demand. See docs/development.md for credentials and how a suite is laid out.
evals:  ## Run evals, baseline vs trial. SKILL=to-spec scopes to evals/to-spec; EVAL_ARGS adds pytest args (-n 6, --count 3, -k …)
	uv run --group evals harnessbench run $(if $(SET),--set $(SET),) $(if $(SKILL),--eval-paths evals/$(SKILL),) -- $(EVAL_ARGS)

evals\:lint:  ## Statically lint eval assertions (no credentials, no sandbox)
	uv run --group evals harnessbench lint

clean:  ## Remove the venv and Python caches
	rm -rf .venv .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
