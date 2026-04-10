# Testing & Evals

## Quick Start

```bash
make test
```

Runs the full pytest suite with parallel execution (pytest-xdist). Target runtime: under 2 minutes with haiku.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_TEST_MODEL` | `haiku` | Model to use for test runs |
| `CLAUDE_TEST_TIMEOUT` | `60` | Timeout in seconds per CLI call |
| `CLAUDE_TEST_CWD` | `tmp/tests/<run_id>` | Working directory for subprocess |
| `CLAUDE_TEST_PLUGIN_DIR` | project root | Plugin directory to load skills from |

## Test Structure

```
tests/
├── conftest.py                        # Session-scoped runner fixture
├── support/
│   ├── harness/claude_runner.py       # ClaudeRunner — invokes `claude -p`
│   └── assertions/
│       ├── deterministic.py           # Pure-Python checks (regex, string matching)
│       └── judge.py                   # LLM judge for semantic checks
└── skills/
    └── ghostwrite/
        ├── conftest.py                # Source content fixtures per medium
        ├── test_ghostwrite_rules.py   # Rule compliance (~6 tests)
        └── test_ghostwrite_mediums.py # Medium formatting (~10 tests)
```

## Writing a New Test

1. Add a test function in the appropriate `test_*.py` file
2. Use the `runner` fixture to call Claude: `output = runner.run("your prompt")`
3. Assert with deterministic helpers or the LLM judge

```python
def test_my_rule(self, runner, email_prompt, email_source):
    output = runner.run(email_prompt)
    violations = no_em_dashes(output)
    assert violations == [], f"Em dashes found: {violations}"
```

## Adding a Deterministic Assertion

Add a function to `tests/support/assertions/deterministic.py`:

```python
def my_check(text: str) -> list[str]:
    """Return violations. Empty list = pass."""
    return [line for line in text.splitlines() if some_condition(line)]
```

Export it from `tests/support/assertions/__init__.py`.

## Using the LLM Judge

For semantic checks that regex can't handle:

```python
from tests.support.assertions import judge

result = judge(
    source=original_text,
    output=rewritten_text,
    rubric="The opening sentence contains the main point or ask.",
    runner=runner,
)
assert result.passed, f"Failed: {result.reasoning}"
```

Judge tests make an additional LLM call, so use sparingly.

## Adding Tests for a New Skill

1. Create `tests/skills/<skill_name>/conftest.py` with source content fixtures
2. Create `tests/skills/<skill_name>/test_<skill_name>_*.py` with test cases
3. Tests automatically pick up the shared `runner` fixture from `tests/conftest.py`

## Running Options

```bash
# Full suite, parallel (default)
make test

# Serial execution (debugging)
uv run pytest tests/ -v -n0

# Single test file
uv run pytest tests/skills/ghostwrite/test_ghostwrite_rules.py -v

# Single test
uv run pytest tests/skills/ghostwrite/test_ghostwrite_rules.py::TestGhostwriteRules::test_no_em_dashes -v

# With different model
CLAUDE_TEST_MODEL=sonnet make test
```
