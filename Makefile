.PHONY: help install test test\:e2e lint format evals evals\:lint clean
.DEFAULT_GOAL := help

help:  ## Show this help
	@awk '/^[a-zA-Z_:\\-]+:.*## / {t=$$0; sub(/:[ \t]*##.*/,"",t); gsub(/\\/,"",t); d=$$0; sub(/^.*## /,"",d); printf "  \033[36m%-15s\033[0m %s\n", t, d}' $(MAKEFILE_LIST)

install:  ## Create the venv and install dev dependencies (uv sync)
	uv sync

test:  ## Run the test suite: skill scripts plus the real-Codex contract test (needs `codex` installed). Autoload off so benchspec stays out
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest

test\:e2e:  ## Run e2e tests against real external CLIs (codex must be signed in; ~2 min)
	PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest -m e2e

lint:  ## Lint and type-check Python (ruff + ty)
	uv run ruff check .
	uv run ty check

format:  ## Format Python with ruff
	uv run ruff format .

# The eval runner (benchspec) lives in the opt-in `evals` dependency group — `uv run --group evals`
# syncs it on demand. See docs/development.md for credentials and how a suite is laid out.
evals:  ## Run evals, baseline vs trial. SKILL=to-spec scopes to evals/to-spec; EVAL_ARGS adds pytest args (-n 6, --count 3, -k …)
	uv run --group evals benchspec run $(if $(SET),--set $(SET),) $(if $(SKILL),--eval-paths evals/$(SKILL),) -- $(EVAL_ARGS)

evals\:lint:  ## Statically lint eval assertions (no credentials, no sandbox)
	uv run --group evals benchspec lint

clean:  ## Remove the venv and Python caches
	rm -rf .venv .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
