# Harness Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Code-quality sweep of the harness — ruff config, tightened imports, clearer error messages, JSON schema validation, reporter exit-code tests, skill-triggers negative cases, a sharper prompt-engineer assertion, docs update, and a `make test-unit` target.

**Architecture:** Batch of independent small improvements. No single cross-cutting refactor. Each task is self-contained and can be committed separately.

**Tech Stack:** Python 3.12+, pytest, ruff, jsonschema, make.

**Source:** `references/plans/2026-04-07-eval-harness-review-followups.md` items S1, S3, S4, S5, S6, S7, S8.

**Depends on:** Plans 01–05 should land first so the harness is structurally stable before polishing.

---

## Task 1: Add ruff config and fix lint

**Files:**
- Modify: `pyproject.toml` (or create if absent)
- Modify: harness files as needed

- [ ] **Step 1: Check whether pyproject.toml exists**

Run: `ls pyproject.toml 2>/dev/null && echo present || echo absent`

- [ ] **Step 2: Add or extend `[tool.ruff]` block**

If `pyproject.toml` exists, append (or merge with existing sections):

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]  # line length handled by formatter
```

If it does not exist, create it with just that block plus a minimal `[project]` stub if the repo doesn't already get Python tooling from somewhere else. Use `uv run ruff --version` first to confirm ruff is available; if not, add it: `uv add --dev ruff`.

- [ ] **Step 3: Run ruff on the harness**

Run: `uv run ruff check tests/support/harness`
Expected: prints a list of issues (import order, unused imports, etc.).

- [ ] **Step 4: Auto-fix what's safe**

Run: `uv run ruff check tests/support/harness --fix`

- [ ] **Step 5: Hand-fix remaining issues**

Specifically resolve these known items from the review (S1):
- `tests/support/harness/runner.py` — move `from claude_agent_sdk import ...` out of `run_claude` to module level (unless it causes import-time side effects; if it does, leave and add `# noqa: PLC0415` with a comment).
- `tests/support/harness/runner.py` — `run_codex` / `run_gemini` accept `*args, **kwargs` and raise `NotImplementedError`. Delete both stub functions per YAGNI.
- `tests/support/harness/orchestrator.py` — `import shutil` should be module-level (plan 01 already handled this if it landed; verify).
- `tests/support/harness/grader.py` — leave the manual JSON fence-stripping fallback in place as a safety net, but extract to a `_parse_grader_fallback(raw: str) -> dict` helper and cover with one unit test. (Fallback code is in the pre-plan-02 `grade()` — after plan 02 it's in `_grade_text_llm`.)

- [ ] **Step 6: Run ruff again**

Run: `uv run ruff check tests/support/harness`
Expected: no issues remaining.

- [ ] **Step 7: Run the harness tests**

Run: `uv run pytest tests/support -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml tests/support/harness
git commit -m "chore(harness): add ruff config and fix lint"
```

---

## Task 2: Improve discovery error messages for missing keys

**Files:**
- Modify: `tests/support/harness/discovery.py`
- Test: `tests/support/harness/test_discovery.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/support/harness/test_discovery.py`:

```python
def test_missing_name_raises_clear_error(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({"evals": [{"id": "c1", "turns": ["hi"]}]}))
    with pytest.raises(ValueError, match="missing 'name'"):
        load_eval_file(f, kind="skill")


def test_missing_evals_raises_clear_error(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({"name": "demo"}))
    with pytest.raises(ValueError, match="missing 'evals'"):
        load_eval_file(f, kind="skill")
```

- [ ] **Step 2: Run, verify they fail**

Run: `uv run pytest tests/support/harness/test_discovery.py -k "missing_name or missing_evals" -v`
Expected: FAIL with `KeyError` not `ValueError`.

- [ ] **Step 3: Add key validation in `load_eval_file`**

At the top of `load_eval_file` after `data = json.loads(...)`:

```python
    if "name" not in data:
        raise ValueError(f"{path}: missing 'name' at top level.")
    if "evals" not in data:
        raise ValueError(f"{path}: missing 'evals' at top level (should be a list of cases).")
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/discovery.py tests/support/harness/test_discovery.py
git commit -m "feat(harness): clearer errors for missing eval file keys"
```

---

## Task 3: Add JSON schema validation for eval files

**Files:**
- Create: `tests/support/harness/eval.schema.json`
- Modify: `tests/support/harness/discovery.py`
- Test: `tests/support/harness/test_discovery.py`

- [ ] **Step 1: Write the schema**

Create `tests/support/harness/eval.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["name", "evals"],
  "properties": {
    "name": {"type": "string", "minLength": 1},
    "shared_assertions": {
      "type": "array",
      "items": {"$ref": "#/$defs/assertion"}
    },
    "evals": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["id", "turns"],
        "properties": {
          "id": {"type": "string", "minLength": 1},
          "turns": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string"}
          },
          "files": {"type": "array", "items": {"type": "string"}},
          "assertions": {"type": "array", "items": {"$ref": "#/$defs/assertion"}},
          "use_shared_assertions": {"type": "boolean"},
          "grader_model": {"type": "string"},
          "grader_input_limit": {"type": "integer", "minimum": 1000},
          "cleanup": {"type": "array", "items": {"type": "string"}}
        },
        "additionalProperties": false
      }
    }
  },
  "additionalProperties": false,
  "$defs": {
    "assertion": {
      "type": "object",
      "oneOf": [
        {"required": ["text"], "properties": {"text": {"type": "string", "minLength": 1}}, "additionalProperties": false},
        {"required": ["tool_called"], "properties": {"tool_called": {"type": "string", "minLength": 1}}, "additionalProperties": false},
        {"required": ["tool_not_called"], "properties": {"tool_not_called": {"type": "string", "minLength": 1}}, "additionalProperties": false},
        {"required": ["skill_invoked"], "properties": {"skill_invoked": {"type": "string", "minLength": 1}}, "additionalProperties": false}
      ]
    }
  }
}
```

- [ ] **Step 2: Wire schema validation into discovery**

Check if `jsonschema` is installed: `uv run python -c "import jsonschema; print(jsonschema.__version__)"`. If not: `uv add --dev jsonschema`.

Then in `tests/support/harness/discovery.py`, add at module level:

```python
_SCHEMA_PATH = Path(__file__).parent / "eval.schema.json"
_SCHEMA = None


def _get_schema() -> dict:
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = json.loads(_SCHEMA_PATH.read_text())
    return _SCHEMA
```

Inside `load_eval_file`, right after `data = json.loads(path.read_text())`:

```python
    from jsonschema import validate, ValidationError
    try:
        validate(instance=data, schema=_get_schema())
    except ValidationError as e:
        raise ValueError(f"{path}: schema validation failed: {e.message} (at {list(e.absolute_path)})") from e
```

- [ ] **Step 3: Write a failing test for schema validation**

Add to `test_discovery.py`:

```python
def test_schema_rejects_unknown_top_level_key(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({
        "name": "demo",
        "evals": [{"id": "c1", "turns": ["hi"]}],
        "random_typo_key": 42,
    }))
    with pytest.raises(ValueError, match="schema validation failed"):
        load_eval_file(f, kind="skill")


def test_schema_rejects_assertion_with_multiple_keys(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({
        "name": "demo",
        "evals": [{
            "id": "c1",
            "turns": ["hi"],
            "assertions": [{"text": "x", "tool_called": "y"}],
        }],
    }))
    with pytest.raises(ValueError, match="schema validation failed"):
        load_eval_file(f, kind="skill")
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: all PASS. Also confirm existing real eval files still load:

```bash
uv run python -c "from pathlib import Path; from tests.support.harness.discovery import discover_suites; print([s.name for s in discover_suites(Path('tests'))])"
```
Expected: prints all 6 suites without error. If any suite fails validation, that is a latent schema mismatch — fix either the eval JSON (preferred) or loosen the schema.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/eval.schema.json tests/support/harness/discovery.py tests/support/harness/test_discovery.py pyproject.toml
git commit -m "feat(harness): validate eval files against JSON schema"
```

---

## Task 4: Strengthen reporter exit-code tests

**Files:**
- Modify: `tests/support/harness/test_reporter.py`

- [ ] **Step 1: Read the existing test file to see what's there**

Run: `uv run pytest tests/support/harness/test_reporter.py -v --collect-only`

- [ ] **Step 2: Add exit-code tests**

Append to `tests/support/harness/test_reporter.py`:

```python
from tests.support.harness.reporter import DotsReporter, CaseResult, _print_summary
from tests.support.harness.models import Grading, RunPlan, EvalCase
from tests.support.harness.runner import RunResult


def _make_result(
    variant="with_skill",
    suite_kind="skill",
    passed=1, failed=0, exit_code=0,
):
    case = EvalCase(id="c1", turns=["hi"])
    plan = RunPlan(
        suite_name="demo", suite_kind=suite_kind, case_id="c1",
        variant=variant, turns=["hi"], context_paths=[], case=case,
    )
    run = RunResult(
        stdout="", files_written={}, input_tokens=0, output_tokens=0,
        duration_s=0.0, exit_code=exit_code, tool_trace=[], turn_count=1,
    )
    exps = [{"text": f"e{i}", "passed": True, "evidence": "ok"} for i in range(passed)]
    exps += [{"text": f"f{i}", "passed": False, "evidence": "no"} for i in range(failed)]
    return CaseResult(plan=plan, run=run, grading=Grading.from_expectations(exps))


def test_all_pass_returns_0(capsys):
    assert _print_summary([_make_result(passed=3)], verbose=False) == 0


def test_failed_assertion_returns_1(capsys):
    assert _print_summary([_make_result(passed=1, failed=1)], verbose=False) == 1


def test_run_error_returns_1(capsys):
    assert _print_summary([_make_result(exit_code=1)], verbose=False) == 1


def test_baseline_failure_does_not_fail_run(capsys):
    # A skill baseline failing is expected — it should not flip exit code.
    assert _print_summary(
        [_make_result(variant="baseline", passed=0, failed=3)],
        verbose=False,
    ) == 0


def test_core_failure_returns_1(capsys):
    assert _print_summary(
        [_make_result(suite_kind="core", variant="run", failed=1)],
        verbose=False,
    ) == 1
```

- [ ] **Step 3: Run them**

Run: `uv run pytest tests/support/harness/test_reporter.py -v`
Expected: all PASS. If the `baseline failure` test fails, inspect `_print_summary` — the current exit-code logic only flips on `with_skill` variants, so baselines should already pass through. If the test reveals a bug, fix the logic and re-run.

- [ ] **Step 4: Commit**

```bash
git add tests/support/harness/test_reporter.py
git commit -m "test(reporter): cover exit-code logic for all result types"
```

---

## Task 5: Add negative skill-triggers cases

**Files:**
- Modify: `tests/core/skill-triggers.json`

- [ ] **Step 1: Append negative cases**

Add to the `evals` array in `tests/core/skill-triggers.json`:

```json
    {
      "id": "no-skill-on-trivia",
      "turns": ["what is 2 + 2?"],
      "files": [],
      "assertions": [
        {"tool_not_called": "Skill"},
        {"text": "Output answers the arithmetic question directly"}
      ]
    },
    {
      "id": "no-ghostwrite-on-fresh-draft",
      "turns": [
        "Write me a brand new 200-word blog post about why Rust's borrow checker is good for beginners. This is a fresh post — I have no source content for you to rewrite."
      ],
      "files": [],
      "assertions": [
        {"skill_invoked": "ghostwrite"},
        {"tool_not_called": "Skill"},
        {"text": "The ghostwrite skill was NOT invoked (it is a rewriter, not a drafter)"}
      ]
    }
```

**Wait:** the second case asserts both `skill_invoked: ghostwrite` (which is PASS if ghostwrite fires) and `tool_not_called: Skill` (which is PASS if no Skill tool fires at all). These contradict. Fix: the intent is to confirm ghostwrite did NOT fire. Use only the negative assertion. Correct version:

```json
    {
      "id": "no-ghostwrite-on-fresh-draft",
      "turns": [
        "Write me a brand new 200-word blog post about why Rust's borrow checker is good for beginners. This is a fresh post — I have no source content for you to rewrite."
      ],
      "files": [],
      "assertions": [
        {"text": "The ghostwrite skill did NOT fire on this turn — check the TOOL TRACE for any Skill tool invocation with skill containing 'ghostwrite'"},
        {"text": "The response either produces the draft directly or declines, but does not route through a rewriter skill"}
      ]
    }
```

(We can't easily express "no Skill tool call with skill=ghostwrite" deterministically today — `tool_not_called: Skill` would disallow *any* Skill use, and the model might legitimately fire a different skill. A text assertion against the tool trace is acceptable here.)

Use that corrected version for `no-ghostwrite-on-fresh-draft`. The `no-skill-on-trivia` case is fine as written.

- [ ] **Step 2: Run the suite**

Run: `uv run python -m tests.support.harness skill-triggers`
Expected: 6 cases total. Both negatives complete. If the model routes "2+2?" to a skill, that's a legitimate false-positive finding.

- [ ] **Step 3: Commit**

```bash
git add tests/core/skill-triggers.json
git commit -m "test(skill-triggers): add negative cases for trivia and fresh drafts"
```

---

## Task 6: Sharpen `prompt-engineer/vague-summarization-request` assertion

**Files:**
- Modify: `tests/skills/prompt-engineer/evals.json`

- [ ] **Step 1: Edit the assertion**

In `tests/skills/prompt-engineer/evals.json`, in the `vague-summarization-request` case, replace:

```json
        {
          "text": "Questions are presented one at a time, not as a numbered list of 5+ questions"
        }
```

with:

```json
        {
          "text": "Output contains at most two question marks total (one-at-a-time behavior, not a bulk list)"
        }
```

- [ ] **Step 2: Run the suite**

Run: `uv run python -m tests.support.harness prompt-engineer --no-baseline`
Expected: 3 cases run. The sharper assertion is graded reliably (grader counts punctuation).

- [ ] **Step 3: Commit**

```bash
git add tests/skills/prompt-engineer/evals.json
git commit -m "test(prompt-engineer): sharpen one-at-a-time assertion to count question marks"
```

---

## Task 7: Add `make test-unit` target

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Read the current Makefile**

Run: `cat Makefile` (or use Read if you prefer)

- [ ] **Step 2: Add the `test-unit` target**

Append to `Makefile`:

```make
.PHONY: test-unit
test-unit:
	uv run pytest tests/support -v
```

- [ ] **Step 3: Verify it works**

Run: `make test-unit`
Expected: runs all harness unit tests, reports PASS.

- [ ] **Step 4: Commit**

```bash
git add Makefile
git commit -m "chore: add make test-unit target for harness pytest"
```

---

## Task 8: Update docs/evals.md

**Files:**
- Modify: `docs/evals.md`

Capture the new capabilities so future eval authors know they exist: deterministic assertion types, shared_assertions, grader_input_limit, cleanup safety rules, and the static-multi-turn caveat.

- [ ] **Step 1: Add a "Assertion types" section**

After the "Eval file format" section in `docs/evals.md`, insert:

````markdown
## Assertion types

Assertions are graded in two ways depending on their shape.

**Text assertions** (default) go to an LLM judge:
```json
{"text": "Output contains a '## TL;DR' section"}
```

**Deterministic assertions** are graded in Python against the tool trace — faster, cheaper, no LLM variance:
```json
{"tool_called": "scrape_as_markdown"}
{"tool_not_called": "WebFetch"}
{"skill_invoked": "ghostwrite"}
```

Use deterministic assertions for any observable fact about tool use. Reserve text assertions for content and behavior.

## Shared assertions

Cases in the same suite often share structural assertions (e.g. every summarize case wants the same H1/TL;DR/Cliff Notes format). Hoist them to the suite level:

```json
{
  "name": "summarize",
  "shared_assertions": [
    {"text": "Output contains an H1 title"},
    {"text": "Output contains a '## TL;DR' section"}
  ],
  "evals": [
    {"id": "c1", "turns": ["..."], "assertions": [{"text": "..."}]}
  ]
}
```

Shared assertions are prepended to each case's own `assertions`. A case can opt out with `"use_shared_assertions": false`.

## Grader input limits

Long multi-turn runs produce huge grader prompts. Defaults: 40,000 chars of stdout, 10,000 chars per file, last 50 tool trace entries. Override per case with `"grader_input_limit": 80000` (scales all three).

## Cleanup safety

`cleanup` globs must be relative paths under `references/specs/` or `tmp/`. Absolute paths, `..` segments, and other roots are rejected at load time.

## Writing good assertions

- **Prefer testable, observable properties.** "Output contains `## TL;DR`" is gradable; "output is well-structured" is not.
- **Avoid surface-only checks** (character counts, backtick counts, exact whitespace) unless they are load-bearing.
- **Anchor at least half of assertions in content, not form.** A case that only grades headings can pass with a nonsense body.
- **Multi-turn replies are static.** If the script's turn 3 reply is written assuming turn 2 asks a specific question and the model asks a different one, the reply is a non-sequitur. Keep scripted replies broad, or split the case into single-turn variants (one for process, one for content).
````

- [ ] **Step 2: Verify the doc renders reasonably**

Read the updated file:

```bash
head -200 docs/evals.md
```

Confirm no obvious formatting errors.

- [ ] **Step 3: Commit**

```bash
git add docs/evals.md
git commit -m "docs(evals): document deterministic assertions, shared sets, limits"
```

---

## Verification

- [ ] `uv run ruff check tests/support/harness` — clean
- [ ] `make test-unit` — all PASS
- [ ] `make test` — full eval suite runs (may have legitimate model-miss failures from earlier plans; those are findings, not regressions)
- [ ] `docs/evals.md` has sections for assertion types, shared assertions, grader limits, cleanup safety, and writing guidance

## Out of scope

- Changing the grader model
- Codex / Gemini runners
- Restructuring `tests/` layout
