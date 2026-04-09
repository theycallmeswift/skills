# Eval Harness Plan B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the eval harness into a fast `make test` (deterministic, <90s) and a deep `make eval` (rubric-graded, ~2min). Replace most text assertions with 19 deterministic primitives, move quality checks into per-skill `RUBRIC.md` files, and flatten the tests tree.

**Architecture:** All changes live inside `tests/support/harness/`. Phases 1–4 add new code without breaking anything (additive). Phase 5 flattens the tests tree and migrates each suite one at a time. Phase 6 deletes now-dead legacy code. Phase 7 rewrites docs.

**Tech Stack:** Python 3.12, `claude-agent-sdk`, `jsonschema`, `pytest`, Rich, the existing harness.

**Source spec:** `references/specs/2026-04-08-eval-harness-plan-b-design.md`

**Branch:** `eval-harness-refactor` (already created, spec already committed)

---

## File Structure

**New files:**
- `tests/support/harness/rubric.py` — RUBRIC.md parser
- `tests/support/harness/tests/test_rubric.py` — parser unit tests
- `skills/ghostwrite/RUBRIC.md`
- `skills/summarize/RUBRIC.md`
- `skills/scope/RUBRIC.md`
- `skills/prompt-engineer/RUBRIC.md`
- `tests/ghostwrite.json` (moved from `tests/skills/ghostwrite/evals.json`, then rewritten)
- `tests/summarize.json` (moved)
- `tests/scope.json` (moved)
- `tests/prompt-engineer.json` (moved)
- `tests/skill-triggers.json` (moved from `tests/core/`)
- `tests/no-ai-attribution.json` (moved from `tests/core/`)
- `tests/fixtures/test-paper.pdf` (moved from `tests/skills/summarize/`)
- `skills/ghostwrite/lint_test.py` (moved from `tests/skills/ghostwrite/test_lint.py`)
- `skills/summarize/lint_test.py` (moved from `tests/skills/summarize/test_lint.py`)

**Modified files:**
- `tests/support/harness/grader.py` — add deterministic primitives, add `grade_rubric()`, rename `_grade_lint` → `_grade_script_name`
- `tests/support/harness/discovery.py` — flat `tests/*.json` scan with skill/core auto-detection
- `tests/support/harness/models.py` — add `tier` to `RunPlan`
- `tests/support/harness/orchestrator.py` — tier-aware rubric grading path
- `tests/support/harness/reporter.py` — fast + deep summary split, no WARN logic
- `tests/support/harness/__main__.py` — `--tier test|eval` flag
- `tests/support/harness/eval.schema.json` — accept new assertion shapes, remove dead fields
- `tests/support/harness/tests/test_grader.py` — tests for every new primitive
- `tests/support/harness/tests/test_discovery.py` — flat-scan tests
- `tests/support/harness/tests/test_reporter.py` — tier summary tests
- `Makefile` — add `eval` target
- `pyproject.toml` / `conftest.py` — pytest collection of `skills/*/lint_test.py`
- `docs/evals.md` — rewrite for new commands + vocab
- `CLAUDE.md`, `AGENTS.md` — update Commands section

**Deleted (after migration):**
- `tests/skills/` (entire subtree)
- `tests/core/` (entire subtree)

---

## Conventions

- **TDD everywhere in Phases 1–4.** Write the unit test first, run it to see it fail, implement, run it to see it pass, commit.
- **No attribution.** Commit messages never mention Claude, AI, or the harness vendor. No `Co-Authored-By` trailers.
- **Commit style.** Matches recent history: `type: short description` (e.g., `harness: add regex primitive with min/max counts`).
- **Run tests with:** `uv run pytest tests/support/harness/tests/ -v`
- **Run the eval harness with:** `uv run python -m tests.support.harness [names...]` (current flags) or later `--tier test|eval`.
- **Backward compatibility.** Through Phase 5, legacy eval files (`{"text": ...}`, `{"lint": ...}`, `shared_assertions`) must still work. Phase 6 is where they die.

---

## Phase 1 — Deterministic Assertion Vocabulary

Goal: add 14 new primitives to `grader.py`, rename `lint` → `script_name`, update the schema. All additive: old primitives still work.

### Task 1: Groundwork — source resolver + dispatch refactor

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/tests/test_grader.py`

The goal is to introduce a helper that resolves the `on` field (where to look: `stdout`, `final_message`, or `files.<glob>`) and a dispatch table so later tasks just add one entry per primitive.

- [ ] **Step 1: Write the failing test for `_resolve_source`**

Add to `tests/support/harness/tests/test_grader.py`:

```python
from tests.support.harness.grader import _resolve_source


def _run(stdout="", final_message="", files_written=None):
    return RunResult(
        stdout=stdout,
        files_written=files_written or {},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.0,
        exit_code=0,
        tool_trace=[],
        turn_count=1,
        final_message=final_message,
    )


def test_resolve_source_defaults_to_final_message():
    run = _run(stdout="STDOUT", final_message="FINAL")
    assert _resolve_source(run, None) == ["FINAL"]


def test_resolve_source_stdout():
    run = _run(stdout="STDOUT", final_message="FINAL")
    assert _resolve_source(run, "stdout") == ["STDOUT"]


def test_resolve_source_final_message_explicit():
    run = _run(stdout="STDOUT", final_message="FINAL")
    assert _resolve_source(run, "final_message") == ["FINAL"]


def test_resolve_source_files_glob_returns_all_matches():
    run = _run(files_written={"a.md": "alpha", "b.md": "beta", "c.txt": "gamma"})
    got = _resolve_source(run, "files.*.md")
    assert sorted(got) == ["alpha", "beta"]


def test_resolve_source_files_glob_no_matches_returns_empty():
    run = _run(files_written={"a.md": "alpha"})
    assert _resolve_source(run, "files.*.txt") == []
```

- [ ] **Step 2: Run test to confirm failure**

```
uv run pytest tests/support/harness/tests/test_grader.py::test_resolve_source_defaults_to_final_message -v
```

Expected: `ImportError: cannot import name '_resolve_source'`.

- [ ] **Step 3: Implement `_resolve_source`**

Add to `tests/support/harness/grader.py` (near the top, after the constants):

```python
import fnmatch


def _resolve_source(run: RunResult, on: str | None) -> list[str]:
    """Return the list of text sources to run an assertion against.

    - None or "final_message": the final assistant text (what the user sees)
    - "stdout": the concatenated run output
    - "files.<glob>": contents of every written file whose relative path matches the glob
    """
    if on is None or on == "final_message":
        return [getattr(run, "final_message", "") or ""]
    if on == "stdout":
        return [run.stdout or ""]
    if on.startswith("files."):
        pattern = on[len("files."):]
        return [
            content
            for path, content in run.files_written.items()
            if fnmatch.fnmatch(path, pattern)
        ]
    raise ValueError(f"unknown `on` target: {on!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

```
uv run pytest tests/support/harness/tests/test_grader.py -v -k resolve_source
```

Expected: all 5 tests pass.

- [ ] **Step 5: Introduce the primitive dispatch table**

Refactor `_grade_deterministic` so each primitive is a small function with signature `(assertion: dict, run: RunResult) -> dict`. This is the pattern every subsequent task will extend.

```python
from typing import Callable

_PrimitiveFn = Callable[[dict, RunResult], dict]

_PRIMITIVES: dict[str, _PrimitiveFn] = {}


def _primitive(key: str) -> Callable[[_PrimitiveFn], _PrimitiveFn]:
    def decorator(fn: _PrimitiveFn) -> _PrimitiveFn:
        _PRIMITIVES[key] = fn
        return fn
    return decorator


@_primitive("tool_called")
def _grade_tool_called(a: dict, run: RunResult) -> dict:
    needle = a["tool_called"]
    hit = _match_tool(run.tool_trace, needle)
    if hit is not None:
        return {
            "text": f"tool_called: {needle}",
            "passed": True,
            "evidence": f"matched tool '{hit['name']}' on turn {hit.get('turn', '?')}",
        }
    return {
        "text": f"tool_called: {needle}",
        "passed": False,
        "evidence": f"no matching tool in trace ({len(run.tool_trace)} entries)",
    }


@_primitive("tool_not_called")
def _grade_tool_not_called(a: dict, run: RunResult) -> dict:
    needle = a["tool_not_called"]
    hit = _match_tool(run.tool_trace, needle)
    if hit is None:
        return {
            "text": f"tool_not_called: {needle}",
            "passed": True,
            "evidence": f"no matching tool in trace ({len(run.tool_trace)} entries)",
        }
    return {
        "text": f"tool_not_called: {needle}",
        "passed": False,
        "evidence": f"found '{hit['name']}' on turn {hit.get('turn', '?')}",
    }


@_primitive("skill_invoked")
def _grade_skill_invoked(a: dict, run: RunResult) -> dict:
    skill = a["skill_invoked"]
    hit = _match_skill_invocation(run.tool_trace, skill)
    if hit is not None:
        return {
            "text": f"skill_invoked: {skill}",
            "passed": True,
            "evidence": f"Skill tool fired with skill='{hit['input'].get('skill', '?')}' on turn {hit.get('turn', '?')}",
        }
    has_any_skill = any(e.get("name") == "Skill" for e in run.tool_trace)
    if has_any_skill:
        fired = [
            e.get("input", {}).get("skill", "?")
            for e in run.tool_trace
            if e.get("name") == "Skill"
        ]
        evidence = f"Skill tool fired but with different skills: {fired}"
    else:
        evidence = "no Skill tool invocations in trace"
    return {"text": f"skill_invoked: {skill}", "passed": False, "evidence": evidence}


@_primitive("lint")  # TEMPORARY alias until Task 9 renames to script_name
def _grade_lint_primitive(a: dict, run: RunResult) -> dict:
    return _grade_lint(a["lint"], run)


def _grade_deterministic(assertions: list[dict], run: RunResult) -> list[dict]:
    out: list[dict] = []
    for a in assertions:
        for key, fn in _PRIMITIVES.items():
            if key in a:
                out.append(fn(a, run))
                break
    return out


_DETERMINISTIC_KEYS = tuple(_PRIMITIVES.keys())


def _is_deterministic(assertion: dict) -> bool:
    return any(k in assertion for k in _PRIMITIVES)
```

Delete the old long `if/elif` chain from `_grade_deterministic`. Keep `_grade_lint`, `_match_tool`, `_match_skill_invocation` unchanged — the primitive functions call them.

- [ ] **Step 6: Run the full grader test suite**

```
uv run pytest tests/support/harness/tests/test_grader.py -v
```

Expected: every existing test still passes (tool_called, tool_not_called, skill_invoked, lint, merge ordering). The refactor must be behavior-preserving.

- [ ] **Step 7: Commit**

```bash
git add tests/support/harness/grader.py tests/support/harness/tests/test_grader.py
git commit -m "harness: introduce primitive dispatch + source resolver"
```

---

### Task 2: Content primitives — `regex` and `not_regex`

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/tests/test_grader.py`

`regex` is the meatiest content primitive because it supports `min` / `max` counts. `not_regex` is a thin wrapper (`max: 0`).

- [ ] **Step 1: Write failing tests**

```python
def test_regex_passes_on_single_match():
    run = _run(final_message="Hey, Sarah -- welcome")
    exps = _grade_deterministic([{"regex": r"^Hey, Sarah --"}], run)
    assert exps[0]["passed"] is True
    assert exps[0]["text"].startswith("regex:")


def test_regex_fails_when_absent():
    run = _run(final_message="Hello world")
    exps = _grade_deterministic([{"regex": r"^Hey"}], run)
    assert exps[0]["passed"] is False


def test_regex_min_count_enforced():
    run = _run(final_message="one? two?")
    exps = _grade_deterministic([{"regex": r"\?", "min": 3}], run)
    assert exps[0]["passed"] is False
    assert "2" in exps[0]["evidence"]


def test_regex_max_count_enforced():
    run = _run(final_message="one? two? three?")
    exps = _grade_deterministic([{"regex": r"\?", "max": 2}], run)
    assert exps[0]["passed"] is False


def test_regex_min_and_max_inclusive():
    run = _run(final_message="a? b?")
    exps = _grade_deterministic([{"regex": r"\?", "min": 2, "max": 2}], run)
    assert exps[0]["passed"] is True


def test_regex_respects_on_field_stdout():
    run = _run(stdout="VISIBLE", final_message="HIDDEN")
    exps = _grade_deterministic(
        [{"regex": "VISIBLE", "on": "stdout"}], run
    )
    assert exps[0]["passed"] is True


def test_not_regex_passes_when_absent():
    run = _run(final_message="clean output")
    exps = _grade_deterministic([{"not_regex": "forbidden"}], run)
    assert exps[0]["passed"] is True


def test_not_regex_fails_when_present():
    run = _run(final_message="forbidden word here")
    exps = _grade_deterministic([{"not_regex": "forbidden"}], run)
    assert exps[0]["passed"] is False
```

- [ ] **Step 2: Run tests to confirm failure**

```
uv run pytest tests/support/harness/tests/test_grader.py -v -k "regex"
```

Expected: all 8 tests fail (primitive not registered).

- [ ] **Step 3: Implement `regex` and `not_regex` primitives**

Add to `grader.py`:

```python
import re


@_primitive("regex")
def _grade_regex(a: dict, run: RunResult) -> dict:
    pattern = a["regex"]
    min_n = a.get("min", 1)
    max_n = a.get("max")  # None = no upper bound
    sources = _resolve_source(run, a.get("on"))
    count = sum(len(re.findall(pattern, s)) for s in sources)
    passed = count >= min_n and (max_n is None or count <= max_n)
    bound = f"min={min_n}" + (f", max={max_n}" if max_n is not None else "")
    return {
        "text": f"regex: {pattern} ({bound})",
        "passed": passed,
        "evidence": f"found {count} match(es) across {len(sources)} source(s)",
    }


@_primitive("not_regex")
def _grade_not_regex(a: dict, run: RunResult) -> dict:
    # Shorthand for regex with max=0.
    return _grade_regex(
        {"regex": a["not_regex"], "min": 0, "max": 0, "on": a.get("on")}, run
    )
```

- [ ] **Step 4: Run tests**

```
uv run pytest tests/support/harness/tests/test_grader.py -v -k "regex"
```

Expected: 8/8 pass.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/grader.py tests/support/harness/tests/test_grader.py
git commit -m "harness: add regex and not_regex primitives with count bounds"
```

---

### Task 3: Content primitives — `contains`, `contains_all`, `not_contains`

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/tests/test_grader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_contains_literal_substring_passes():
    run = _run(final_message="the answer is 42")
    exps = _grade_deterministic([{"contains": "42"}], run)
    assert exps[0]["passed"] is True


def test_contains_fails_when_absent():
    run = _run(final_message="hello")
    exps = _grade_deterministic([{"contains": "world"}], run)
    assert exps[0]["passed"] is False


def test_contains_all_requires_every_literal():
    run = _run(final_message="450 fellows, 30% up, 92% rec rate")
    exps = _grade_deterministic(
        [{"contains_all": ["450", "30%", "92%"]}], run
    )
    assert exps[0]["passed"] is True


def test_contains_all_fails_on_missing_item():
    run = _run(final_message="450 fellows, 30% up")
    exps = _grade_deterministic(
        [{"contains_all": ["450", "30%", "92%"]}], run
    )
    assert exps[0]["passed"] is False
    assert "92%" in exps[0]["evidence"]


def test_not_contains_passes_when_absent():
    run = _run(final_message="clean")
    exps = _grade_deterministic([{"not_contains": "dirty"}], run)
    assert exps[0]["passed"] is True


def test_not_contains_fails_when_present():
    run = _run(final_message="dirty string")
    exps = _grade_deterministic([{"not_contains": "dirty"}], run)
    assert exps[0]["passed"] is False
```

- [ ] **Step 2: Run to confirm failure**

```
uv run pytest tests/support/harness/tests/test_grader.py -v -k "contains"
```

- [ ] **Step 3: Implement**

Add to `grader.py`:

```python
@_primitive("contains")
def _grade_contains(a: dict, run: RunResult) -> dict:
    needle = a["contains"]
    sources = _resolve_source(run, a.get("on"))
    hit = any(needle in s for s in sources)
    return {
        "text": f"contains: {needle!r}",
        "passed": hit,
        "evidence": ("found literal" if hit else f"not found in {len(sources)} source(s)"),
    }


@_primitive("contains_all")
def _grade_contains_all(a: dict, run: RunResult) -> dict:
    needles = a["contains_all"]
    sources = _resolve_source(run, a.get("on"))
    haystack = "\n".join(sources)
    missing = [n for n in needles if n not in haystack]
    return {
        "text": f"contains_all: {needles}",
        "passed": not missing,
        "evidence": ("all present" if not missing else f"missing: {missing}"),
    }


@_primitive("not_contains")
def _grade_not_contains(a: dict, run: RunResult) -> dict:
    needle = a["not_contains"]
    sources = _resolve_source(run, a.get("on"))
    hit = any(needle in s for s in sources)
    return {
        "text": f"not_contains: {needle!r}",
        "passed": not hit,
        "evidence": ("literal found (should be absent)" if hit else "absent, as required"),
    }
```

- [ ] **Step 4: Run tests**

Expected: 6/6 pass.

- [ ] **Step 5: Commit**

```bash
git commit -am "harness: add contains, contains_all, not_contains primitives"
```

---

### Task 4: Shape primitives — `output_len_lte`, `output_len_gte`, `token_usage_lte`

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/tests/test_grader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_output_len_lte_passes_under_bound():
    run = _run(final_message="short")
    exps = _grade_deterministic([{"output_len_lte": 100}], run)
    assert exps[0]["passed"] is True


def test_output_len_lte_fails_over_bound():
    run = _run(final_message="x" * 200)
    exps = _grade_deterministic([{"output_len_lte": 100}], run)
    assert exps[0]["passed"] is False
    assert "200" in exps[0]["evidence"]


def test_output_len_gte_enforces_minimum():
    run = _run(final_message="short")
    exps = _grade_deterministic([{"output_len_gte": 100}], run)
    assert exps[0]["passed"] is False


def test_output_len_respects_on_stdout():
    run = _run(stdout="x" * 50, final_message="")
    exps = _grade_deterministic(
        [{"output_len_lte": 40, "on": "stdout"}], run
    )
    assert exps[0]["passed"] is False


def test_token_usage_lte_passes():
    run = _run()
    run.input_tokens = 1000
    run.output_tokens = 500
    exps = _grade_deterministic([{"token_usage_lte": 2000}], run)
    assert exps[0]["passed"] is True


def test_token_usage_lte_fails_over_cap():
    run = _run()
    run.input_tokens = 5000
    run.output_tokens = 6000
    exps = _grade_deterministic([{"token_usage_lte": 10000}], run)
    assert exps[0]["passed"] is False
    assert "11000" in exps[0]["evidence"]
```

- [ ] **Step 2: Confirm failure**

```
uv run pytest tests/support/harness/tests/test_grader.py -v -k "len or token_usage"
```

- [ ] **Step 3: Implement**

```python
@_primitive("output_len_lte")
def _grade_output_len_lte(a: dict, run: RunResult) -> dict:
    cap = a["output_len_lte"]
    sources = _resolve_source(run, a.get("on"))
    length = sum(len(s) for s in sources)
    return {
        "text": f"output_len_lte: {cap}",
        "passed": length <= cap,
        "evidence": f"length={length}",
    }


@_primitive("output_len_gte")
def _grade_output_len_gte(a: dict, run: RunResult) -> dict:
    floor = a["output_len_gte"]
    sources = _resolve_source(run, a.get("on"))
    length = sum(len(s) for s in sources)
    return {
        "text": f"output_len_gte: {floor}",
        "passed": length >= floor,
        "evidence": f"length={length}",
    }


@_primitive("token_usage_lte")
def _grade_token_usage_lte(a: dict, run: RunResult) -> dict:
    cap = a["token_usage_lte"]
    total = run.input_tokens + run.output_tokens
    return {
        "text": f"token_usage_lte: {cap}",
        "passed": total <= cap,
        "evidence": f"total_tokens={total}",
    }
```

- [ ] **Step 4: Run tests**

Expected: 6/6 pass.

- [ ] **Step 5: Commit**

```bash
git commit -am "harness: add shape primitives (output_len_lte/gte, token_usage_lte)"
```

---

### Task 5: Trace primitive — `skill_not_invoked`

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/tests/test_grader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_skill_not_invoked_passes_when_absent():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"skill_not_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is True


def test_skill_not_invoked_fails_when_skill_fired():
    run = _run_with_trace(
        [{"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1}]
    )
    exps = _grade_deterministic([{"skill_not_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False
    assert "ghostwrite" in exps[0]["evidence"]


def test_skill_not_invoked_accepts_prefixed_name():
    run = _run_with_trace(
        [{"name": "Skill", "input": {"skill": "mechaswift:ghostwrite"}, "turn": 2}]
    )
    exps = _grade_deterministic([{"skill_not_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False
```

- [ ] **Step 2: Confirm failure**

```
uv run pytest tests/support/harness/tests/test_grader.py -v -k "skill_not_invoked"
```

- [ ] **Step 3: Implement**

```python
@_primitive("skill_not_invoked")
def _grade_skill_not_invoked(a: dict, run: RunResult) -> dict:
    skill = a["skill_not_invoked"]
    hit = _match_skill_invocation(run.tool_trace, skill)
    if hit is None:
        return {
            "text": f"skill_not_invoked: {skill}",
            "passed": True,
            "evidence": f"no {skill} Skill invocation in trace",
        }
    return {
        "text": f"skill_not_invoked: {skill}",
        "passed": False,
        "evidence": f"Skill tool fired with '{hit['input'].get('skill', '?')}' on turn {hit.get('turn', '?')}",
    }
```

- [ ] **Step 4: Run tests**

Expected: 3/3 pass.

- [ ] **Step 5: Commit**

```bash
git commit -am "harness: add skill_not_invoked primitive"
```

---

### Task 6: Trace primitives — `trace_order`, `trace_count_lte`, `turn_count_lte`

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/tests/test_grader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_trace_order_passes_when_tools_in_order():
    trace = [
        {"name": "scrape_as_markdown", "input": {}, "turn": 1},
        {"name": "Bash", "input": {}, "turn": 1},
        {"name": "Write", "input": {}, "turn": 1},
    ]
    run = _run_with_trace(trace)
    exps = _grade_deterministic(
        [{"trace_order": ["scrape_as_markdown", "Write"]}], run
    )
    assert exps[0]["passed"] is True


def test_trace_order_fails_when_out_of_order():
    trace = [
        {"name": "Write", "input": {}, "turn": 1},
        {"name": "scrape_as_markdown", "input": {}, "turn": 1},
    ]
    run = _run_with_trace(trace)
    exps = _grade_deterministic(
        [{"trace_order": ["scrape_as_markdown", "Write"]}], run
    )
    assert exps[0]["passed"] is False


def test_trace_order_fails_when_missing_tool():
    trace = [{"name": "scrape_as_markdown", "input": {}, "turn": 1}]
    run = _run_with_trace(trace)
    exps = _grade_deterministic(
        [{"trace_order": ["scrape_as_markdown", "Write"]}], run
    )
    assert exps[0]["passed"] is False
    assert "Write" in exps[0]["evidence"]


def test_trace_count_lte_passes_under_cap():
    run = _run_with_trace(
        [{"name": "Bash", "input": {}, "turn": 1} for _ in range(2)]
    )
    exps = _grade_deterministic(
        [{"trace_count_lte": {"tool": "Bash", "n": 3}}], run
    )
    assert exps[0]["passed"] is True


def test_trace_count_lte_fails_over_cap():
    run = _run_with_trace(
        [{"name": "Bash", "input": {}, "turn": 1} for _ in range(5)]
    )
    exps = _grade_deterministic(
        [{"trace_count_lte": {"tool": "Bash", "n": 3}}], run
    )
    assert exps[0]["passed"] is False
    assert "5" in exps[0]["evidence"]


def test_turn_count_lte_passes():
    run = _run_with_trace([])
    run.turn_count = 1
    exps = _grade_deterministic([{"turn_count_lte": 1}], run)
    assert exps[0]["passed"] is True


def test_turn_count_lte_fails():
    run = _run_with_trace([])
    run.turn_count = 3
    exps = _grade_deterministic([{"turn_count_lte": 1}], run)
    assert exps[0]["passed"] is False
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement**

```python
@_primitive("trace_order")
def _grade_trace_order(a: dict, run: RunResult) -> dict:
    expected = a["trace_order"]
    names = [e.get("name", "") for e in run.tool_trace]
    # Match each expected tool using substring containment (like _match_tool),
    # advancing a cursor so order must be preserved. Missing expected = fail.
    cursor = 0
    missing: list[str] = []
    for needle in expected:
        found = False
        for i in range(cursor, len(names)):
            if needle in names[i]:
                cursor = i + 1
                found = True
                break
        if not found:
            missing.append(needle)
    passed = not missing
    return {
        "text": f"trace_order: {expected}",
        "passed": passed,
        "evidence": ("matched in order" if passed else f"missing or out of order: {missing}"),
    }


@_primitive("trace_count_lte")
def _grade_trace_count_lte(a: dict, run: RunResult) -> dict:
    spec = a["trace_count_lte"]
    tool = spec["tool"]
    cap = spec["n"]
    count = sum(1 for e in run.tool_trace if tool in e.get("name", ""))
    return {
        "text": f"trace_count_lte: {tool} <= {cap}",
        "passed": count <= cap,
        "evidence": f"found {count} call(s) to {tool}",
    }


@_primitive("turn_count_lte")
def _grade_turn_count_lte(a: dict, run: RunResult) -> dict:
    cap = a["turn_count_lte"]
    return {
        "text": f"turn_count_lte: {cap}",
        "passed": run.turn_count <= cap,
        "evidence": f"ran {run.turn_count} turn(s)",
    }
```

- [ ] **Step 4: Run tests**

Expected: 7/7 pass.

- [ ] **Step 5: Commit**

```bash
git commit -am "harness: add trace_order, trace_count_lte, turn_count_lte"
```

---

### Task 7: Files primitives — `files_written_include`, `files_written_exclude`, `files_written_count`

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/tests/test_grader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_files_written_include_passes_on_match():
    run = _run(files_written={"references/specs/foo.md": "x"})
    exps = _grade_deterministic(
        [{"files_written_include": "references/specs/*.md"}], run
    )
    assert exps[0]["passed"] is True


def test_files_written_include_fails_when_nothing_matches():
    run = _run(files_written={"other.txt": "x"})
    exps = _grade_deterministic(
        [{"files_written_include": "references/specs/*.md"}], run
    )
    assert exps[0]["passed"] is False


def test_files_written_exclude_passes_when_no_match():
    run = _run(files_written={"notes.md": "x"})
    exps = _grade_deterministic(
        [{"files_written_exclude": "package.json"}], run
    )
    assert exps[0]["passed"] is True


def test_files_written_exclude_fails_on_match():
    run = _run(files_written={"package.json": "{}"})
    exps = _grade_deterministic(
        [{"files_written_exclude": "package.json"}], run
    )
    assert exps[0]["passed"] is False


def test_files_written_count_zero_passes_when_no_files():
    run = _run(files_written={})
    exps = _grade_deterministic([{"files_written_count": 0}], run)
    assert exps[0]["passed"] is True


def test_files_written_count_zero_fails_when_files_exist():
    run = _run(files_written={"a.md": "x", "sub/b.md": "y"})
    exps = _grade_deterministic([{"files_written_count": 0}], run)
    assert exps[0]["passed"] is False
    assert "2" in exps[0]["evidence"]


def test_files_written_count_exact_match():
    run = _run(files_written={"a.md": "x", "b.md": "y"})
    exps = _grade_deterministic([{"files_written_count": 2}], run)
    assert exps[0]["passed"] is True
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement**

```python
@_primitive("files_written_include")
def _grade_files_written_include(a: dict, run: RunResult) -> dict:
    pattern = a["files_written_include"]
    matches = [p for p in run.files_written if fnmatch.fnmatch(p, pattern)]
    return {
        "text": f"files_written_include: {pattern}",
        "passed": bool(matches),
        "evidence": (f"matched: {matches}" if matches else f"no files matched (wrote {len(run.files_written)})"),
    }


@_primitive("files_written_exclude")
def _grade_files_written_exclude(a: dict, run: RunResult) -> dict:
    pattern = a["files_written_exclude"]
    matches = [p for p in run.files_written if fnmatch.fnmatch(p, pattern)]
    return {
        "text": f"files_written_exclude: {pattern}",
        "passed": not matches,
        "evidence": ("no matches" if not matches else f"forbidden matches: {matches}"),
    }


@_primitive("files_written_count")
def _grade_files_written_count(a: dict, run: RunResult) -> dict:
    target = a["files_written_count"]
    actual = len(run.files_written)
    return {
        "text": f"files_written_count: {target}",
        "passed": actual == target,
        "evidence": f"wrote {actual} file(s)",
    }
```

- [ ] **Step 4: Run tests**

Expected: 7/7 pass.

- [ ] **Step 5: Commit**

```bash
git commit -am "harness: add files_written_include/exclude/count primitives"
```

---

### Task 8: Files primitive — `file_contains` (with text/regex sub-field)

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/tests/test_grader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_file_contains_text_literal_passes():
    run = _run(files_written={"references/specs/foo.md": "Out of scope: X"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "references/specs/*.md", "text": "Out of scope"}}],
        run,
    )
    assert exps[0]["passed"] is True


def test_file_contains_text_fails_when_no_matching_file():
    run = _run(files_written={"other.txt": "irrelevant"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "*.md", "text": "x"}}], run
    )
    assert exps[0]["passed"] is False
    assert "no files matched" in exps[0]["evidence"]


def test_file_contains_text_fails_when_text_absent():
    run = _run(files_written={"a.md": "no match here"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "*.md", "text": "needed"}}], run
    )
    assert exps[0]["passed"] is False


def test_file_contains_regex_passes():
    run = _run(files_written={"a.md": "allowlist entry"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "*.md", "regex": r"(?i)(allowlist|routing)"}}], run
    )
    assert exps[0]["passed"] is True


def test_file_contains_requires_exactly_one_of_text_or_regex():
    run = _run(files_written={"a.md": "x"})
    exps = _grade_deterministic(
        [{"file_contains": {"path": "*.md", "text": "x", "regex": "x"}}], run
    )
    assert exps[0]["passed"] is False
    assert "exactly one" in exps[0]["evidence"]
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement**

```python
@_primitive("file_contains")
def _grade_file_contains(a: dict, run: RunResult) -> dict:
    spec = a["file_contains"]
    path_glob = spec["path"]
    text = spec.get("text")
    pattern = spec.get("regex")
    if (text is None) == (pattern is None):
        return {
            "text": f"file_contains: {path_glob}",
            "passed": False,
            "evidence": "invalid assertion: must set exactly one of `text` or `regex`",
        }
    matches = [(p, c) for p, c in run.files_written.items() if fnmatch.fnmatch(p, path_glob)]
    if not matches:
        return {
            "text": f"file_contains: {path_glob}",
            "passed": False,
            "evidence": f"no files matched glob (wrote {len(run.files_written)})",
        }
    for path, content in matches:
        if text is not None and text in content:
            return {
                "text": f"file_contains: {path_glob} text={text!r}",
                "passed": True,
                "evidence": f"found in {path}",
            }
        if pattern is not None and re.search(pattern, content):
            return {
                "text": f"file_contains: {path_glob} regex={pattern!r}",
                "passed": True,
                "evidence": f"regex matched in {path}",
            }
    return {
        "text": f"file_contains: {path_glob}",
        "passed": False,
        "evidence": f"no matching file contained the target (checked {[p for p, _ in matches]})",
    }
```

- [ ] **Step 4: Run tests**

Expected: 5/5 pass.

- [ ] **Step 5: Commit**

```bash
git commit -am "harness: add file_contains primitive with text/regex sub-field"
```

---

### Task 9: Rename `lint` → `script_name`

**Files:**
- Modify: `tests/support/harness/grader.py`
- Test: `tests/support/harness/tests/test_grader.py`

Introduce `script_name` as the canonical form. Keep `lint` working as an alias for one more phase (eval files still use it until migration).

- [ ] **Step 1: Write failing tests**

```python
def test_script_name_runs_skill_lint_and_passes_on_clean():
    clean = "Hey, Sarah,\n\nSeason 3 wrapped with 450 fellows.\n\n- Swift\n"
    run = _run(final_message=clean)
    exps = _grade_deterministic([{"script_name": "ghostwrite"}], run)
    assert len(exps) == 1
    assert exps[0]["passed"] is True
    assert exps[0]["text"] == "script_name: ghostwrite"


def test_script_name_fails_on_em_dash():
    run = _run(final_message="We shipped it — finally.\n")
    exps = _grade_deterministic([{"script_name": "ghostwrite"}], run)
    assert exps[0]["passed"] is False
    assert "em dash" in exps[0]["evidence"]


def test_lint_alias_still_works():
    """Legacy key, remove in Phase 6."""
    run = _run(final_message="Hey, Sarah,\n\n- Swift\n")
    exps = _grade_deterministic([{"lint": "ghostwrite"}], run)
    assert exps[0]["passed"] is True
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement**

In `grader.py`, rename `_grade_lint` to `_grade_script_name` (keeping the old name as a thin alias) and register the new primitive:

```python
def _grade_script_name(skill: str, run: RunResult) -> dict:
    """Run skills/<skill>/lint.py against the agent's captured output."""
    lint_path = _repo_root() / "skills" / skill / "lint.py"
    text = f"script_name: {skill}"
    if not lint_path.exists():
        return {
            "text": text,
            "passed": False,
            "evidence": f"lint script not found at {lint_path}",
        }
    content = getattr(run, "final_message", "") or run.stdout or ""
    if not content.strip() and run.files_written:
        content = next(iter(run.files_written.values()))
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, str(lint_path), tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    passed = result.returncode == 0
    if passed:
        evidence = "lint clean (exit 0)"
    else:
        findings = result.stdout.strip() or result.stderr.strip() or "(no findings emitted)"
        evidence = f"exit {result.returncode}: {findings}"
    return {"text": text, "passed": passed, "evidence": evidence}


# Backward-compat alias. Delete in Phase 6 after migration.
def _grade_lint(skill: str, run: RunResult) -> dict:
    out = _grade_script_name(skill, run)
    out["text"] = f"lint: {skill}"
    return out


@_primitive("script_name")
def _grade_script_name_primitive(a: dict, run: RunResult) -> dict:
    return _grade_script_name(a["script_name"], run)
```

Note: the existing `_grade_lint_primitive` (from Task 1) stays — it dispatches to `_grade_lint`, which now calls `_grade_script_name` under the hood.

- [ ] **Step 4: Run tests**

```
uv run pytest tests/support/harness/tests/test_grader.py -v -k "lint or script_name"
```

Expected: all pass, including the legacy `lint` tests from earlier.

- [ ] **Step 5: Commit**

```bash
git commit -am "harness: add script_name primitive (lint kept as alias)"
```

---

### Task 10: Update `eval.schema.json`

**Files:**
- Modify: `tests/support/harness/eval.schema.json`
- Test: `tests/support/harness/tests/test_discovery.py` (add a schema-accept test)

Extend the schema to accept the new primitives. Keep the old ones (`text`, `lint`, `shared_assertions`, `grader_model`, `grader_input_limit`, `use_shared_assertions`) for now — they're deleted in Phase 6.

- [ ] **Step 1: Write a schema-acceptance test**

Add to `tests/support/harness/tests/test_discovery.py`:

```python
import json
from pathlib import Path

from tests.support.harness.discovery import load_eval_file


def _write(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "demo.json"
    p.write_text(json.dumps(data))
    return p


def test_schema_accepts_new_primitives(tmp_path):
    data = {
        "name": "demo",
        "evals": [
            {
                "id": "c1",
                "turns": ["hello"],
                "assertions": [
                    {"regex": "hi", "min": 1, "max": 3, "on": "final_message"},
                    {"not_regex": "bad"},
                    {"contains": "hello"},
                    {"contains_all": ["a", "b"]},
                    {"not_contains": "bad"},
                    {"output_len_lte": 100},
                    {"output_len_gte": 10},
                    {"token_usage_lte": 1000},
                    {"skill_invoked": "ghostwrite"},
                    {"skill_not_invoked": "summarize"},
                    {"trace_order": ["Read", "Write"]},
                    {"trace_count_lte": {"tool": "Bash", "n": 3}},
                    {"turn_count_lte": 1},
                    {"files_written_include": "*.md"},
                    {"files_written_exclude": "*.py"},
                    {"files_written_count": 0},
                    {"file_contains": {"path": "*.md", "text": "ok"}},
                    {"script_name": "ghostwrite"},
                ],
            }
        ],
    }
    path = _write(tmp_path, data)
    suite = load_eval_file(path, kind="skill")
    assert suite.name == "demo"
    assert len(suite.cases[0].assertions) == 18
```

- [ ] **Step 2: Run to confirm failure**

```
uv run pytest tests/support/harness/tests/test_discovery.py::test_schema_accepts_new_primitives -v
```

Expected: fails on schema validation (new keys not in `oneOf`).

- [ ] **Step 3: Update `eval.schema.json`**

Replace the `assertion` definition's `oneOf` with this expanded list (keep existing `text` and `lint` variants for backward compat):

```json
"assertion": {
  "type": "object",
  "oneOf": [
    {"required": ["text"], "properties": {"text": {"type": "string", "minLength": 1}}, "additionalProperties": false},
    {"required": ["tool_called"], "properties": {"tool_called": {"type": "string", "minLength": 1}}, "additionalProperties": false},
    {"required": ["tool_not_called"], "properties": {"tool_not_called": {"type": "string", "minLength": 1}}, "additionalProperties": false},
    {"required": ["skill_invoked"], "properties": {"skill_invoked": {"type": "string", "minLength": 1}}, "additionalProperties": false},
    {"required": ["skill_not_invoked"], "properties": {"skill_not_invoked": {"type": "string", "minLength": 1}}, "additionalProperties": false},
    {"required": ["lint"], "properties": {"lint": {"type": "string", "minLength": 1}}, "additionalProperties": false},
    {"required": ["script_name"], "properties": {"script_name": {"type": "string", "minLength": 1}}, "additionalProperties": false},
    {
      "required": ["regex"],
      "properties": {
        "regex": {"type": "string", "minLength": 1},
        "min": {"type": "integer", "minimum": 0},
        "max": {"type": ["integer", "null"], "minimum": 0},
        "on": {"type": "string"}
      },
      "additionalProperties": false
    },
    {"required": ["not_regex"], "properties": {"not_regex": {"type": "string", "minLength": 1}, "on": {"type": "string"}}, "additionalProperties": false},
    {"required": ["contains"], "properties": {"contains": {"type": "string", "minLength": 1}, "on": {"type": "string"}}, "additionalProperties": false},
    {"required": ["contains_all"], "properties": {"contains_all": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1}, "on": {"type": "string"}}, "additionalProperties": false},
    {"required": ["not_contains"], "properties": {"not_contains": {"type": "string", "minLength": 1}, "on": {"type": "string"}}, "additionalProperties": false},
    {"required": ["output_len_lte"], "properties": {"output_len_lte": {"type": "integer", "minimum": 0}, "on": {"type": "string"}}, "additionalProperties": false},
    {"required": ["output_len_gte"], "properties": {"output_len_gte": {"type": "integer", "minimum": 0}, "on": {"type": "string"}}, "additionalProperties": false},
    {"required": ["token_usage_lte"], "properties": {"token_usage_lte": {"type": "integer", "minimum": 0}}, "additionalProperties": false},
    {
      "required": ["trace_order"],
      "properties": {"trace_order": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1}},
      "additionalProperties": false
    },
    {
      "required": ["trace_count_lte"],
      "properties": {
        "trace_count_lte": {
          "type": "object",
          "required": ["tool", "n"],
          "properties": {"tool": {"type": "string"}, "n": {"type": "integer", "minimum": 0}},
          "additionalProperties": false
        }
      },
      "additionalProperties": false
    },
    {"required": ["turn_count_lte"], "properties": {"turn_count_lte": {"type": "integer", "minimum": 1}}, "additionalProperties": false},
    {"required": ["files_written_include"], "properties": {"files_written_include": {"type": "string", "minLength": 1}}, "additionalProperties": false},
    {"required": ["files_written_exclude"], "properties": {"files_written_exclude": {"type": "string", "minLength": 1}}, "additionalProperties": false},
    {"required": ["files_written_count"], "properties": {"files_written_count": {"type": "integer", "minimum": 0}}, "additionalProperties": false},
    {
      "required": ["file_contains"],
      "properties": {
        "file_contains": {
          "type": "object",
          "required": ["path"],
          "properties": {
            "path": {"type": "string", "minLength": 1},
            "text": {"type": "string"},
            "regex": {"type": "string"}
          },
          "additionalProperties": false
        }
      },
      "additionalProperties": false
    }
  ]
}
```

- [ ] **Step 4: Run tests**

Expected: the new test passes and existing discovery tests still pass.

```
uv run pytest tests/support/harness/tests/test_discovery.py -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/eval.schema.json tests/support/harness/tests/test_discovery.py
git commit -m "harness: extend eval schema with new assertion primitives"
```

---

## Phase 2 — Rubric Parser and Grader

### Task 11: Create `rubric.py` parser

**Files:**
- Create: `tests/support/harness/rubric.py`
- Create: `tests/support/harness/tests/test_rubric.py`

- [ ] **Step 1: Write failing tests**

Create `tests/support/harness/tests/test_rubric.py`:

```python
from pathlib import Path

import pytest

from tests.support.harness.rubric import parse_rubric_file, parse_rubric_text


def test_parses_critical_and_optional_bullets():
    text = """# Ghostwrite Rubric

Intro paragraph grader sees as context.

## Critical

- Preserves every factual claim
- Reads in Swift's voice

## Optional

- Contractions used where natural
"""
    items = parse_rubric_text(text)
    assert items == [
        {"text": "Preserves every factual claim", "critical": True},
        {"text": "Reads in Swift's voice", "critical": True},
        {"text": "Contractions used where natural", "critical": False},
    ]


def test_ignores_content_outside_known_sections():
    text = """# Rubric

## Notes

- ignored bullet

## Critical

- kept bullet
"""
    items = parse_rubric_text(text)
    assert items == [{"text": "kept bullet", "critical": True}]


def test_missing_file_returns_empty_list(tmp_path):
    missing = tmp_path / "no.md"
    assert parse_rubric_file(missing) == []


def test_parses_real_file(tmp_path):
    p = tmp_path / "RUBRIC.md"
    p.write_text("## Critical\n\n- a\n- b\n")
    items = parse_rubric_file(p)
    assert [i["text"] for i in items] == ["a", "b"]


def test_rejects_malformed_critical_header():
    text = "## critical\n\n- bad"  # lowercase — we're strict
    items = parse_rubric_text(text)
    assert items == []  # header doesn't match, so no items captured
```

- [ ] **Step 2: Confirm failure**

```
uv run pytest tests/support/harness/tests/test_rubric.py -v
```

Expected: `ImportError: No module named 'tests.support.harness.rubric'`.

- [ ] **Step 3: Implement**

Create `tests/support/harness/rubric.py`:

```python
from pathlib import Path


def parse_rubric_file(path: Path) -> list[dict]:
    """Return [{text, critical}, ...]. Missing file returns []."""
    if not path.exists():
        return []
    return parse_rubric_text(path.read_text())


def parse_rubric_text(text: str) -> list[dict]:
    items: list[dict] = []
    current_section: str | None = None  # "critical" | "optional" | None
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            heading = line[3:].strip()
            if heading == "Critical":
                current_section = "critical"
            elif heading == "Optional":
                current_section = "optional"
            else:
                current_section = None
            continue
        if current_section is None:
            continue
        if line.startswith("- "):
            bullet = line[2:].strip()
            if bullet:
                items.append({"text": bullet, "critical": current_section == "critical"})
    return items
```

- [ ] **Step 4: Run tests**

Expected: 5/5 pass.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/rubric.py tests/support/harness/tests/test_rubric.py
git commit -m "harness: add RUBRIC.md parser"
```

---

### Task 12: Add `grade_rubric()` to `grader.py`

**Files:**
- Modify: `tests/support/harness/grader.py`
- Modify: `tests/support/harness/tests/test_grader.py`

- [ ] **Step 1: Write failing tests**

```python
import asyncio

from tests.support.harness.grader import grade_rubric
from tests.support.harness.models import Grading


def test_grade_rubric_returns_empty_when_no_items(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("# no items\n")
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    assert isinstance(result, Grading)
    assert result.total == 0


def test_grade_rubric_passes_when_all_critical_pass(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("## Critical\n\n- item A\n- item B\n")

    async def fake_llm_call(prompt, model):
        return {
            "items": [
                {"text": "item A", "critical": True, "status": "pass", "evidence": "ok"},
                {"text": "item B", "critical": True, "status": "pass", "evidence": "ok"},
            ]
        }

    monkeypatch.setattr("tests.support.harness.grader._rubric_llm_call", fake_llm_call)
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    assert result.passed == 2
    assert result.failed == 0


def test_grade_rubric_fails_when_critical_item_fails(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("## Critical\n\n- item A\n")

    async def fake_llm_call(prompt, model):
        return {"items": [{"text": "item A", "critical": True, "status": "fail", "evidence": "missing"}]}

    monkeypatch.setattr("tests.support.harness.grader._rubric_llm_call", fake_llm_call)
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    assert result.failed == 1


def test_grade_rubric_na_counts_as_pass_for_critical_gate(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("## Critical\n\n- item A\n- item B\n")

    async def fake_llm_call(prompt, model):
        return {
            "items": [
                {"text": "item A", "critical": True, "status": "pass", "evidence": "ok"},
                {"text": "item B", "critical": True, "status": "n/a", "evidence": "not applicable"},
            ]
        }

    monkeypatch.setattr("tests.support.harness.grader._rubric_llm_call", fake_llm_call)
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    # Case passes: both critical items are pass/na. We report n/a items as
    # "passed" for aggregate scoring simplicity — the rubric summary on screen
    # can show na breakdowns separately.
    assert result.failed == 0
    assert result.total == 2


def test_grade_rubric_optional_failures_dont_fail_the_case(monkeypatch, tmp_path):
    rubric_path = tmp_path / "RUBRIC.md"
    rubric_path.write_text("## Critical\n\n- crit\n\n## Optional\n\n- opt\n")

    async def fake_llm_call(prompt, model):
        return {
            "items": [
                {"text": "crit", "critical": True, "status": "pass", "evidence": "ok"},
                {"text": "opt", "critical": False, "status": "fail", "evidence": "nope"},
            ]
        }

    monkeypatch.setattr("tests.support.harness.grader._rubric_llm_call", fake_llm_call)
    run = _run(final_message="x")
    result = asyncio.run(grade_rubric(run, rubric_path))
    # Optional fail is reported but doesn't count toward `failed`.
    assert result.failed == 0
    assert result.total == 2
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement**

Add to `grader.py`:

```python
from .rubric import parse_rubric_file

RUBRIC_PROMPT = """\
You are a strict rubric grader. Evaluate the AGENT OUTPUT below against each RUBRIC ITEM.

For each item return one of:
- "pass": the output clearly satisfies the item
- "fail": the output clearly does not satisfy the item
- "n/a": the item does not apply to this kind of output (e.g. the correct behavior is a refusal)

Cite specific evidence from the output. No partial credit. When uncertain, fail.

Return ONLY a JSON object matching:
{{
  "items": [
    {{"text": "<item text>", "critical": true|false, "status": "pass"|"fail"|"n/a", "evidence": "<quote or observation>"}}
  ]
}}

AGENT OUTPUT (final message):
{final_message}

FILES WRITTEN:
{files_block}

RUBRIC:
{rubric_text}
"""

_RUBRIC_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "critical": {"type": "boolean"},
                        "status": {"type": "string", "enum": ["pass", "fail", "n/a"]},
                        "evidence": {"type": "string"},
                    },
                    "required": ["text", "critical", "status", "evidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    },
}


async def _rubric_llm_call(prompt: str, model: str) -> dict:
    """Call the LLM with structured output. Isolated so tests can monkeypatch."""
    options = ClaudeAgentOptions(model=model, output_format=_RUBRIC_SCHEMA)
    structured: dict | None = None
    parts: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if getattr(message, "structured_output", None):
                structured = message.structured_output
            elif getattr(message, "result", None):
                parts.append(message.result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    parts.append(block.text)
    if structured is not None:
        return structured
    raw = "".join(parts).strip()
    return _parse_grader_fallback(raw)


async def grade_rubric(
    run: RunResult,
    rubric_path: Path,
    model: str = DEFAULT_GRADER_MODEL,
) -> Grading:
    items = parse_rubric_file(rubric_path)
    if not items:
        return Grading.from_expectations([])
    rubric_text = rubric_path.read_text()
    final_msg = getattr(run, "final_message", "") or run.stdout or "(empty)"
    files_block = (
        "\n\n".join(f"--- {p} ---\n{_truncate_tail(c, DEFAULT_FILE_LIMIT)}" for p, c in run.files_written.items())
        or "(none)"
    )
    prompt = RUBRIC_PROMPT.format(
        final_message=_truncate_tail(final_msg, DEFAULT_STDOUT_LIMIT),
        files_block=files_block,
        rubric_text=rubric_text,
    )
    data = await _rubric_llm_call(prompt, model)
    expectations: list[dict] = []
    for graded in data["items"]:
        status = graded["status"]
        critical = graded["critical"]
        # Pass rule (see spec §Rubric grader):
        #   - critical + fail  => failed
        #   - critical + pass  => passed
        #   - critical + n/a   => passed (excused)
        #   - optional + any   => passed (informational only)
        if critical and status == "fail":
            passed = False
        else:
            passed = True
        expectations.append(
            {
                "text": ("[critical] " if critical else "[optional] ") + graded["text"] + f" -- {status}",
                "passed": passed,
                "evidence": graded["evidence"],
            }
        )
    return Grading.from_expectations(expectations)
```

- [ ] **Step 4: Run tests**

```
uv run pytest tests/support/harness/tests/test_grader.py -v -k "rubric"
```

Expected: 5/5 pass.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/grader.py tests/support/harness/tests/test_grader.py
git commit -m "harness: add grade_rubric with n/a-aware pass rule"
```

---

## Phase 3 — Tier Flag and Orchestration

### Task 13: Add `tier` to CLI and `RunPlan`, add `make eval` target

**Files:**
- Modify: `tests/support/harness/models.py`
- Modify: `tests/support/harness/__main__.py`
- Modify: `Makefile`
- Modify: `tests/support/harness/tests/test_discovery.py` (existing plan tests)

- [ ] **Step 1: Write failing test**

Add to `tests/support/harness/tests/test_discovery.py`:

```python
from tests.support.harness.discovery import build_run_plans
from tests.support.harness.models import EvalCase, EvalSuite


def test_run_plan_carries_tier(tmp_path):
    suite = EvalSuite(
        name="demo",
        kind="core",
        source_path=tmp_path / "demo.json",
        cases=[EvalCase(id="c1", turns=["hi"])],
    )
    plans = build_run_plans([suite], project_root=tmp_path, baseline=False, tier="eval")
    assert plans[0].tier == "eval"
```

- [ ] **Step 2: Run to confirm failure**

Expected: `TypeError: build_run_plans() got an unexpected keyword argument 'tier'` or `AttributeError`.

- [ ] **Step 3: Implement**

Update `tests/support/harness/models.py` — add a `tier` field to `RunPlan`:

```python
RunTier = Literal["test", "eval"]

@dataclass
class RunPlan:
    suite_name: str
    suite_kind: EvalKind
    case_id: str
    variant: RunVariant
    turns: list[str]
    context_paths: list[Path]
    case: EvalCase
    tier: RunTier = "test"
```

Update `tests/support/harness/discovery.py` — thread `tier` through `build_run_plans`:

```python
def build_run_plans(
    suites: list[EvalSuite],
    project_root: Path,
    baseline: bool,
    tier: str = "test",
) -> list[RunPlan]:
    # existing body; set tier= on every RunPlan(...)
```

Pass `tier=tier` in every `RunPlan(...)` construction in that function.

Update `tests/support/harness/__main__.py`:

```python
parser.add_argument(
    "--tier",
    choices=["test", "eval"],
    default="test",
    help="test = fast deterministic. eval = deep with rubric grading.",
)
# ...
return asyncio.run(
    run_evals(
        project_root=project_root,
        names=args.names or None,
        baseline=(args.tier == "eval") and not args.no_baseline,
        verbose=args.verbose,
        reporter=reporter,
        model=args.model,
        tier=args.tier,
    )
)
```

Update `Makefile`:

```makefile
.PHONY: install test eval test-harness lint format

install:
	uv sync

test:
	uv run python -m tests.support.harness --tier test $(ARGS)

eval:
	uv run python -m tests.support.harness --tier eval $(ARGS)

test-harness:
	uv run pytest -v

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .
```

- [ ] **Step 4: Run tests**

```
uv run pytest tests/support/harness/tests/test_discovery.py -v
uv run pytest tests/support/harness/tests/ -v
```

Expected: new test passes, existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/models.py tests/support/harness/discovery.py tests/support/harness/__main__.py Makefile tests/support/harness/tests/test_discovery.py
git commit -m "harness: add --tier flag and make eval target"
```

---

### Task 14: Orchestrator routes rubric grading to deep tier only

**Files:**
- Modify: `tests/support/harness/orchestrator.py`
- Test: `tests/support/harness/tests/test_orchestrator.py` (create if absent)

- [ ] **Step 1: Write a routing test**

Add to `tests/support/harness/tests/test_orchestrator.py`:

```python
from pathlib import Path

from tests.support.harness.orchestrator import _should_rubric_grade
from tests.support.harness.models import EvalCase, RunPlan


def _plan(tier: str, kind: str, suite_name: str) -> RunPlan:
    return RunPlan(
        suite_name=suite_name,
        suite_kind=kind,
        case_id="c1",
        variant="run",
        turns=["hi"],
        context_paths=[],
        case=EvalCase(id="c1", turns=["hi"]),
        tier=tier,
    )


def test_rubric_grading_skipped_on_fast_tier(tmp_path):
    # Even if a rubric exists, fast tier must not grade it.
    plan = _plan("test", "skill", "ghostwrite")
    assert _should_rubric_grade(plan, project_root=tmp_path) is False


def test_rubric_grading_skipped_when_no_rubric_file(tmp_path):
    plan = _plan("eval", "skill", "ghostwrite")
    # No skills/ghostwrite/RUBRIC.md on disk.
    assert _should_rubric_grade(plan, project_root=tmp_path) is False


def test_rubric_grading_runs_on_deep_tier_when_rubric_exists(tmp_path):
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "skills" / "ghostwrite" / "RUBRIC.md").write_text("## Critical\n\n- x\n")
    plan = _plan("eval", "skill", "ghostwrite")
    assert _should_rubric_grade(plan, project_root=tmp_path) is True


def test_rubric_grading_skipped_for_core_suites(tmp_path):
    (tmp_path / "skills" / "skill-triggers").mkdir(parents=True)
    (tmp_path / "skills" / "skill-triggers" / "RUBRIC.md").write_text("## Critical\n\n- x\n")
    plan = _plan("eval", "core", "skill-triggers")
    assert _should_rubric_grade(plan, project_root=tmp_path) is False
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement**

Add to `tests/support/harness/orchestrator.py`:

```python
def _should_rubric_grade(plan: RunPlan, project_root: Path) -> bool:
    if plan.tier != "eval":
        return False
    if plan.suite_kind != "skill":
        return False
    # Don't re-grade lift baselines against the rubric — the rubric is a
    # quality bar on the with-skill variant.
    if plan.variant == "baseline":
        return False
    rubric_path = project_root / "skills" / plan.suite_name / "RUBRIC.md"
    return rubric_path.exists()
```

Then in `_run_one`, after the existing `grade(...)` call, add rubric grading and merge:

```python
from .grader import grade_rubric

# after:
# grading = await grade(...)

if _should_rubric_grade(plan, project_root=project_root):
    rubric_path = project_root / "skills" / plan.suite_name / "RUBRIC.md"
    rubric_grading = await grade_rubric(run, rubric_path)
    grading = Grading.from_expectations(grading.expectations + rubric_grading.expectations)
```

Update `run_evals(...)` signature to accept `tier: str = "test"` and pass it to `build_run_plans`.

- [ ] **Step 4: Run tests**

```
uv run pytest tests/support/harness/tests/test_orchestrator.py -v
```

Expected: 4/4 pass.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/orchestrator.py tests/support/harness/tests/test_orchestrator.py
git commit -m "harness: wire rubric grading into deep tier"
```

---

### Task 15: Fast-tier smoke — existing suites still pass

**Files:** (none modified — this is a verification task)

- [ ] **Step 1: Run the existing eval suite on fast tier**

```
make test ARGS="ghostwrite"
```

Expected:
- The run completes.
- The grader still calls the LLM for `{"text": ...}` assertions (backward compat — not touched yet).
- Deterministic assertions run normally.

If it fails, go back and fix before proceeding. This catches regressions in Tasks 1–14.

- [ ] **Step 2: Run the harness unit tests**

```
uv run pytest tests/support/harness/tests/ -v
```

Expected: every test passes.

- [ ] **Step 3: No commit** — this is a verification gate only.

---

## Phase 4 — Reporter Split

### Task 16: Fast-tier reporter summary

**Files:**
- Modify: `tests/support/harness/reporter.py`
- Modify: `tests/support/harness/tests/test_reporter.py` (create if absent)

Goal: when the run's tier is `test`, `_print_summary` prints the fast-tier layout (single table per suite kind, no WARN, no baselines, no lift comparison, model name in footer).

- [ ] **Step 1: Write failing tests**

```python
import io
from contextlib import redirect_stdout
from pathlib import Path

from tests.support.harness.models import EvalCase, Grading, RunPlan
from tests.support.harness.reporter import CaseResult, _print_summary
from tests.support.harness.runner import RunResult


def _cr(suite, case_id, kind, tier, passed, total, variant="run"):
    return CaseResult(
        plan=RunPlan(
            suite_name=suite,
            suite_kind=kind,
            case_id=case_id,
            variant=variant,
            turns=["hi"],
            context_paths=[],
            case=EvalCase(id=case_id, turns=["hi"]),
            tier=tier,
        ),
        run=RunResult(
            stdout="",
            files_written={},
            input_tokens=0,
            output_tokens=0,
            duration_s=1.0,
            exit_code=0,
            tool_trace=[],
            turn_count=1,
        ),
        grading=Grading.from_expectations(
            [{"text": f"c{i}", "passed": i < passed, "evidence": ""} for i in range(total)]
        ),
    )


def test_fast_tier_summary_single_table_no_warn():
    results = [
        _cr("ghostwrite", "sponsor-email", "skill", "test", passed=4, total=4),
        _cr("ghostwrite", "linkedin", "skill", "test", passed=3, total=4),
        _cr("skill-triggers", "t1", "core", "test", passed=3, total=3),
    ]
    buf = io.StringIO()
    with redirect_stdout(buf):
        _print_summary(results, verbose=False, model="claude-haiku-4-5")
    out = buf.getvalue()
    assert "WARN" not in out
    assert "baseline" not in out
    assert "## Core" in out
    assert "## Skills" in out
    assert "claude-haiku-4-5" in out
    assert "ghostwrite" in out
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement**

Refactor `_print_summary` to detect tier (read from the first result's plan) and dispatch to either `_print_fast_summary` or the existing deep-tier layout. Add a `model: str | None = None` parameter threaded from `run_evals` (the orchestrator already knows which model it used).

```python
def _print_summary(results: list[CaseResult], verbose: bool, model: str | None = None) -> int:
    if not results:
        return 0
    tier = results[0].plan.tier
    if tier == "test":
        return _print_fast_summary(results, verbose=verbose, model=model)
    return _print_deep_summary(results, verbose=verbose, model=model)


def _print_fast_summary(results: list[CaseResult], verbose: bool, model: str | None) -> int:
    exit_code = 0
    by_suite_kind: dict[str, dict[str, list[CaseResult]]] = {"core": {}, "skill": {}}
    for r in results:
        suite = r.plan.suite_name
        by_suite_kind[r.plan.suite_kind].setdefault(suite, []).append(r)

    if by_suite_kind["core"]:
        print("\n## Core\n")
        for suite, cases in sorted(by_suite_kind["core"].items()):
            passed = sum(1 for c in cases if c.grading.failed == 0 and c.run.exit_code == 0)
            total = len(cases)
            status = "ok" if passed == total else "fail"
            if status == "fail":
                exit_code = 1
            print(f"{suite:<25} {passed}/{total}  {status}")

    if by_suite_kind["skill"]:
        print("\n## Skills\n")
        for suite, cases in sorted(by_suite_kind["skill"].items()):
            passed = sum(1 for c in cases if c.grading.failed == 0 and c.run.exit_code == 0)
            total = len(cases)
            status = "ok" if passed == total else "fail"
            if status == "fail":
                exit_code = 1
            print(f"{suite:<25} {passed}/{total}  {status}")

    total_cases = len(results)
    passed_cases = sum(1 for r in results if r.grading.failed == 0 and r.run.exit_code == 0)
    pct = int(round(100 * passed_cases / total_cases)) if total_cases else 0
    print(f"\n{passed_cases}/{total_cases} pass ({pct}%) on {model or 'default'}")
    _print_failures(results, verbose)
    return exit_code


def _print_failures(results, verbose):
    failures = [r for r in results if r.grading.failed > 0 or r.run.exit_code != 0]
    if failures:
        print("\n### Failures\n")
        for r in failures:
            label = f"{r.plan.suite_name} > {r.plan.case_id}"
            print(f"\n**{label}**")
            if r.run.exit_code != 0:
                print(f"- RUN ERROR ({r.run.exit_code}): {r.run.error}")
            for exp in r.grading.expectations:
                if not exp["passed"]:
                    print(f"- FAIL: {exp['text']}")
                    print(f"  Evidence: {exp.get('evidence', '(none)')}")
    if verbose:
        print("\n### Passing assertions (verbose)\n")
        for r in results:
            for exp in r.grading.expectations:
                if exp["passed"]:
                    print(f"- PASS [{r.plan.suite_name}/{r.plan.case_id}]: {exp['text']}")
                    print(f"  Evidence: {exp.get('evidence', '(none)')}")


def _print_deep_summary(results: list[CaseResult], verbose: bool, model: str | None) -> int:
    # Temporary passthrough — Task 17 replaces this with the tiered layout.
    return _print_existing_summary(results, verbose)


_print_existing_summary = _print_summary.__wrapped__ if hasattr(_print_summary, "__wrapped__") else None
```

In practice, rename the existing `_print_summary` body to `_print_existing_summary` (a plain function), and have the new `_print_summary` route to either `_print_fast_summary` or `_print_existing_summary`.

Thread `model` through `DotsReporter.finish` / `RichReporter.finish` / `run_evals` / `make_reporter`. Each reporter stores the model on `start()` or passes it to `_print_summary` at finish time.

- [ ] **Step 4: Run tests**

```
uv run pytest tests/support/harness/tests/test_reporter.py -v
```

Expected: new test passes, existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/reporter.py tests/support/harness/orchestrator.py tests/support/harness/tests/test_reporter.py
git commit -m "harness: add fast-tier reporter layout"
```

---

### Task 17: Deep-tier reporter with Core / Regression / Lift tables

**Files:**
- Modify: `tests/support/harness/reporter.py`
- Modify: `tests/support/harness/tests/test_reporter.py`

- [ ] **Step 1: Write failing test**

```python
def test_deep_tier_summary_has_three_tables_and_no_warn():
    # Build a result set with one core, one regression, one lift (with baseline).
    results = [
        _cr("skill-triggers", "t1", "core", "eval", passed=3, total=3),
        _cr("summarize", "paste-raw-text", "skill", "eval", passed=4, total=4, variant="with_skill"),
        _cr(
            "ghostwrite", "sponsor-email", "skill", "eval", passed=4, total=4, variant="with_skill"
        ),
        _cr(
            "ghostwrite", "sponsor-email", "skill", "eval", passed=2, total=4, variant="baseline"
        ),
    ]
    # Mark ghostwrite sponsor-email as lift intent:
    results[2].plan.case.intent = "lift"
    results[3].plan.case.intent = "lift"
    # summarize paste-raw-text is regression by default.

    buf = io.StringIO()
    with redirect_stdout(buf):
        _print_summary(results, verbose=False, model="claude-sonnet-4-6")
    out = buf.getvalue()
    assert "## Core" in out
    assert "## Skills (regression)" in out
    assert "## Lift" in out
    assert "WARN" not in out
    assert "claude-sonnet-4-6" in out
```

- [ ] **Step 2: Confirm failure** — the deep-tier path still falls through to the old summary (which has WARN).

- [ ] **Step 3: Implement**

Replace `_print_existing_summary` with a purpose-built deep-tier printer. Delete the WARN logic and `LIFT_MIN_WITH_SKILL_RATE` (all failures are real now).

```python
def _print_deep_summary(results: list[CaseResult], verbose: bool, model: str | None) -> int:
    exit_code = 0
    model_label = model or "default"

    core = [r for r in results if r.plan.suite_kind == "core"]
    skill = [r for r in results if r.plan.suite_kind == "skill"]

    # Core table
    if core:
        print(f"\n## Core — {model_label}\n")
        by_suite: dict[str, list[CaseResult]] = {}
        for r in core:
            by_suite.setdefault(r.plan.suite_name, []).append(r)
        for suite, cases in sorted(by_suite.items()):
            passed = sum(1 for c in cases if c.grading.failed == 0 and c.run.exit_code == 0)
            total = len(cases)
            status = "ok" if passed == total else "fail"
            if status == "fail":
                exit_code = 1
            print(f"{suite:<32} {passed}/{total} checks   {status}")

    # Pair up with_skill and baseline runs by (suite, case_id)
    by_key: dict[tuple[str, str], dict[str, CaseResult]] = {}
    for r in skill:
        by_key.setdefault((r.plan.suite_name, r.plan.case_id), {})[r.plan.variant] = r

    regression_rows = []
    lift_rows = []
    for (suite, case_id), variants in sorted(by_key.items()):
        ws = variants.get("with_skill")
        if ws is None:
            continue
        if ws.plan.case.intent == "lift":
            lift_rows.append((suite, case_id, ws, variants.get("baseline")))
        else:
            regression_rows.append((suite, case_id, ws))

    if regression_rows:
        print(f"\n## Skills (regression) — {model_label}\n")
        for suite, case_id, ws in regression_rows:
            failing = ws.run.exit_code != 0 or ws.grading.failed > 0
            if failing:
                exit_code = 1
            status = "fail" if failing else "ok"
            print(f"{suite:<20} {case_id:<32} {_fmt_score(ws.grading):<14} {status}")

    if lift_rows:
        print(f"\n## Lift — {model_label}\n")
        for suite, case_id, ws, bl in lift_rows:
            ws_str = _fmt_score(ws.grading)
            bl_str = _fmt_score(bl.grading) if bl else "—"
            failing = ws.run.exit_code != 0 or ws.grading.failed > 0
            if failing:
                exit_code = 1
            status = "fail" if failing else "ok"
            print(
                f"{suite:<20} {case_id:<32} with_skill={ws_str:<12} baseline={bl_str:<12} {status}"
            )

    _print_failures(results, verbose)
    return exit_code
```

Also update the `make_reporter()` / `RichReporter` / `DotsReporter` paths so that `finish(..., model=...)` forwards to `_print_summary`. Drop `LIFT_MIN_WITH_SKILL_RATE`.

- [ ] **Step 4: Run tests**

Expected: all reporter tests pass.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/reporter.py tests/support/harness/orchestrator.py tests/support/harness/tests/test_reporter.py
git commit -m "harness: deep-tier reporter with Core/Regression/Lift tables"
```

---

## Phase 5 — Flatten Tree and Migrate Suites

### Task 18: Rewrite discovery for flat `tests/*.json`

**Files:**
- Modify: `tests/support/harness/discovery.py`
- Modify: `tests/support/harness/tests/test_discovery.py`

Goal: new discovery scans `tests/*.json` directly. Auto-detects skill vs core by matching the filename stem against `skills/<name>/`. Keep the old nested scan as a fallback for the window where files are being moved.

- [ ] **Step 1: Write failing tests**

```python
def test_flat_discovery_finds_skill_suite(tmp_path):
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "ghostwrite.json").write_text(
        json.dumps({"name": "ghostwrite", "evals": [{"id": "x", "turns": ["hi"]}]})
    )
    suites = discover_suites(tmp_path / "tests", skills_root=tmp_path / "skills")
    assert len(suites) == 1
    assert suites[0].kind == "skill"
    assert suites[0].name == "ghostwrite"


def test_flat_discovery_treats_unknown_stem_as_core(tmp_path):
    (tmp_path / "skills").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "skill-triggers.json").write_text(
        json.dumps({"name": "skill-triggers", "evals": [{"id": "x", "turns": ["hi"]}]})
    )
    suites = discover_suites(tmp_path / "tests", skills_root=tmp_path / "skills")
    assert suites[0].kind == "core"
```

- [ ] **Step 2: Confirm failure**

- [ ] **Step 3: Implement**

Update `discover_suites` to accept `skills_root` and scan flat:

```python
def discover_suites(
    tests_root: Path,
    names: list[str] | None = None,
    skills_root: Path | None = None,
) -> list[EvalSuite]:
    if skills_root is None:
        skills_root = tests_root.parent / "skills"

    suites: list[EvalSuite] = []

    # Flat layout: tests/*.json
    for path in sorted(tests_root.glob("*.json")):
        stem = path.stem
        kind: EvalKind = "skill" if (skills_root / stem).is_dir() else "core"
        suites.append(load_eval_file(path, kind=kind))

    # Legacy fallback (remove after Phase 5 migration): tests/skills/*/evals.json
    skills_dir = tests_root / "skills"
    if skills_dir.is_dir():
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            evals_file = skill_dir / "evals.json"
            if evals_file.is_file():
                suites.append(load_eval_file(evals_file, kind="skill"))

    core_dir = tests_root / "core"
    if core_dir.is_dir():
        for f in sorted(core_dir.glob("*.json")):
            suites.append(load_eval_file(f, kind="core"))

    if names:
        wanted = set(names)
        suites = [s for s in suites if s.name in wanted]

    return suites
```

Also update `build_run_plans` to resolve the `files:` field relative to a new `tests/fixtures/` directory when the suite is flat (rather than the eval file's own dir).

```python
# in build_run_plans, replace eval_dir = suite.source_path.parent
# with:
if suite.source_path.parent.name == "tests":
    eval_dir = suite.source_path.parent / "fixtures"
else:
    eval_dir = suite.source_path.parent  # legacy layout
```

- [ ] **Step 4: Run tests**

```
uv run pytest tests/support/harness/tests/test_discovery.py -v
```

Expected: new tests pass, existing legacy tests still pass.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/discovery.py tests/support/harness/tests/test_discovery.py
git commit -m "harness: flat tests/*.json discovery with skill auto-detection"
```

---

### Task 19: Git-mv files into the new layout

**Files:** (purely mechanical file moves)

- [ ] **Step 1: Move skill eval files**

```bash
git mv tests/skills/ghostwrite/evals.json tests/ghostwrite.json
git mv tests/skills/summarize/evals.json tests/summarize.json
git mv tests/skills/scope/evals.json tests/scope.json
git mv tests/skills/prompt-engineer/evals.json tests/prompt-engineer.json
```

- [ ] **Step 2: Move core eval files**

```bash
git mv tests/core/skill-triggers.json tests/skill-triggers.json
git mv tests/core/no-ai-attribution.json tests/no-ai-attribution.json
```

- [ ] **Step 3: Move fixtures**

```bash
mkdir -p tests/fixtures
git mv tests/skills/summarize/test-paper.pdf tests/fixtures/test-paper.pdf
```

- [ ] **Step 4: Move lint tests next to their skills**

```bash
git mv tests/skills/ghostwrite/test_lint.py skills/ghostwrite/lint_test.py
git mv tests/skills/summarize/test_lint.py skills/summarize/lint_test.py
```

- [ ] **Step 5: Delete now-empty directories**

```bash
rmdir tests/skills/ghostwrite tests/skills/summarize tests/skills/scope tests/skills/prompt-engineer tests/skills 2>/dev/null || true
rmdir tests/core 2>/dev/null || true
```

If any `__init__.py` files were left behind, remove them with `git rm`.

- [ ] **Step 6: Update eval files' `files:` references**

In `tests/summarize.json`, any `files` entry referencing `test-paper.pdf` must now resolve from `tests/fixtures/`. Check each suite:

```
uv run python -c "import json; [print(f, json.load(open(f)).get('evals', [])) for f in ['tests/summarize.json', 'tests/scope.json', 'tests/skill-triggers.json', 'tests/no-ai-attribution.json']]" | grep files
```

Update any `"files": ["test-paper.pdf"]` to `"files": ["test-paper.pdf"]` (same name — the resolver now looks in `tests/fixtures/`, which is where it lives).

- [ ] **Step 7: Run harness discovery sanity check**

```
uv run python -c "from pathlib import Path; from tests.support.harness.discovery import discover_suites; s = discover_suites(Path('tests'), skills_root=Path('skills')); print([(x.name, x.kind) for x in s])"
```

Expected output should list all 6 suites with their correct kinds.

- [ ] **Step 8: Commit**

```bash
git commit -m "tests: flatten tests/ tree, move fixtures, relocate lint tests"
```

---

### Task 20: pytest collection — pick up `skills/*/lint_test.py`

**Files:**
- Modify: `pyproject.toml`
- Modify: `conftest.py` (or create one at repo root)

- [ ] **Step 1: Check current pytest config**

```
uv run pytest --collect-only 2>&1 | head -40
```

If `skills/ghostwrite/lint_test.py` and `skills/summarize/lint_test.py` show up, pytest already collects them via the `lint_test.py` name pattern. If not, add them.

- [ ] **Step 2: Update `pyproject.toml`**

Add or extend the `[tool.pytest.ini_options]` section:

```toml
[tool.pytest.ini_options]
testpaths = ["tests", "skills"]
python_files = ["test_*.py", "*_test.py"]
```

- [ ] **Step 3: Run harness test suite**

```
uv run pytest -v
```

Expected: every test (harness + lint tests in both locations) runs and passes. No import errors.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "tests: update pytest collection for flattened layout"
```

---

### Task 21: Verify fast tier still runs against legacy-format suites

**Files:** (verification only)

- [ ] **Step 1: Run fast tier over one skill suite in its current (pre-migration) format**

```
make test ARGS="ghostwrite"
```

Expected: runs to completion. Some `{"text": ...}` assertions will still go through the LLM grader (backward compat). Deterministic assertions grade in Python. No crashes.

- [ ] **Step 2: Run fast tier over a core suite**

```
make test ARGS="skill-triggers"
```

Expected: completes successfully.

- [ ] **Step 3: No commit** — verification gate.

---

### Task 22: Migrate `ghostwrite` — rewrite JSON and write `RUBRIC.md`

**Files:**
- Modify: `tests/ghostwrite.json`
- Create: `skills/ghostwrite/RUBRIC.md`

Use Appendix A of the spec as the source of truth for every conversion.

- [ ] **Step 1: Rewrite `tests/ghostwrite.json`**

Full replacement content:

```json
{
  "name": "ghostwrite",
  "evals": [
    {
      "id": "sponsor-email",
      "intent": "lift",
      "turns": [
        "Rewrite this as an email to our sponsor contact Sarah:\n\nHey so I wanted to reach out because we just wrapped up Season 3 of the Fellowship and the numbers were really strong. We had 450 fellows complete the program which is up 30% from last season. 92% of them said they'd recommend it to a friend. I think this is a great opportunity for us to talk about renewing the sponsorship for next season and maybe even expanding the scope of what we do together. Let me know if you'd be open to hopping on a call next week to discuss."
      ],
      "assertions": [
        {"script_name": "ghostwrite"},
        {"regex": "^Hey, Sarah --"},
        {"regex": "(- Swift|Happy Hacking,\\s*\\nSwift)\\s*$"},
        {"contains_all": ["450", "30%", "92%"]},
        {"output_len_lte": 600}
      ]
    },
    {
      "id": "linkedin-from-scratch",
      "intent": "lift",
      "turns": [
        "Write a LinkedIn post announcing that MLH is partnering with a new AI company to offer hackathon participants access to their API."
      ],
      "assertions": [
        {"script_name": "ghostwrite"}
      ]
    }
  ]
}
```

Everything semantic moves to the rubric.

- [ ] **Step 2: Create `skills/ghostwrite/RUBRIC.md`**

```markdown
# Ghostwrite Rubric

Evaluated by `make eval`. Each item is a testable outcome — not a rule to encode in the skill, but a goal the output must satisfy.

## Critical

- Output leads with the results or the ask in the first sentence (no preamble like "I wanted to reach out")
- Output preserves every factual claim from the input (numbers, names, dates)
- For the `linkedin-from-scratch` refusal case: the output does NOT contain a full LinkedIn post draft
- For the `linkedin-from-scratch` refusal case: the output asks the user to provide source content, notes, or bullet points to rewrite
- For the `linkedin-from-scratch` refusal case: the output explains that ghostwrite is a rewriter, not a creator
- For the `linkedin-from-scratch` refusal case: the output does not invent the AI company's name or fabricate partnership details

## Optional

- Contractions used where natural (we're, don't, that's)
- Sign-off matches Swift's conventions
```

- [ ] **Step 3: Run fast tier for ghostwrite**

```
make test ARGS="ghostwrite"
```

Expected: both cases pass on deterministic checks (the output_len_lte may fail on `linkedin-from-scratch` if the refusal is long — adjust if so, or add `output_len_lte` only to `sponsor-email`).

- [ ] **Step 4: Run deep tier for ghostwrite**

```
make eval ARGS="ghostwrite"
```

Expected: rubric items grade, critical items pass.

- [ ] **Step 5: Commit**

```bash
git add tests/ghostwrite.json skills/ghostwrite/RUBRIC.md
git commit -m "evals: migrate ghostwrite to deterministic + RUBRIC.md"
```

---

### Task 23: Migrate `summarize`

**Files:**
- Modify: `tests/summarize.json`
- Create: `skills/summarize/RUBRIC.md`

Follow Appendix A, `summarize` section.

- [ ] **Step 1: Rewrite `tests/summarize.json`**

Convert every case per the audit. Each case gets `{"script_name": "summarize"}` explicitly (no more `shared_assertions`). Tool-trace assertions (`tool_called` / `tool_not_called`) stay as-is. Convert the dev.to URL assertions to regex. Move semantic checks to rubric.

Use the structure from Task 22 as the template. Every case in the old file gets rewritten. For the specific assertion replacements, refer to `references/specs/2026-04-08-eval-harness-plan-b-design.md` Appendix A § summarize.

- [ ] **Step 2: Create `skills/summarize/RUBRIC.md`**

```markdown
# Summarize Rubric

Evaluated by `make eval`. Goals the output must satisfy across every case.

## Critical

- Output contains a clickable markdown link to the source URL near the title (for web-sourced cases)
- The shareable snippet block includes the source URL (for web-sourced cases)
- Key points reference specific content from the source, not generic commentary
- For local-file cases: title is derived from the document/paper title or filename, not a URL or generic placeholder like "Summary"
- For local-file cases: the shareable snippet block contains no URL
- For local-file cases: key points are grounded in the source content, not invented or generic
- For the `short-input-no-padding` case: the summary names the Q3 demo day date change as the core fact
- For the `short-input-no-padding` case: every bullet is directly supported by the 4-sentence input (no invented project-management commentary)

## Optional

- Bullets are scannable and roughly parallel in shape
```

- [ ] **Step 3: Run fast tier**

```
make test ARGS="summarize"
```

Expected: all 6 cases pass.

- [ ] **Step 4: Run deep tier**

```
make eval ARGS="summarize"
```

Expected: rubric grades, critical items mostly pass. `n/a` is fine for items that don't apply to a given case.

- [ ] **Step 5: Commit**

```bash
git add tests/summarize.json skills/summarize/RUBRIC.md
git commit -m "evals: migrate summarize to deterministic + RUBRIC.md"
```

---

### Task 24: Migrate `scope`

**Files:**
- Modify: `tests/scope.json`
- Create: `skills/scope/RUBRIC.md`

- [ ] **Step 1: Rewrite `tests/scope.json`**

Follow Appendix A § scope. Key conversions:
- `github-webhook-slack`: many `{"file_contains": {...}}` assertions for the written spec file
- `vague-notifications`: `{"regex": "\\?", "max": 2}` for "one question at a time"; `{"files_written_exclude": "references/specs/*"}`
- `skip-design-rate-limiter`: `{"regex": "\\?"}`; `{"files_written_count": 0}` (new primitive)

- [ ] **Step 2: Create `skills/scope/RUBRIC.md`**

```markdown
# Scope Rubric

Evaluated by `make eval`.

## Critical

- Output proposes 2-3 distinct approaches with trade-offs (when generating a design)
- Output includes a clear recommendation with reasoning for which approach to use
- Output asks the user to review the spec before proceeding
- Written spec marks the user-stated non-goals as out of scope, naming each one
- For `vague-notifications`: output does not propose a full design or write a spec without first gathering requirements
- For `skip-design-rate-limiter`: output does NOT agree to skip scoping — it pushes back and asks a clarifying question
- For `skip-design-rate-limiter`: output acknowledges the user's urgency AND names a concrete risk of jumping in blind

## Optional

- Output includes a self-review step scanning for placeholders or contradictions
- Output offers what's-next options (implementation plan, scope another piece, etc.)
```

- [ ] **Step 3: Run fast tier**

```
make test ARGS="scope"
```

- [ ] **Step 4: Run deep tier**

```
make eval ARGS="scope"
```

- [ ] **Step 5: Commit**

```bash
git add tests/scope.json skills/scope/RUBRIC.md
git commit -m "evals: migrate scope to deterministic + RUBRIC.md"
```

---

### Task 25: Migrate `prompt-engineer`

**Files:**
- Modify: `tests/prompt-engineer.json`
- Create: `skills/prompt-engineer/RUBRIC.md`

- [ ] **Step 1: Rewrite `tests/prompt-engineer.json`**

Follow Appendix A § prompt-engineer. Key conversions:
- `contract-extraction-json`: `{"regex": "\`\`\`[\\s\\S]*?\`\`\`"}`, `{"contains_all": ["parties", "effective_date", "termination"]}`, `{"not_regex": "(?i)You are (a|an) (helpful|friendly)\\s*(AI\\s*)?assistant"}`. **Delete** the "Technique:" line assertion.
- `fix-bad-prompt`: `{"regex": "\`\`\`[\\s\\S]*?\`\`\`"}`
- `vague-summarization-request`: `{"regex": "\\?", "max": 2}`, `{"not_regex": "\`\`\`[\\s\\S]*?\`\`\`"}`

- [ ] **Step 2: Create `skills/prompt-engineer/RUBRIC.md`**

```markdown
# Prompt Engineer Rubric

Evaluated by `make eval`.

## Critical

- The produced prompt explicitly instructs the LLM to return only JSON with no prose wrapper, markdown fences, or commentary (for `contract-extraction-json`)
- The produced prompt specifies behavior when a required field is missing (null vs omit vs error) (for `contract-extraction-json`)
- The produced prompt addresses long or multi-page inputs (chunking, truncation, or explicit full-document processing) (for `contract-extraction-json`)
- Output contains a Changes section (or equivalent) explaining what was fixed and why (for `fix-bad-prompt`)
- The diagnosis identifies at least two of: vague role, contradictory instructions, politeness padding, missing output format (for `fix-bad-prompt`)
- The rewritten prompt removes "helpful AI assistant", "please", and "thank you" padding (for `fix-bad-prompt`)
- The rewritten prompt specifies a concrete output format (for `fix-bad-prompt`)
- The rewritten prompt resolves the "thorough but concise" contradiction (for `fix-bad-prompt`)
- For `vague-summarization-request`: output does not fabricate specifics the user did not provide

## Optional

- The rewritten prompt is shorter than the original (for `fix-bad-prompt`)
```

- [ ] **Step 3: Run fast tier**

```
make test ARGS="prompt-engineer"
```

- [ ] **Step 4: Run deep tier**

```
make eval ARGS="prompt-engineer"
```

- [ ] **Step 5: Commit**

```bash
git add tests/prompt-engineer.json skills/prompt-engineer/RUBRIC.md
git commit -m "evals: migrate prompt-engineer to deterministic + RUBRIC.md"
```

---

### Task 26: Migrate `skill-triggers` (core, no rubric)

**Files:**
- Modify: `tests/skill-triggers.json`

- [ ] **Step 1: Rewrite `tests/skill-triggers.json`**

Convert per Appendix A. All cases should end up fully deterministic. The `no-ghostwrite-on-fresh-draft` case uses `{"skill_not_invoked": "ghostwrite"}`.

- [ ] **Step 2: Run fast tier**

```
make test ARGS="skill-triggers"
```

Expected: all 6 cases pass deterministically, no LLM grader calls.

- [ ] **Step 3: Commit**

```bash
git add tests/skill-triggers.json
git commit -m "evals: migrate skill-triggers to fully deterministic"
```

---

### Task 27: Migrate `no-ai-attribution` (core, no rubric)

**Files:**
- Modify: `tests/no-ai-attribution.json`

- [ ] **Step 1: Rewrite `tests/no-ai-attribution.json`**

Per Appendix A, every assertion in the three cases converts to deterministic primitives (`not_regex`, `file_contains`, `contains`). No rubric.

- [ ] **Step 2: Run fast tier**

```
make test ARGS="no-ai-attribution"
```

Expected: all 3 cases pass.

- [ ] **Step 3: Commit**

```bash
git add tests/no-ai-attribution.json
git commit -m "evals: migrate no-ai-attribution to fully deterministic"
```

---

### Task 28: Full `make test` — all suites green

**Files:** (verification)

- [ ] **Step 1: Run everything**

```
time make test
```

Expected:
- All 6 suites discovered.
- All cases pass.
- Wall-clock under 90 seconds.
- Zero LLM grader calls (`grep` for grader trace if unsure).

- [ ] **Step 2: Run harness unit tests**

```
uv run pytest -v
```

- [ ] **Step 3: No commit** — verification gate.

If anything fails, fix inline and commit with a `fix:` prefix.

---

### Task 29: Full `make eval` — rubric grading green

**Files:** (verification)

- [ ] **Step 1: Run the deep tier**

```
time make eval
```

Expected:
- All suites run. Lift cases also run baselines.
- Rubric grading runs for the 4 skill suites with `RUBRIC.md`.
- `no-ai-attribution` and `skill-triggers` grade deterministically only (no rubric).
- All critical rubric items pass (or clearly actionable failures for followup).
- Wall-clock around 2 minutes.

- [ ] **Step 2: Review any rubric failures**

If a critical rubric item fails, decide: is the skill broken, or is the rubric item too strict? Fix the rubric item (or the skill) and rerun.

- [ ] **Step 3: No commit unless you adjusted a rubric** — then commit with `evals: tighten <skill> rubric`.

---

## Phase 6 — Delete Dead Code

Once every suite is migrated and both commands pass, the legacy code paths become dead. Remove them.

### Task 30: Delete legacy eval-file fields and discovery fallback

**Files:**
- Modify: `tests/support/harness/discovery.py`
- Modify: `tests/support/harness/models.py`
- Modify: `tests/support/harness/eval.schema.json`
- Modify: `tests/support/harness/tests/test_discovery.py`

- [ ] **Step 1: Update schema to reject dead fields**

In `eval.schema.json`:
- Remove `shared_assertions` from top-level properties.
- Remove `use_shared_assertions`, `grader_model`, `grader_input_limit` from per-case properties.
- Remove the `text` and `lint` variants from the `assertion` oneOf.

- [ ] **Step 2: Remove dead code from `discovery.py`**

- Delete the `shared_assertions` merge logic in `load_eval_file`.
- Delete the `use_shared_assertions` handling.
- Delete the `grader_model` / `grader_input_limit` reads.
- Delete the legacy nested-tree fallback (`tests/skills/` and `tests/core/` scans).

- [ ] **Step 3: Remove dead fields from `models.py`**

Drop `grader_model` and `grader_input_limit` from `EvalCase`.

- [ ] **Step 4: Update or delete tests that referenced the dead fields**

In `test_discovery.py`, remove any tests that verified `shared_assertions` merging. Replace with a test that a suite with `shared_assertions` at the top level fails schema validation (proof of deletion).

- [ ] **Step 5: Run harness unit tests**

```
uv run pytest tests/support/harness/tests/ -v
```

- [ ] **Step 6: Run full harness**

```
make test && make eval
```

- [ ] **Step 7: Commit**

```bash
git add tests/support/harness/ Makefile
git commit -m "harness: delete legacy shared_assertions, grader overrides, nested discovery"
```

---

### Task 31: Delete dead grader paths

**Files:**
- Modify: `tests/support/harness/grader.py`
- Modify: `tests/support/harness/orchestrator.py`
- Modify: `tests/support/harness/tests/test_grader.py`

- [ ] **Step 1: Remove text-assertion LLM grading**

Delete from `grader.py`:
- `GRADER_PROMPT`, `_OUTPUT_SCHEMA`
- `_build_prompt`
- `_grade_text_llm`
- `DEFAULT_STDOUT_LIMIT`, `DEFAULT_FILE_LIMIT`, `DEFAULT_TRACE_LIMIT`
- `_truncate_tail`
- `_parse_grader_fallback` (if not used by `grade_rubric`; otherwise keep)

Keep `grade_rubric` (which may still use `_truncate_tail` — move it there if so).

- [ ] **Step 2: Simplify `grade()`**

Replace the existing `grade()` with a deterministic-only version:

```python
async def grade(
    run: RunResult,
    assertions: list[dict],
    original_prompt: str = "",
) -> Grading:
    expectations = _grade_deterministic(assertions, run)
    return Grading.from_expectations(expectations)
```

Note: `grade()` is no longer actually async, but callers `await` it — keep the `async` keyword so the orchestrator call sites don't need changes.

- [ ] **Step 3: Delete `_grade_lint` alias and the `lint` primitive registration**

```python
# DELETE these:
def _grade_lint(...): ...

@_primitive("lint")
def _grade_lint_primitive(...): ...
```

- [ ] **Step 4: Update orchestrator**

Remove `original_prompt` reconstruction and `input_limit` / `grader_model` threading from `_run_one`. The `grade()` call is now simple:

```python
grading = await grade(run, plan.case.assertions)
```

- [ ] **Step 5: Remove dead grader tests**

From `test_grader.py`, delete:
- `test_truncate_tail_*`
- `test_build_prompt_*`
- `test_grade_merges_deterministic_and_text_in_order`
- `test_grader_passes_obviously_true_assertion`
- `test_grader_fails_obviously_false_assertion`
- `test_parse_grader_fallback_*`
- `test_lint_alias_still_works`

Keep everything that tests the deterministic primitives and `grade_rubric`.

- [ ] **Step 6: Run harness tests**

```
uv run pytest tests/support/harness/tests/ -v
```

- [ ] **Step 7: Run full harness**

```
make test && make eval
```

- [ ] **Step 8: Commit**

```bash
git add tests/support/harness/grader.py tests/support/harness/orchestrator.py tests/support/harness/tests/test_grader.py
git commit -m "harness: delete text-assertion LLM grading and lint alias"
```

---

### Task 32: Delete `--no-baseline` flag and WARN logic

**Files:**
- Modify: `tests/support/harness/__main__.py`
- Modify: `tests/support/harness/reporter.py`
- Modify: `tests/support/harness/tests/test_reporter.py`

- [ ] **Step 1: Delete `--no-baseline`**

In `__main__.py`, remove the `--no-baseline` argument. `run_evals` now derives baselines from tier:

```python
return asyncio.run(
    run_evals(
        project_root=project_root,
        names=args.names or None,
        baseline=(args.tier == "eval"),
        verbose=args.verbose,
        reporter=reporter,
        model=args.model,
        tier=args.tier,
    )
)
```

- [ ] **Step 2: Delete `LIFT_MIN_WITH_SKILL_RATE`**

Already removed in Task 17 if you followed the deep-tier reimplementation. Double-check and delete any remaining references.

- [ ] **Step 3: Delete any leftover WARN code paths**

Search for `WARN` and `saturated` in `reporter.py` — remove anything still lingering.

- [ ] **Step 4: Run tests**

```
uv run pytest tests/support/harness/tests/ -v
make test
make eval
```

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/__main__.py tests/support/harness/reporter.py tests/support/harness/tests/test_reporter.py
git commit -m "harness: delete --no-baseline flag and WARN lift logic"
```

---

## Phase 7 — Docs and Final Integration

### Task 33: Rewrite `docs/evals.md`

**Files:**
- Modify: `docs/evals.md`

- [ ] **Step 1: Rewrite `docs/evals.md`**

New structure:

```markdown
# Evals

Two commands, two questions.

## `make test` — Did I break anything?

Fast, deterministic, runs on every edit. Target <90s. No LLM grading.

\```
make test                    # all suites
make test ARGS="ghostwrite"   # single suite
\```

Every assertion grades in Python. If your eval uses a check that can't be expressed deterministically, it belongs in the rubric (see `make eval`).

## `make eval` — Is the skill still doing good work?

Deep, rubric-graded, runs pre-release or when iterating on a skill. Target ~2 min.

\```
make eval                    # all suites (with lift baselines)
make eval ARGS="summarize"   # one suite
\```

## Writing an eval

1. Create `tests/<name>.json`. If `<name>` matches a directory under `skills/`, the harness treats it as a skill suite; otherwise it's a core suite.
2. Each case has `id`, `turns`, and `assertions` (an array of deterministic primitives). Optional: `intent` (`lift` or `regression`), `files`, `cleanup`.
3. For skill suites that want quality grading in `make eval`, create `skills/<name>/RUBRIC.md` with `## Critical` and `## Optional` sections.

## Assertion vocabulary

See `references/specs/2026-04-08-eval-harness-plan-b-design.md` § Assertion vocabulary for the full list of 20 primitives across content, shape, trace, files, and the `script_name` escape hatch.

## Rubric format

\```markdown
# <Skill> Rubric

## Critical

- <testable outcome the output must satisfy>

## Optional

- <nice-to-have; reported but never fails the case>
\```

The grader returns `pass` / `fail` / `n/a` for each item. A case fails only if a critical item is `fail`. `n/a` is for items that legitimately don't apply (e.g. a refusal case).

## Fixtures

Put shared input files under `tests/fixtures/`. Reference them in a case via `"files": ["fixture-name.ext"]`.

## Artifacts

Every run writes artifacts under `tmp/evals/<timestamp>/` — one directory per suite/case/variant with the raw output, files written, and grading results.
```

- [ ] **Step 2: Commit**

```bash
git add docs/evals.md
git commit -m "docs: rewrite evals.md for two-tier harness"
```

---

### Task 34: Update `CLAUDE.md` and `AGENTS.md` Commands sections

**Files:**
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Update `CLAUDE.md`**

Find the `## Commands` section. Replace its contents with:

```markdown
## Commands

- **make test** -- Fast deterministic eval pass. <90s, no LLM grading. Run on every edit.
- **make eval** -- Deep eval pass with rubric grading. ~2 min. Run pre-release or when iterating on a skill.
- **make test-harness** -- Run the Python harness unit tests.
- See `docs/evals.md` for the full workflow.
```

- [ ] **Step 2: Update `AGENTS.md`**

Same change — find the Commands section and update it to match.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md AGENTS.md
git commit -m "docs: update Commands sections for make test + make eval split"
```

---

### Task 35: Final integration run

**Files:** (verification)

- [ ] **Step 1: Harness unit tests**

```
uv run pytest -v
```

Expected: everything passes.

- [ ] **Step 2: Fast tier**

```
time make test
```

Expected: all suites green, <90s.

- [ ] **Step 3: Deep tier**

```
time make eval
```

Expected: all suites green, ~2 min.

- [ ] **Step 4: Lint**

```
make lint
```

- [ ] **Step 5: Format**

```
make format
```

- [ ] **Step 6: Commit any lint/format fixes**

```bash
git status
# if changes:
git add -u
git commit -m "style: ruff fixes after refactor"
```

- [ ] **Step 7: Push the branch and open the PR**

```bash
git push -u origin eval-harness-refactor
gh pr create --base dev --title "Eval harness Plan B: two-tier refactor" --body "$(cat <<'EOF'
## Summary
- Split the eval harness into `make test` (fast, deterministic, <90s) and `make eval` (deep, rubric-graded, ~2min)
- Replaced most text assertions with 20 deterministic primitives
- Moved quality checks into per-skill `RUBRIC.md` files
- Flattened the tests tree to `tests/*.json` with skill/core auto-detection
- Deleted legacy `shared_assertions`, `grader_model` overrides, `--no-baseline`, and WARN lift logic

Spec: `references/specs/2026-04-08-eval-harness-plan-b-design.md`

## Test plan
- [ ] `make test-harness` passes
- [ ] `make test` green in under 90s
- [ ] `make eval` green in around 2 minutes
- [ ] Spot-check a rubric item: flip it to something clearly wrong, confirm `make eval` fails, revert
EOF
)"
```

---

## Appendix: Reference Pointers

- **Source spec:** `references/specs/2026-04-08-eval-harness-plan-b-design.md`
- **Assertion migration audit:** Appendix A of the spec
- **Pass rule for rubric grading:** spec § Rubric grader
- **Current harness layout:** `tests/support/harness/{runner,grader,discovery,orchestrator,reporter,models}.py`
- **Branch:** `eval-harness-refactor` (based off `dev`)
