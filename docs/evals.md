# Evals

All evals are pytest test files. One command, familiar workflow.

## Running evals

```
make test                                          # all evals (parallel)
make test ARGS="tests/skills/ghostwrite/"          # one skill
make test ARGS="-k sponsor_email"                  # one case
make test ARGS="--model claude-haiku-4-5-20251001" # specific model
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

`EvalResult` wraps the agent run and provides assertion methods returning `bool`. Content matchers require an `on` parameter: `"final_message"`, `"stdout"`, or `"files.<glob>"`.

| Method | `on` | Description |
|---|---|---|
| `matches_regex(pattern, on, min=1, max=inf)` | yes | Match count within bounds |
| `not_matches_regex(pattern, on)` | yes | Zero matches |
| `contains(text, on)` | yes | Literal substring found |
| `contains_all(texts, on)` | yes | Every literal found |
| `not_contains(text, on)` | yes | Literal absent |
| `llm_judge(item, on=None, content=None)` | optional | LLM judge (Haiku) grades pass/fail. Pass `on` for a source or `content` for raw text |
| `tool_called(name)` | no | Tool name in trace (substring match) |
| `not_tool_called(name)` | no | Tool name absent |
| `skill_invoked(name)` | no | Skill tool fired with matching name |
| `not_skill_invoked(name)` | no | No matching Skill invocation |
| `trace_order(tools)` | no | Tools appear in order (gaps ok) |
| `trace_count_lte(tool, n)` | no | Tool count <= n |
| `turn_count_lte(n)` | no | Agent completed in <= n turns |
| `token_usage_lte(n)` | no | input + output tokens <= n |
| `file_contains(path_glob, text=None, regex=None)` | no | File matching glob contains text/regex |
| `not_file_contains(path_glob, text=None, regex=None)` | no | Negation |

## Setup helpers

```python
from tests.support.harness.setup import skill_setup, copy_files, cleanup_globs, compose

setup=skill_setup("summarize", project_root)
setup=copy_files("tests/support/fixtures/test-paper.pdf", project_root=project_root)
setup=compose(
    skill_setup("summarize", project_root),
    copy_files("tests/support/fixtures/test-paper.pdf", project_root=project_root),
)
cleanup=cleanup_globs("references/specs/2026-*-demo*.md")
```

## Fixtures

Put shared input files under `tests/support/fixtures/`.

## Example output

```
$ make test ARGS="tests/skills/ghostwrite/"

==================== Eval Summary ====================

Skill            Test                        Result   Time
ghostwrite       test_blog_format            4/4      22.1s
ghostwrite       test_email_format           6/6      18.4s
ghostwrite       test_linkedin_format        5/5      19.7s
ghostwrite       test_slack_format           6/6      15.3s
ghostwrite       test_refuses_from_scratch   2/2      8.9s
                                             23/23    22.1s

==================== 23 passed in 22.1s ====================
```
