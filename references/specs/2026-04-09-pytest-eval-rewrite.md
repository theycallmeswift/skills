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
      test_sponsor_email.py                # lift: rewrite email in Swift's voice
      test_linkedin_from_scratch.py        # lift: refuse to draft without source
    summarize/
      test_devto_article.py                # regression: summarize a live dev.to article
      test_rust_tab_orchestrator.py        # regression: summarize specific URL
      test_anthropic_character.py          # regression: summarize anthropic.com page
      test_local_pdf.py                    # regression: summarize a PDF file
      test_pasted_text.py                  # regression: summarize raw pasted content
      test_short_input.py                  # regression: don't pad short input
    scope/
      test_github_webhook_slack.py         # regression: full multi-turn scoping flow
      test_vague_notifications.py          # lift: ask clarifying questions first
      test_skip_design.py                  # lift: push back on skipping scoping
    prompt-engineer/
      test_contract_extraction.py          # regression: structured JSON extraction prompt
      test_fix_bad_prompt.py               # lift: diagnose and fix a broken prompt
      test_vague_summarization.py          # regression: ask before drafting
  core/
    conftest.py                            # marks core tests
    test_no_ai_attribution.py              # 3 cases: throwaway-commit, pr-draft, amend
    test_skill_triggers.py                 # 6 cases: trigger + no-trigger
  support/
    fixtures/
      test-paper.pdf                       # test data files
    harness/
      runner.py                            # agent execution via Agent SDK
      matchers.py                          # EvalResult class with assertion methods
      reporter.py                          # pytest plugin for lift reporting
      models.py                            # RunResult dataclass
      tests/                               # unit tests for harness internals
        test_matchers.py
        test_runner.py
        test_reporter.py
```

## `run_eval` Fixture

Provided in `tests/conftest.py`. Creates a temp directory, seeds it with context files, runs the agent, returns an `EvalResult`.

```python
@pytest.fixture(scope="module")
def run_eval(project_root, request):
    def _run(
        skill: str | None = None,    # loads skills/<name>/ into context
        turns: list[str] = None,     # user messages, sent sequentially
        files: list[str] = None,     # paths relative to test file, copied into temp cwd
        cleanup: list[str] = None,   # globs to delete after run
        model: str | None = None,    # override runner model
    ) -> EvalResult:
        ...
    return _run
```

Behavior:

- Creates a temp directory for the run
- Copies `AGENTS.md` into it
- If `skill` is set, copies `skills/<name>/` into it and prepends the "read and follow SKILL.md" preamble to the first turn
- Resolves `files` relative to the calling test file's directory, copies them in
- Sends `turns` sequentially through the Agent SDK
- Captures stdout, tool trace, files written, tokens, exit code
- Returns an `EvalResult`
- Cleans up `cleanup` globs and temp directory after the module finishes

## Test Patterns

### Regression case (single run)

```python
# tests/skills/summarize/test_devto_article.py

@pytest.fixture(scope="module")
def result(run_eval):
    return run_eval(
        skill="summarize",
        turns=["Summarize the top article on dev.to that isn't a challenge or contest announcement"],
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

### Lift case (with_skill vs baseline)

```python
# tests/skills/ghostwrite/test_sponsor_email.py

@pytest.fixture(scope="module")
def result(run_eval):
    return run_eval(
        skill="ghostwrite",
        turns=["Rewrite this as an email to our sponsor contact Sarah: ..."],
    )

@pytest.fixture(scope="module")
def baseline(run_eval):
    return run_eval(
        turns=["Rewrite this as an email to our sponsor contact Sarah: ..."],
    )

def test_greeting(result):
    assert result.matches_regex(r"(?m)^Hey, Sarah --", on="final_message")

def test_sign_off(result):
    assert result.matches_regex(
        r"(?m)(- Swift|Happy Hacking,\s*\nSwift)\s*$", on="final_message"
    )

def test_preserves_facts(result):
    assert result.passes_rubric(
        "Preserves all key facts: 450 fellows, 30% increase, 92% recommendation rate",
        on="final_message",
    )

def test_no_em_dash(result):
    assert result.not_contains("—", on="final_message")

def test_baseline_lacks_greeting(baseline):
    assert not baseline.matches_regex(r"(?m)^Hey, Sarah --", on="final_message")
```

### Core case (no skill, grouped)

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
make test ARGS="--eval-verbose"                    # show evidence
make test-harness                                  # harness unit tests only
```

## CLI Options

Registered in `tests/conftest.py`:

- `--model` — override the model the agent uses for runs
- `--eval-verbose` — show passing assertion evidence in output

## Reporter

`tests/support/harness/reporter.py` is a pytest plugin registered via `conftest.py`:

```python
pytest_plugins = ["tests.support.harness.reporter"]
```

It hooks into pytest reporting to:

- Group results by skill/core
- For lift cases (files with both `result` and `baseline` fixtures), print a comparison table
- Show assertion evidence when `--eval-verbose` is set

## Conventions

- Use `textwrap.dedent` on multi-line strings in Python test code
- `test-harness` is an implementation detail — de-emphasize in docs. The harness internals are intended to become a standalone library.

## Migration

### Files created

- `tests/conftest.py`
- `tests/skills/conftest.py`
- `tests/core/conftest.py`
- `tests/support/harness/matchers.py`
- `tests/support/harness/reporter.py` (rewritten as pytest plugin)
- 14 test files under `tests/skills/`
- 2 test files under `tests/core/`
- Harness unit tests: `tests/support/harness/tests/test_matchers.py`, `test_reporter.py`

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
