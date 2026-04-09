# Evals

All evals are pytest test files. One command, familiar workflow.

## Running evals

```
make test                                          # all evals
make test ARGS="tests/skills/ghostwrite/"          # one skill
make test ARGS="-k sponsor_email"                  # one case
make test ARGS="--model claude-haiku-4-5-20251001" # specific model
make test ARGS="--verbose"                         # show evidence
make test-harness                                  # harness unit tests only
```

## Writing an eval

1. Create a test file under `tests/skills/<skill>/` or `tests/core/`.
2. Name it descriptively: `test_sponsor_email.py`, not `test_evals.py`.
3. Use a module-scoped fixture to run the agent once, share the result across assertions.

```python
import pytest
from tests.support.harness.setup import skill_setup

@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=["Your prompt here"],
        setup=skill_setup("your-skill", project_root),
    )

def test_something(result):
    assert result.contains("expected", on="final_message")
```

## Available matchers

`EvalResult` wraps the agent run and provides assertion methods returning `bool`:

**Content** (require `on` parameter: `"final_message"`, `"stdout"`, or `"files.<glob>"`):

| Method | Description |
|---|---|
| `matches_regex(pattern, on, min=1, max=inf)` | Match count within bounds |
| `not_matches_regex(pattern, on)` | Zero matches |
| `contains(text, on)` | Literal substring found |
| `contains_all(texts, on)` | Every literal found |
| `not_contains(text, on)` | Literal absent |
| `output_len_lte(n, on)` | Character count <= n |
| `output_len_gte(n, on)` | Character count >= n |
| `passes_rubric(item, on, model=None)` | LLM judge (default Haiku) grades pass/fail |

**Trace** (no `on` parameter):

| Method | Description |
|---|---|
| `tool_called(name)` | Tool name in trace (substring match) |
| `not_tool_called(name)` | Tool name absent |
| `skill_invoked(name)` | Skill tool fired with matching name |
| `not_skill_invoked(name)` | No matching Skill invocation |
| `trace_order(tools)` | Tools appear in order (gaps ok) |
| `trace_count_lte(tool, n)` | Tool count <= n |
| `turn_count_lte(n)` | Agent completed in <= n turns |
| `token_usage_lte(n)` | input + output tokens <= n |

**Files** (no `on` parameter):

| Method | Description |
|---|---|
| `file_contains(path_glob, text=None, regex=None)` | File matching glob contains text/regex |
| `not_file_contains(path_glob, text=None, regex=None)` | Negation |

## Setup helpers

```python
from tests.support.harness.setup import skill_setup, copy_files, cleanup_globs, compose

# Copy skill dir + AGENTS.md, prepend SKILL.md preamble
setup=skill_setup("summarize", project_root)

# Copy test fixtures into temp cwd
setup=copy_files("tests/support/fixtures/test-paper.pdf", project_root=project_root)

# Compose multiple setup functions
setup=compose(
    skill_setup("summarize", project_root),
    copy_files("tests/support/fixtures/test-paper.pdf", project_root=project_root),
)

# Cleanup files after run
cleanup=cleanup_globs("references/specs/2026-*-demo*.md")
```

## Fixtures

Put shared input files under `tests/support/fixtures/`.
