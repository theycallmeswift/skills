# Scope Split + Grader Truncation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** (1) Split scope's `github-webhook-slack` into a lightweight process case and a heavy content case so each tests one thing well, and (2) truncate grader prompt inputs so long multi-turn runs don't balloon grader cost/latency.

**Architecture:** For the split: add a new short `asks-one-question-at-a-time` case with a single turn that asserts the skill asks one question before the user answers, and keep `github-webhook-slack` as the long content case (now with assertions from plan 04). For grader truncation: add a `_truncate_tail` helper in `grader.py` that keeps the last N characters of stdout / file contents and the last N entries of `tool_trace`, with per-case override via `grader_input_limit`.

**Tech Stack:** Python 3.12+, pytest, JSON.

**Source:** `references/plans/2026-04-07-eval-harness-review-followups.md` items I2 (option b) and I4.

**Depends on:** Plan 04 (eval content gaps) should land first so the content assertions already exist on `github-webhook-slack`.

---

## Context the implementer needs

- Multi-turn cases in the harness use static scripted replies — if the agent asks a different question than expected, the scripted answer is a non-sequitur. This is acknowledged in `docs/evals.md` lines 69–70. Rather than fix it (would require a mid-run LLM), the plan is to split the case so the "one-question-at-a-time" property is tested with a single-turn assertion (no scripted replies needed) and the "spec content" property is tested with one mega-turn that pre-answers everything.
- `grader.py::_build_prompt` interpolates `run.stdout`, every file in `run.files_written`, and the full `run.tool_trace` into one prompt string. Long scope runs produce 30k+ chars of stdout. Haiku will accept it but cost/latency balloons.
- `EvalCase` today has no per-case grader input limit. We'll add an optional `grader_input_limit: int` field (chars) that overrides the default.

---

## Task 1: Add `asks-one-question-at-a-time` scope case

**Files:**
- Modify: `tests/skills/scope/evals.json`

This case sends one vague turn and asserts the skill asks a single clarifying question without listing a bunch of them and without proposing a design yet. It doesn't need multi-turn scripting.

- [ ] **Step 1: Append the case**

Add to the `evals` array in `tests/skills/scope/evals.json` (after `github-webhook-slack` or at the end):

```json
    {
      "id": "asks-one-question-at-a-time",
      "turns": [
        "Scope a GitHub webhook system for MechaSwift that listens for PR events and posts summaries to Slack."
      ],
      "files": [],
      "assertions": [
        {"text": "Output contains exactly one question, or at most two questions, on this turn"},
        {"text": "Output does NOT present a numbered or bulleted list of 3+ clarifying questions at once"},
        {"text": "Output does NOT propose a design or approach on this turn (waits for answers first)"},
        {"text": "Output does NOT write a spec file on this turn"},
        {"text": "Output does NOT create any implementation code or project scaffolding"}
      ]
    }
```

- [ ] **Step 2: Run the suite**

Run: `uv run python -m tests.support.harness scope --no-baseline`
Expected: 4 cases run. The new case has 5 assertions, all focused on the "one question at a time" property.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/scope/evals.json
git commit -m "test(scope): add asks-one-question-at-a-time case"
```

---

## Task 2: Add `grader_input_limit` field to EvalCase

**Files:**
- Modify: `tests/support/harness/models.py`
- Modify: `tests/support/harness/discovery.py`
- Test: `tests/support/harness/test_discovery.py`

- [ ] **Step 1: Write failing test**

Add to `tests/support/harness/test_discovery.py`:

```python
def test_grader_input_limit_is_loaded(tmp_path):
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({
        "name": "demo",
        "evals": [
            {
                "id": "c1",
                "turns": ["hi"],
                "grader_input_limit": 8000,
                "assertions": [{"text": "x"}],
            },
            {
                "id": "c2",
                "turns": ["hi"],
                "assertions": [{"text": "x"}],
            },
        ],
    }))
    suite = load_eval_file(f, kind="skill")
    assert suite.cases[0].grader_input_limit == 8000
    assert suite.cases[1].grader_input_limit is None
```

- [ ] **Step 2: Run it, verify it fails**

Run: `uv run pytest tests/support/harness/test_discovery.py::test_grader_input_limit_is_loaded -v`
Expected: FAIL (field doesn't exist on `EvalCase`).

- [ ] **Step 3: Add the field to `EvalCase`**

In `tests/support/harness/models.py`, add to the `EvalCase` dataclass:

```python
    grader_input_limit: int | None = None
```

Place it after the existing `grader_model: str | None = None` field.

- [ ] **Step 4: Load the field in `discovery.py`**

In `tests/support/harness/discovery.py`, in the `EvalCase(...)` construction inside `load_eval_file`, add:

```python
            grader_input_limit=c.get("grader_input_limit"),
```

- [ ] **Step 5: Run the test**

Run: `uv run pytest tests/support/harness/test_discovery.py::test_grader_input_limit_is_loaded -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/support/harness/models.py tests/support/harness/discovery.py tests/support/harness/test_discovery.py
git commit -m "feat(harness): add grader_input_limit field to EvalCase"
```

---

## Task 3: Implement grader input truncation

**Files:**
- Modify: `tests/support/harness/grader.py`
- Modify: `tests/support/harness/orchestrator.py` (pass the limit through)
- Test: `tests/support/harness/test_grader.py`

Default limit: 40,000 chars for stdout, 10,000 chars per file, and the last 50 entries of `tool_trace`. Per-case override via `grader_input_limit` scales all three proportionally (e.g. doubling the limit doubles stdout and per-file caps and trace size).

- [ ] **Step 1: Write failing tests**

Add to `tests/support/harness/test_grader.py`:

```python
from tests.support.harness.grader import _truncate_tail, _build_prompt, DEFAULT_STDOUT_LIMIT


def test_truncate_tail_keeps_end_and_adds_marker():
    s = "a" * 100
    out = _truncate_tail(s, limit=30)
    assert out.endswith("a" * 30)
    assert "truncated" in out
    assert "70" in out  # chars dropped


def test_truncate_tail_noop_when_under_limit():
    s = "short"
    assert _truncate_tail(s, limit=100) == "short"


def test_build_prompt_truncates_long_stdout():
    run = RunResult(
        stdout="x" * (DEFAULT_STDOUT_LIMIT + 5000),
        files_written={},
        input_tokens=0, output_tokens=0, duration_s=0.0,
        exit_code=0, tool_trace=[], turn_count=1,
    )
    prompt = _build_prompt(run, [{"text": "y"}], original_prompt="p", stdout_limit=DEFAULT_STDOUT_LIMIT)
    assert "truncated" in prompt
    # stdout section should be at most limit + marker overhead (~100 chars)
    assert len(prompt) < DEFAULT_STDOUT_LIMIT + 5000


def test_build_prompt_truncates_tool_trace_to_last_n():
    run = RunResult(
        stdout="x", files_written={},
        input_tokens=0, output_tokens=0, duration_s=0.0,
        exit_code=0,
        tool_trace=[{"name": f"t{i}", "input": {}, "turn": 1} for i in range(200)],
        turn_count=1,
    )
    prompt = _build_prompt(run, [{"text": "y"}], original_prompt="p", trace_limit=50)
    assert '"t199"' in prompt   # last entry present
    assert '"t0"' not in prompt  # first entry dropped
```

- [ ] **Step 2: Run them, verify they fail**

Run: `uv run pytest tests/support/harness/test_grader.py -k "truncate or build_prompt" -v`
Expected: FAIL (`_truncate_tail` doesn't exist; `_build_prompt` has no limit kwargs).

- [ ] **Step 3: Add truncation to grader.py**

In `tests/support/harness/grader.py`, add constants and helper near the top (after `DEFAULT_GRADER_MODEL`):

```python
DEFAULT_STDOUT_LIMIT = 40_000
DEFAULT_FILE_LIMIT = 10_000
DEFAULT_TRACE_LIMIT = 50


def _truncate_tail(s: str, limit: int) -> str:
    """Keep the last `limit` characters of `s`, prepending a truncation marker."""
    if len(s) <= limit:
        return s
    dropped = len(s) - limit
    return f"[... truncated {dropped} chars ...]\n{s[-limit:]}"
```

Replace `_build_prompt` with:

```python
def _build_prompt(
    run: RunResult,
    assertions: list[dict],
    original_prompt: str,
    stdout_limit: int = DEFAULT_STDOUT_LIMIT,
    file_limit: int = DEFAULT_FILE_LIMIT,
    trace_limit: int = DEFAULT_TRACE_LIMIT,
) -> str:
    stdout = _truncate_tail(run.stdout or "(empty)", stdout_limit)
    files_block = (
        "\n\n".join(
            f"--- {p} ---\n{_truncate_tail(c, file_limit)}"
            for p, c in run.files_written.items()
        )
        or "(none)"
    )
    trace = run.tool_trace[-trace_limit:] if len(run.tool_trace) > trace_limit else run.tool_trace
    trace_note = ""
    if len(run.tool_trace) > trace_limit:
        trace_note = f"[... {len(run.tool_trace) - trace_limit} earlier entries truncated ...]\n"
    return GRADER_PROMPT.format(
        original_prompt=original_prompt or "(none)",
        assertions_json=json.dumps(assertions, indent=2),
        stdout=stdout,
        files_block=files_block,
        tool_trace_json=trace_note + json.dumps(trace, indent=2),
    )
```

- [ ] **Step 4: Thread the per-case limit through `grade()` and `_grade_text_llm`**

Update `grade()` and `_grade_text_llm()` to accept an optional `input_limit` parameter. In `_grade_text_llm`, if the limit is set, scale the three defaults:

```python
async def _grade_text_llm(
    run: RunResult,
    assertions: list[dict],
    model: str | None,
    original_prompt: str,
    input_limit: int | None = None,
) -> list[dict]:
    # ... (unchanged SDK imports and options) ...
    if input_limit is None:
        prompt = _build_prompt(run, assertions, original_prompt)
    else:
        scale = input_limit / DEFAULT_STDOUT_LIMIT
        prompt = _build_prompt(
            run, assertions, original_prompt,
            stdout_limit=input_limit,
            file_limit=int(DEFAULT_FILE_LIMIT * scale),
            trace_limit=max(DEFAULT_TRACE_LIMIT, int(DEFAULT_TRACE_LIMIT * scale)),
        )
    # ... (unchanged query loop) ...
```

And update `grade()` to accept and pass through:

```python
async def grade(
    run: RunResult,
    assertions: list[dict],
    model: str | None = None,
    original_prompt: str = "",
    input_limit: int | None = None,
) -> Grading:
    if not assertions:
        return Grading.from_expectations([])

    text_assertions = [a for a in assertions if not _is_deterministic(a)]
    llm_expectations = await _grade_text_llm(
        run, text_assertions, model, original_prompt, input_limit=input_limit
    )

    llm_iter = iter(llm_expectations)
    merged: list[dict] = []
    for a in assertions:
        if _is_deterministic(a):
            merged.extend(_grade_deterministic([a], run))
        else:
            merged.append(next(llm_iter))

    return Grading.from_expectations(merged)
```

- [ ] **Step 5: Pass the limit from orchestrator**

In `tests/support/harness/orchestrator.py`, update the `grade()` call in `_run_one`:

```python
            grading = await grade(
                run,
                plan.case.assertions,
                model=plan.case.grader_model,
                original_prompt=original_prompt,
                input_limit=plan.case.grader_input_limit,
            )
```

- [ ] **Step 6: Run all grader tests**

Run: `uv run pytest tests/support/harness/test_grader.py -v`
Expected: all PASS (new truncation tests + existing deterministic tests).

- [ ] **Step 7: Run the full harness test suite**

Run: `uv run pytest tests/support -v`
Expected: all PASS.

- [ ] **Step 8: Smoke-run the scope suite**

Run: `uv run python -m tests.support.harness scope --no-baseline`
Expected: all 4 cases complete. The `github-webhook-slack` case's grader prompt is no longer unbounded — confirm by inspecting the grader's input size is capped (no exception, reasonable duration).

- [ ] **Step 9: Commit**

```bash
git add tests/support/harness/grader.py tests/support/harness/orchestrator.py tests/support/harness/test_grader.py
git commit -m "feat(harness): truncate grader prompt inputs with per-case override"
```

---

## Verification

- [ ] `uv run pytest tests/support -v` — all green
- [ ] `uv run python -m tests.support.harness scope --no-baseline` — 4 cases, `asks-one-question-at-a-time` present
- [ ] Inspect a `github-webhook-slack` run's grading.json: all 13 assertions graded; duration should not be dominated by a huge grader prompt
- [ ] If an eval legitimately needs more than 40k chars of stdout (rare), add `"grader_input_limit": 120000` to that case in its JSON — no plan 06 work required

## Out of scope for this plan

- Mid-run dynamic multi-turn replies (I2 option a — explicitly deferred in the review doc)
- Harness code-quality sweep (plan 06)
