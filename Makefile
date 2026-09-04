.PHONY: help install test lint format evals evals\:install evals\:lint .evals-deps clean
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

# The eval runner is a private git dependency kept out of pyproject.toml (uv would need access to
# resolve it on every sync). `make evals:install` puts it in the venv; the eval targets do that on
# demand. `make install` prunes it again — that is fine, the next eval target reinstalls.
EVALS_DEPS = "harnessbench[microsandbox] @ git+https://github.com/theycallmeswift/harnessbench.git" "pytest-repeat>=0.9,<1"
evals\:install:  ## Install harnessbench (private git dep) into the venv; needs GitHub access to the repo
	uv pip install $(EVALS_DEPS)

.evals-deps:
	@uv run --no-sync python -c "import harnessbench, pytest_repeat" 2>/dev/null || $(MAKE) evals:install

evals: .evals-deps  ## Run evals, baseline vs trial. SKILL=to-spec scopes to evals/to-spec; EVAL_ARGS adds pytest args (-n 6, --count 3, -k …)
	uv run --no-sync harnessbench run $(if $(SET),--set $(SET),) $(if $(SKILL),--eval-paths evals/$(SKILL),) -- $(EVAL_ARGS)

evals\:lint: .evals-deps  ## Statically lint eval assertions (no credentials, no sandbox)
	uv run --no-sync harnessbench lint

clean:  ## Remove the venv and Python caches
	rm -rf .venv .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
