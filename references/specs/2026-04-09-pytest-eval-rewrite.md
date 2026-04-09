# Pytest Eval Rewrite

Replace the custom JSON-based eval harness with idiomatic pytest. One format, one runner, self-contained test files.

## Goals

1. **One format** — Python test files, no JSON eval definitions, no Markdown rubrics
2. **Self-contained tests** — each test file has its own setup (fixture), teardown (cleanup), and assertions. No cross-referencing skill directories for rubric items.
3. **Mirrored structure** — `skills/ghostwrite/` -> `tests/skills/ghostwrite/`
4. **Descriptive names** — `test_sponsor_email.py`, not `evals.json` or `test_evals.py`
5. **Reuse expensive runs** — module-scoped fixtures so a single agent run serves all assertions in a file

## Directory Structure

```
tests/
  conftest.py                              # run_eval fixture, CLI options, reporter plugin
  skills/
    conftest.py                            # marks skill tests
    ghostwrite/
      test_sponsor_email.py                # rewrite email in Swift's voice
      test_linkedin_from_scratch.py        # refuse to draft without source
    summarize/
      test_devto_article.py                # summarize a live dev.to article
      test_rust_tab_orchestrator.py        # summarize specific URL
      test_anthropic_character.py          # summarize anthropic.com page
      test_local_pdf.py                    # summarize a PDF file
      test_pasted_text.py                  # summarize raw pasted content
      test_short_input.py                  # don't pad short input
    scope/
      test_github_webhook_slack.py         # full multi-turn scoping flow
      test_vague_notifications.py          # ask clarifying questions first
      test_skip_design.py                  # push back on skipping scoping
    prompt-engineer/
      test_contract_extraction.py          # structured JSON extraction prompt
      test_fix_bad_prompt.py               # diagnose and fix a broken prompt
      test_vague_summarization.py          # ask before drafting
  core/
    conftest.py                            # marks core tests
    test_no_ai_attribution.py              # 3 cases: throwaway-commit, pr-draft, amend
    test_skill_triggers.py                 # 6 cases: trigger + no-trigger
  support/
    fixtures/
      test-paper.pdf                       # test data files
    harness/
      runner.py                            # agent execution via Agent SDK
      setup.py                             # setup/cleanup helpers (skill_setup, copy_files, etc.)
      matchers.py                          # EvalResult class with assertion methods
      reporter.py                          # pytest plugin for grouped reporting
      models.py                            # RunResult dataclass
      tests/                               # unit tests for harness internals
        test_matchers.py
        test_runner.py
        test_reporter.py
        test_setup.py
```

## `run_eval` Fixture

The `run_eval` function is defined in the harness (`tests/support/harness/runner.py`) and exposed as a pytest fixture via `tests/conftest.py`. This keeps the logic testable — harness unit tests can call `run_eval` directly without pytest fixtures.

```python
# tests/support/harness/runner.py
def run_eval(
    project_root: Path,
    turns: list[str],                               # user messages, sent sequentially
    setup: Callable[[Path], None] | None = None,    # called with temp cwd before run
    cleanup: Callable[[Path], None] | None = None,  # called with temp cwd after run
    model: str | None = None,                       # override runner model
) -> EvalResult:
    ...

# tests/conftest.py
@pytest.fixture(scope="module")
def run_eval(project_root, request):
    def _run(**kwargs):
        return harness_run_eval(project_root=project_root, **kwargs)
    return _run
```

`setup` and `cleanup` are callables that receive the temp directory `Path`. This keeps `run_eval` generic — the harness doesn't need to know about skills, file copying, or glob patterns. Common setup patterns are provided as helpers:

```python
# tests/support/harness/setup.py
def skill_setup(skill: str, project_root: Path) -> Callable[[Path], None]:
    """Copy skill dir + AGENTS.md into temp cwd, prepend SKILL.md preamble."""
    ...

def copy_files(*paths: str) -> Callable[[Path], None]:
    """Copy files into temp cwd."""
    ...

def cleanup_globs(*patterns: str) -> Callable[[Path], None]:
    """Delete files matching globs."""
    ...

def compose(*fns: Callable[[Path], None]) -> Callable[[Path], None]:
    """Run multiple setup/cleanup functions in sequence."""
    ...
```

Behavior:

- Creates a temp directory for the run
- Calls `setup(tmp_dir)` if provided
- Sends `turns` sequentially through the Agent SDK
- Captures stdout, tool trace, files written, tokens, exit code
- Returns an `EvalResult`
- Calls `cleanup(tmp_dir)` if provided

Unit tests for `run_eval` live in `tests/support/harness/tests/test_runner.py`.

## Test Patterns

### Skill test

```python
# tests/skills/summarize/test_devto_article.py
from tests.support.harness.setup import skill_setup

@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=["Summarize the top article on dev.to that isn't a challenge or contest announcement"],
        setup=skill_setup("summarize", project_root),
    )

def test_has_source_link(result):
    assert result.passes_rubric(
        "Output contains a clickable markdown link to the source dev.to URL near the title",
        on="final_message",
    )

def test_uses_brightdata(result):
    assert result.tool_called("scrape_as_markdown")

def test_no_webfetch(result):
    assert result.not_tool_called("WebFetch")

def test_no_websearch(result):
    assert result.not_tool_called("WebSearch")
```

### Skill test with file fixtures

```python
# tests/skills/summarize/test_local_pdf.py
from tests.support.harness.setup import skill_setup, copy_files, compose

@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=["Summarize this PDF: test-paper.pdf"],
        setup=compose(
            skill_setup("summarize", project_root),
            copy_files("tests/support/fixtures/test-paper.pdf"),
        ),
    )

def test_title_from_content(result):
    assert result.passes_rubric(
        "Title is based on the document/paper title or filename, not a generic placeholder",
        on="final_message",
    )

def test_no_brightdata(result):
    assert result.not_tool_called("brightdata")

def test_uses_read(result):
    assert result.tool_called("Read")
```

### Skill test with cleanup

```python
# tests/skills/scope/test_github_webhook_slack.py
from tests.support.harness.setup import skill_setup, cleanup_globs

@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            "Scope a GitHub webhook system for MechaSwift...",
            "Purpose is surfacing PR activity in Slack...",
            "Go with your recommendation. Walk me through the design.",
            "Looks good, keep going.",
            "Design is approved. Write the spec.",
            "Spec looks good. Nothing else for now.",
        ],
        setup=skill_setup("scope", project_root),
        cleanup=cleanup_globs("references/specs/2026-*-github-webhook*.md"),
    )

def test_proposes_approaches(result):
    assert result.passes_rubric(
        "Output proposes 2-3 distinct approaches with trade-offs",
        on="final_message",
    )

def test_writes_spec_file(result):
    assert any(fnmatch(f, "references/specs/*.md") for f in result.files_written)

def test_no_implementation_code(result):
    assert not any(fnmatch(f, "*.py") for f in result.files_written)
    assert not any(fnmatch(f, "*.js") for f in result.files_written)
    assert not any(fnmatch(f, "*.ts") for f in result.files_written)
    assert "package.json" not in result.files_written
```

### Core test (no skill, grouped)

```python
# tests/core/test_no_ai_attribution.py

@pytest.fixture(scope="module")
def throwaway_commit(run_eval):
    return run_eval(turns=[
        "In a new subdirectory `fake-repo` of your current working directory, ..."
    ])

@pytest.fixture(scope="module")
def pr_draft(run_eval):
    return run_eval(turns=[
        "In a new subdirectory `fake-repo` of your current working directory, ..."
    ])

def test_throwaway_no_coauthor(throwaway_commit):
    assert throwaway_commit.not_matches_regex(r"Co-Authored-By:", on="stdout")

def test_pr_draft_no_generated_footer(pr_draft):
    assert pr_draft.not_matches_regex(r"Generated with", on="final_message")
```

## EvalResult

```python
class EvalResult:
    # Data
    stdout: str
    final_message: str
    files_written: dict[str, str]      # path -> content
    tool_trace: list[dict]
    input_tokens: int
    output_tokens: int
    exit_code: int
    turn_count: int
    duration_s: float

    # Deterministic matchers — return bool for use with assert
    def matches_regex(self, pattern, on, min=1, max=inf) -> bool
    def not_matches_regex(self, pattern, on) -> bool
    def contains(self, text, on) -> bool
    def contains_all(self, texts, on) -> bool
    def not_contains(self, text, on) -> bool
    def output_len_lte(self, n, on) -> bool
    def output_len_gte(self, n, on) -> bool
    def token_usage_lte(self, n) -> bool
    def tool_called(self, name) -> bool
    def not_tool_called(self, name) -> bool
    def skill_invoked(self, name) -> bool
    def not_skill_invoked(self, name) -> bool
    def trace_order(self, tools) -> bool
    def trace_count_lte(self, tool, n) -> bool
    def turn_count_lte(self, n) -> bool
    def file_contains(self, path_glob, text=None, regex=None) -> bool
    def not_file_contains(self, path_glob, text=None, regex=None) -> bool
    def passes_rubric(self, item, on, model=None) -> bool
```

The `on` parameter is required on all content matchers and targets what gets checked:

- `"final_message"` — the agent's last response
- `"stdout"` — full captured stdout
- `"files.<glob>"` — content of files matching the glob

`passes_rubric` sends the item + targeted content to an LLM judge (default Haiku) and returns pass/fail.

Trace and token matchers don't take `on` — they always check the trace/token data.

## Makefile

```makefile
.PHONY: test test-harness

test:
	uv run pytest tests/skills/ tests/core/ $(ARGS)

test-harness:
	uv run pytest tests/support/harness/tests/ $(ARGS)
```

```bash
make test                                          # all evals
make test ARGS="tests/skills/ghostwrite/"          # one skill
make test ARGS="-k sponsor_email"                  # one case
make test ARGS="--model claude-haiku-4-5-20251001" # specific model
make test ARGS="--verbose"                         # show evidence
make test-harness                                  # harness unit tests only
```

### Example output

```
$ make test
uv run pytest tests/skills/ tests/core/

Skill            Test                       Result   Time
ghostwrite       test_sponsor_email         3/4      15.2s
ghostwrite       test_linkedin_scratch      3/3      12.8s
summarize        test_devto_article         4/4      18.1s
summarize        test_rust_tab_orchestrator 4/4      17.5s
scope            test_vague_notifications   1/3      14.5s
scope            test_github_webhook_slack  7/7      22.3s
core             test_skill_triggers        6/6      11.3s
core             test_no_ai_attribution     4/4      16.4s
                                            32/35    48.1s

================================ FAILURES ================================

tests/skills/ghostwrite/test_sponsor_email.py::test_sign_off
  AssertionError: matches_regex failed on final_message
    pattern: (?m)(- Swift|Happy Hacking,\s*\nSwift)\s*$
    final_message (last 200 chars):
      ...Let me know if you'd like to hop on a call next week.

      Best regards,
      Mike

tests/skills/scope/test_vague_notifications.py::test_asks_clarifying_question
  AssertionError: passes_rubric failed on final_message
    rubric: "Output asks at least one clarifying question before proposing approaches"
    judge_reasoning: "The output immediately proposes three notification
      architectures without asking any clarifying questions about the user's
      requirements, audience, or constraints."

tests/skills/scope/test_vague_notifications.py::test_no_full_design
  AssertionError: passes_rubric failed on final_message
    rubric: "Output does not propose a full design without first gathering requirements"
    judge_reasoning: "The output presents three complete architectural approaches
      with trade-offs, which constitutes a full design proposal."

================== 3 failed, 32 passed in 48.1s ==================
```

Each row is one agent run (module-scoped fixture). Multiple assertions against the same run are aggregated into the Result column. Failures print full detail below the table.

## CLI Options

Registered in `tests/conftest.py`:

- `--model` — override the model the agent uses for runs
- `--verbose` — show passing assertion evidence in output

## Reporter

`tests/support/harness/reporter.py` is a pytest plugin registered via `conftest.py`:

```python
pytest_plugins = ["tests.support.harness.reporter"]
```

It hooks into pytest reporting to:

- Print a summary table with one row per test file (skill, test name, pass/total, duration)
- Print full failure details below the table
- Show assertion evidence when `--verbose` is set

## Future: Comparative Benchmarks

Comparative benchmarking (skill vs no-skill, model A vs model B) is out of scope for this rewrite. A future `make benchmark` mode will add:

- Parametrized runs across configurations (skill loaded/not, model variants)
- Matrix reporter showing pass rates per config
- Delta analysis

The test infrastructure built here (runner, setup helpers, matchers) will serve as the foundation.

## Conventions

- Use `textwrap.dedent` on multi-line strings in Python test code
- `test-harness` is an implementation detail — de-emphasize in docs. The harness internals are intended to become a standalone library.

## Migration

### Files created

- `tests/conftest.py`
- `tests/skills/conftest.py`
- `tests/core/conftest.py`
- `tests/support/harness/matchers.py`
- `tests/support/harness/setup.py`
- `tests/support/harness/reporter.py` (rewritten as pytest plugin)
- 14 test files under `tests/skills/`
- 2 test files under `tests/core/`
- Harness unit tests: `tests/support/harness/tests/test_matchers.py`, `test_reporter.py`, `test_setup.py`

### Files moved

- `tests/skills/summarize/test-paper.pdf` -> `tests/support/fixtures/test-paper.pdf`

### Files deleted

- All `evals.json` files (6 files)
- `eval.schema.json`
- `tests/support/fixtures/sample-core-eval.json`, `sample-skill-eval.json`
- `tests/support/harness/discovery.py`, `orchestrator.py`, `grader.py`, `__main__.py`
- `tests/support/harness/tests/test_discovery.py`, `test_orchestrator.py`, `test_grader.py`
- `skills/ghostwrite/lint.py`, `skills/summarize/lint.py`
- `tests/skills/ghostwrite/test_lint.py`, `tests/skills/summarize/test_lint.py`
- All `__init__.py` files under `tests/` (pytest doesn't need them)
- All `RUBRIC.md` files from the worktree

### Files updated

- `Makefile` — new test targets
- `docs/evals.md` — rewritten for pytest-based system
- `CLAUDE.md` — update Commands section
- Skill `SKILL.md` files — remove references to lint.py self-check

### Assertion migration

Every existing JSON assertion maps to a pytest assertion:

| JSON form | pytest form |
|---|---|
| `{"regex": "..."}` | `result.matches_regex(r"...", on="final_message")` |
| `{"not_regex": "..."}` | `result.not_matches_regex(r"...", on="final_message")` |
| `{"contains": "..."}` | `result.contains("...", on="final_message")` |
| `{"contains_all": [...]}` | `result.contains_all([...], on="final_message")` |
| `{"not_contains": "..."}` | `result.not_contains("...", on="final_message")` |
| `{"tool_called": "..."}` | `result.tool_called("...")` |
| `{"tool_not_called": "..."}` | `result.not_tool_called("...")` |
| `{"skill_invoked": "..."}` | `result.skill_invoked("...")` |
| `{"skill_not_invoked": "..."}` | `result.not_skill_invoked("...")` |
| `{"files_written_include": "..."}` | `assert any(fnmatch(f, "...") for f in result.files_written)` |
| `{"files_written_exclude": "..."}` | `assert not any(fnmatch(f, "...") for f in result.files_written)` |
| `{"files_written_count": N}` | `assert len(result.files_written) == N` |
| `{"file_contains": {...}}` | `result.file_contains("glob", text="..." or regex="...")` |
| `{"text": "..."}` | `result.passes_rubric("...", on="final_message")` |
| `{"lint": "..."}` / `{"script_name": "..."}` | Inline the checks as regular assertions (e.g., `result.not_contains("—", on="final_message")`). Delete lint.py after migration. |

## What stays

- `tests/support/harness/runner.py` — agent execution core, adapted for the new fixture API
- `tests/support/harness/models.py` — `RunResult` dataclass
