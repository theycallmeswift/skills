# Eval Harness Review Fixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 7 issues found during code review of the two-tier eval harness implementation.

**Architecture:** All changes are in the worktree at `.worktrees/eval-harness-impl/` on the `eval-harness-impl` branch. Fixes are independent — each task is a self-contained commit. Tasks 1–5 are code fixes; Tasks 6–7 are docs/cleanup.

**Tech Stack:** Python 3.12, pytest, the eval harness at `tests/support/harness/`.

**Branch:** `eval-harness-impl` (worktree at `.worktrees/eval-harness-impl/`)

---

## File Structure

**Modified files:**
- `tests/scope.json` — add missing `files_written_include` and `file_contains` assertions
- `skills/scope/RUBRIC.md` — reconcile with new deterministic assertions (may remove duplicates)
- `tests/ghostwrite.json` — fix regex anchoring for greeting/sign-off
- `tests/support/harness/grader.py` — remove async from `grade()`
- `tests/support/harness/orchestrator.py` — update `grade()` call site
- `tests/support/harness/tests/test_grader.py` — add `final_message` to `_run_with_trace`
- `tests/support/harness/reporter.py` — handle baseline-only results in `_print_deep_summary`
- `tests/support/harness/tests/test_reporter.py` — add test for baseline-only case
- `docs/evals.md` — add assertion primitives cheat sheet

**Deleted:**
- `tests/skills/__init__.py` (and `tests/skills/` directory)

---

## Conventions

- **Commit style:** `type: short description` matching existing history.
- **Run tests with:** `cd .worktrees/eval-harness-impl && uv run pytest tests/support/harness/tests/ -v`
- **No attribution.** No `Co-Authored-By`, no AI mentions.

---

## Task 1: Add missing scope.json assertions for github-webhook-slack

**Files:**
- Modify: `.worktrees/eval-harness-impl/tests/scope.json`
- Modify: `.worktrees/eval-harness-impl/skills/scope/RUBRIC.md`

The spec (Appendix A § scope, items #3, #8–13) calls for deterministic assertions that catch spec content regressions in `make test`. Currently only 4 exclusion assertions exist. The `files_written_include` and `file_contains` primitives were built for this but go unused.

- [ ] **Step 1: Add deterministic assertions to scope.json**

Replace the `github-webhook-slack` assertions array with:

```json
"assertions": [
    {"files_written_include": "references/specs/*.md"},
    {"files_written_exclude": "package.json"},
    {"files_written_exclude": "*.py"},
    {"files_written_exclude": "*.js"},
    {"files_written_exclude": "*.ts"},
    {"file_contains": {"path": "references/specs/*.md", "regex": "(?i)(allowlist|routing table|repo.{0,10}channel)"}},
    {"file_contains": {"path": "references/specs/*.md", "regex": "(?i)(Redis|BullMQ|persistent queue|durable queue)"}},
    {"file_contains": {"path": "references/specs/*.md", "text": "opened"}},
    {"file_contains": {"path": "references/specs/*.md", "text": "ready_for_review"}},
    {"file_contains": {"path": "references/specs/*.md", "text": "closed"}},
    {"file_contains": {"path": "references/specs/*.md", "regex": "(?i)out of scope"}},
    {"file_contains": {"path": "references/specs/*.md", "text": "Fly.io"}},
    {"file_contains": {"path": "references/specs/*.md", "text": "Node.js"}},
    {"file_contains": {"path": "references/specs/*.md", "regex": "(?i)YAML"}}
]
```

This matches spec items #3 (files_written_include), #4 (4× exclude), #8 (routing), #9 (durable queue), #10 (3× event types), #11 (out of scope), #12 (Fly.io + Node.js), #13 (YAML).

- [ ] **Step 2: Reconcile RUBRIC.md**

The RUBRIC.md should keep rubric items that add semantic value beyond what the deterministic checks cover. Review each item:

- "A spec file is written to references/specs/ with a descriptive name" — the deterministic check catches existence but not "descriptive name". **Keep** in rubric, add "(descriptive filename)" qualifier.
- "Written spec mentions per-repo to channel routing" — deterministic regex catches surface signal. Rubric adds semantic judgment ("routing table covers all repos"). **Keep** as-is — the rubric phrasing is broader.
- "Written spec specifies a durable queue or retry mechanism" — same reasoning. **Keep**.
- "Written spec lists all three event types" — deterministic `text` checks are exact matches. Rubric version is redundant. **Remove** from rubric.
- "Written spec marks the user-stated non-goals as out of scope, naming each one" — deterministic only checks "out of scope" appears. Rubric checks *each* non-goal is named. **Keep** — rubric is stricter.
- "Written spec deployment target is Fly.io and the runtime is Node.js" — exact text matches cover this. **Remove** from rubric.
- "Written spec mentions YAML config loaded at startup" — deterministic catches "YAML". Rubric could check "loaded at startup, no hot reload". **Keep** with qualifier "(no hot reload mentioned)".

Updated `skills/scope/RUBRIC.md`:

```markdown
# Scope Rubric

Evaluated by `make eval`.

## Critical

- Output proposes 2-3 distinct approaches with trade-offs (when generating a design)
- Output includes a clear recommendation with reasoning for which approach to use
- Output asks the user to review the spec before proceeding
- A spec file is written to references/specs/ with a descriptive name (not a generic placeholder)
- Written spec mentions per-repo to channel routing (allowlist, routing table, or equivalent)
- Written spec specifies a durable queue or retry mechanism (Redis, BullMQ, persistent queue)
- Written spec marks the user-stated non-goals as out of scope, naming each one
- Written spec mentions YAML config loaded at startup with no hot reload
- For `vague-notifications`: output does not propose a full design or write a spec without first gathering requirements
- For `skip-design-rate-limiter`: output does NOT agree to skip scoping — it pushes back and asks a clarifying question
- For `skip-design-rate-limiter`: output acknowledges the user's urgency AND names a concrete risk of jumping in blind

## Optional

- Output includes a self-review step scanning for placeholders or contradictions
- Output offers what's-next options (implementation plan, scope another piece, etc.)
```

- [ ] **Step 3: Run unit tests**

```
cd .worktrees/eval-harness-impl && uv run pytest tests/support/harness/tests/ -v
```

Expected: all tests pass (scope.json schema validation, if any, is not unit-tested here — the schema is validated at discovery time).

- [ ] **Step 4: Commit**

```bash
cd .worktrees/eval-harness-impl
git add tests/scope.json skills/scope/RUBRIC.md
git commit -m "evals: add missing scope deterministic assertions and reconcile rubric"
```

---

## Task 2: Fix ghostwrite.json regex anchoring

**Files:**
- Modify: `.worktrees/eval-harness-impl/tests/ghostwrite.json`

The spec calls for `^`-anchored greeting and `$`-anchored sign-off. The model adds preamble before the rewritten content, so `^` anchoring on the full output will false-fail. The fix: use `(?m)` multiline flag so `^` matches the start of any line, not just the start of the string. This catches "greeting appears at the start of a line" without requiring it to be the very first character of the output.

For the sign-off, `$` with `(?m)` matches end-of-line, which is what we want — the sign-off should end a line near the end of the rewritten content.

- [ ] **Step 1: Update assertions in ghostwrite.json**

Change the `sponsor-email` assertions from:

```json
{"regex": "Hey, Sarah --"},
{"regex": "(- Swift|Happy Hacking,\\s*\\nSwift)"},
```

To:

```json
{"regex": "(?m)^Hey, Sarah --"},
{"regex": "(?m)(- Swift|Happy Hacking,\\s*\\nSwift)\\s*$"},
```

The `(?m)` flag makes `^` match start-of-line and `$` match end-of-line. This catches regressions where the greeting/sign-off appear mid-line (embedded in prose) while tolerating preamble before/after the rewritten content.

- [ ] **Step 2: Run unit tests**

```
cd .worktrees/eval-harness-impl && uv run pytest tests/support/harness/tests/ -v
```

Expected: all pass. The regex primitive test at `test_regex_passes_on_single_match` uses `^Hey, Sarah --` which will still match since the test input starts with that string.

- [ ] **Step 3: Commit**

```bash
cd .worktrees/eval-harness-impl
git add tests/ghostwrite.json
git commit -m "evals: anchor ghostwrite greeting/sign-off regexes with multiline flag"
```

---

## Task 3: Remove unnecessary async from grade()

**Files:**
- Modify: `.worktrees/eval-harness-impl/tests/support/harness/grader.py:569-574`
- Modify: `.worktrees/eval-harness-impl/tests/support/harness/orchestrator.py:60`

`grade()` is `async` but calls only `_grade_deterministic()` which is synchronous. The only caller is `orchestrator.py:60` which does `await grade(...)`.

- [ ] **Step 1: Make grade() synchronous**

In `grader.py`, change:

```python
async def grade(
    run: RunResult,
    assertions: list[dict],
) -> Grading:
    expectations = _grade_deterministic(assertions, run)
    return Grading.from_expectations(expectations)
```

To:

```python
def grade(
    run: RunResult,
    assertions: list[dict],
) -> Grading:
    expectations = _grade_deterministic(assertions, run)
    return Grading.from_expectations(expectations)
```

- [ ] **Step 2: Remove await at call site**

In `orchestrator.py`, change line 60:

```python
grading = await grade(run, plan.case.assertions)
```

To:

```python
grading = grade(run, plan.case.assertions)
```

- [ ] **Step 3: Run unit tests**

```
cd .worktrees/eval-harness-impl && uv run pytest tests/support/harness/tests/ -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
cd .worktrees/eval-harness-impl
git add tests/support/harness/grader.py tests/support/harness/orchestrator.py
git commit -m "harness: make grade() synchronous"
```

---

## Task 4: Add explicit final_message to _run_with_trace helper

**Files:**
- Modify: `.worktrees/eval-harness-impl/tests/support/harness/tests/test_grader.py:66-76`

`_run_with_trace` creates `RunResult` without `final_message`, relying on the dataclass default. Add it explicitly.

- [ ] **Step 1: Update _run_with_trace**

In `test_grader.py`, change:

```python
def _run_with_trace(trace):
    return RunResult(
        stdout="",
        files_written={},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.0,
        exit_code=0,
        tool_trace=trace,
        turn_count=1,
    )
```

To:

```python
def _run_with_trace(trace):
    return RunResult(
        stdout="",
        files_written={},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.0,
        exit_code=0,
        tool_trace=trace,
        turn_count=1,
        final_message="",
    )
```

- [ ] **Step 2: Run unit tests**

```
cd .worktrees/eval-harness-impl && uv run pytest tests/support/harness/tests/ -v
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
cd .worktrees/eval-harness-impl
git add tests/support/harness/tests/test_grader.py
git commit -m "tests: add explicit final_message to _run_with_trace helper"
```

---

## Task 5: Handle baseline-only results in _print_deep_summary

**Files:**
- Modify: `.worktrees/eval-harness-impl/tests/support/harness/reporter.py:90-93`
- Modify: `.worktrees/eval-harness-impl/tests/support/harness/tests/test_reporter.py`

Currently, if a lift case has a baseline but no `with_skill` variant (e.g., filtered out), the result silently vanishes. Add a warning line instead.

- [ ] **Step 1: Write a failing test**

Add to `test_reporter.py`:

```python
def test_deep_summary_baseline_only_prints_warning(capsys):
    """A lift case with only a baseline (no with_skill) should print, not vanish."""
    bl = _mk_result("ghostwrite", "sponsor-email", "baseline", "skill", passed=2, failed=1, intent="lift")
    buf = io.StringIO()
    with redirect_stdout(buf):
        _print_summary([bl], verbose=False)
    out = buf.getvalue()
    # Should mention the case somehow, not silently drop it.
    assert "sponsor-email" in out
```

- [ ] **Step 2: Run test to verify it fails**

```
cd .worktrees/eval-harness-impl && uv run pytest tests/support/harness/tests/test_reporter.py::test_deep_summary_baseline_only_prints_warning -v
```

Expected: FAIL — `sponsor-email` not found in output (the baseline is silently skipped).

- [ ] **Step 3: Fix _print_deep_summary**

In `reporter.py`, change the lift pairing loop (around line 90):

```python
    for (suite, case_id), variants in sorted(by_key.items()):
        ws = variants.get("with_skill")
        if ws is None:
            continue
```

To:

```python
    for (suite, case_id), variants in sorted(by_key.items()):
        ws = variants.get("with_skill")
        if ws is None:
            bl = variants.get("baseline")
            if bl and bl.plan.case.intent == "lift":
                lift_rows.append((suite, case_id, None, bl))
            continue
```

And update the lift table printer to handle `ws=None`:

```python
    if lift_rows:
        print(f"\n## Lift — {model_label}\n")
        for suite, case_id, ws, bl in lift_rows:
            if ws is None:
                bl_str = _fmt_score(bl.grading) if bl else "—"
                print(f"{suite:<20} {case_id:<32} with_skill=—{'':>12} baseline={bl_str:<12} skip")
                continue
            ws_str = _fmt_score(ws.grading)
            bl_str = _fmt_score(bl.grading) if bl else "—"
            failing = ws.run.exit_code != 0 or ws.grading.failed > 0
            if failing:
                exit_code = 1
            status = "fail" if failing else "ok"
            print(
                f"{suite:<20} {case_id:<32} with_skill={ws_str:<12} baseline={bl_str:<12} {status}"
            )
```

Note: baseline-only results do NOT set `exit_code = 1`. They're informational — the missing `with_skill` is the anomaly, not a failure.

- [ ] **Step 4: Run tests**

```
cd .worktrees/eval-harness-impl && uv run pytest tests/support/harness/tests/test_reporter.py -v
```

Expected: all pass including the new test.

- [ ] **Step 5: Commit**

```bash
cd .worktrees/eval-harness-impl
git add tests/support/harness/reporter.py tests/support/harness/tests/test_reporter.py
git commit -m "harness: show baseline-only lift results instead of silently dropping"
```

---

## Task 6: Add assertion primitives cheat sheet to docs/evals.md

**Files:**
- Modify: `.worktrees/eval-harness-impl/docs/evals.md`

Replace the "See spec" line with a compact inline reference.

- [ ] **Step 1: Replace the assertion vocabulary section**

Replace the current section:

```markdown
## Assertion vocabulary

See `references/specs/2026-04-08-eval-harness-plan-b-design.md` for the full list of primitives across content, shape, trace, files, and the `script_name` escape hatch.
```

With:

```markdown
## Assertion vocabulary

Every assertion is a JSON object with exactly one primitive key.

**Content** (checked against `final_message` by default; override with `"on": "stdout"` or `"on": "files.<glob>"`):

| Primitive | Example | Passes when |
|---|---|---|
| `regex` | `{"regex": "\\?", "min": 1, "max": 2}` | Match count is within `[min, max]`. Defaults: `min=1`, `max=∞`. |
| `not_regex` | `{"not_regex": "(?i)sorry"}` | Zero matches. |
| `contains` | `{"contains": "42"}` | Literal substring found. |
| `contains_all` | `{"contains_all": ["A", "B"]}` | Every literal found. |
| `not_contains` | `{"not_contains": "secret"}` | Literal absent. |

**Shape:**

| Primitive | Example | Passes when |
|---|---|---|
| `output_len_lte` | `{"output_len_lte": 600}` | Character count ≤ value. |
| `output_len_gte` | `{"output_len_gte": 100}` | Character count ≥ value. |
| `token_usage_lte` | `{"token_usage_lte": 50000}` | `input + output` tokens ≤ value. |

**Trace:**

| Primitive | Example | Passes when |
|---|---|---|
| `tool_called` | `{"tool_called": "scrape_as_markdown"}` | Tool name appears in trace (substring match). |
| `tool_not_called` | `{"tool_not_called": "WebFetch"}` | Tool name absent from trace. |
| `skill_invoked` | `{"skill_invoked": "ghostwrite"}` | `Skill` tool fired with matching skill (bare or prefixed). |
| `skill_not_invoked` | `{"skill_not_invoked": "ghostwrite"}` | No matching `Skill` tool invocation. |
| `trace_order` | `{"trace_order": ["Read", "Write"]}` | Tools appear in trace in this order (gaps ok). |
| `trace_count_lte` | `{"trace_count_lte": {"tool": "Bash", "n": 3}}` | Tool invocation count ≤ `n`. |
| `turn_count_lte` | `{"turn_count_lte": 1}` | Agent completed in ≤ `n` turns. |

**Files:**

| Primitive | Example | Passes when |
|---|---|---|
| `files_written_include` | `{"files_written_include": "refs/specs/*.md"}` | At least one written file matches glob. |
| `files_written_exclude` | `{"files_written_exclude": "package.json"}` | No written file matches glob. |
| `files_written_count` | `{"files_written_count": 0}` | Exact file count. |
| `file_contains` | `{"file_contains": {"path": "*.md", "text": "X"}}` | A file matching `path` glob contains `text` or matches `regex`. Set exactly one of `text` or `regex`. |

**Script:**

| Primitive | Example | Passes when |
|---|---|---|
| `script_name` | `{"script_name": "ghostwrite"}` | `skills/<name>/lint.py` exits 0 on the output. |
```

- [ ] **Step 2: Run unit tests** (sanity check — no code changed)

```
cd .worktrees/eval-harness-impl && uv run pytest tests/support/harness/tests/ -v
```

- [ ] **Step 3: Commit**

```bash
cd .worktrees/eval-harness-impl
git add docs/evals.md
git commit -m "docs: add assertion primitives cheat sheet to evals.md"
```

---

## Task 7: Delete tests/skills/__init__.py leftover

**Files:**
- Delete: `.worktrees/eval-harness-impl/tests/skills/__init__.py`
- Delete: `.worktrees/eval-harness-impl/tests/skills/` (directory)

- [ ] **Step 1: Verify the directory only contains __init__.py**

```bash
cd .worktrees/eval-harness-impl && ls -la tests/skills/
```

Expected: only `__init__.py` (0 bytes).

- [ ] **Step 2: Delete it**

```bash
cd .worktrees/eval-harness-impl && rm -rf tests/skills/
```

- [ ] **Step 3: Run unit tests**

```
cd .worktrees/eval-harness-impl && uv run pytest tests/support/harness/tests/ -v
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
cd .worktrees/eval-harness-impl
git add -A tests/skills/
git commit -m "cleanup: delete leftover tests/skills/ directory"
```
