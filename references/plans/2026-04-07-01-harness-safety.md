# Harness Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the eval harness from clobbering real repo files, ensure artifacts outlive the temp cwd, and lock both behaviors in with an orchestrator-level test.

**Architecture:** (1) Confine `cleanup` globs to a fixed allowlist of safe roots under `project_root` and reject unsafe patterns at load time. (2) Restructure `_run_one` so artifact persistence happens inside the `TemporaryDirectory` scope, preserving the cwd for potential copy. (3) Add the first end-to-end orchestrator test using fake runner/grader stubs.

**Tech Stack:** Python 3.12+, pytest, `asyncio`, `tempfile`, `pathlib`.

**Source:** `references/plans/2026-04-07-eval-harness-review-followups.md` items I6, I7, S2.

---

## Context the implementer needs

- The harness lives in `tests/support/harness/`. Unit tests are `test_*.py` in the same directory and run with `uv run pytest tests/support`.
- Eval cases can declare a `cleanup` list of glob patterns (see `tests/skills/scope/evals.json` — `"references/specs/2026-*-github-webhook-slack*.md"`). Today `_run_one` runs these globs against `project_root` with no constraints.
- Today the orchestrator runs each case inside a `tempfile.TemporaryDirectory` but exits that scope **before** writing artifacts. `run.files_written` has already captured file contents in memory so nothing currently breaks, but any future "copy raw files from cwd" change would silently break.
- `scope/github-webhook-slack` currently relies on `cleanup` to delete a spec file. Per I6 we need to know whether the spec lands inside `tmp/` (the harness cwd) or the real `project_root/references/specs/`. Task 1 verifies this.

---

## Task 1: Verify where scope writes the spec file

**Files:**
- Modify: none (investigation only)

- [ ] **Step 1: Run the scope eval once with extra tracing**

Run: `uv run python -m tests.support.harness scope --no-baseline`

After it finishes, inspect the latest `tmp/evals/<timestamp>/scope/eval-github-webhook-slack/with_skill/outputs/output.md` and `eval_metadata.json`. Also run:

```bash
git status references/specs/
```

Expected one of two outcomes:
- **(A) Spec landed in the temp cwd only.** `git status` is clean. `files_written` in the grading input contained the spec. → Current `cleanup` glob is a no-op safety net. Safe to restrict it aggressively.
- **(B) Spec landed in the real repo.** `git status` shows a new file under `references/specs/`. → This is a latent bug: the harness is supposed to be isolated. Note it, delete the file manually, and continue — Task 2 will prevent recurrence regardless.

- [ ] **Step 2: Record the finding**

Add one sentence to the top of this plan file (or jot in the PR description later) stating which outcome occurred. No commit needed yet.

---

## Task 2: Restrict cleanup globs to a safe allowlist

**Files:**
- Modify: `tests/support/harness/discovery.py` (validate at load time)
- Modify: `tests/support/harness/orchestrator.py` (use validated cleanup in `_run_one`)
- Test: `tests/support/harness/test_discovery.py`

The allowlist: `references/specs/`, `tmp/`, and the case's own temp cwd. Absolute paths and `..` segments rejected.

- [ ] **Step 1: Write the failing test**

Add to `tests/support/harness/test_discovery.py`:

```python
import json
import pytest
from pathlib import Path
from tests.support.harness.discovery import load_eval_file


def _write_suite(tmp_path: Path, cleanup: list[str]) -> Path:
    f = tmp_path / "evals.json"
    f.write_text(json.dumps({
        "name": "demo",
        "evals": [{
            "id": "c1",
            "turns": ["hi"],
            "cleanup": cleanup,
        }],
    }))
    return f


def test_cleanup_allows_safe_references_specs(tmp_path):
    f = _write_suite(tmp_path, ["references/specs/2026-*.md"])
    suite = load_eval_file(f, kind="skill")
    assert suite.cases[0].cleanup == ["references/specs/2026-*.md"]


def test_cleanup_allows_tmp_subpaths(tmp_path):
    f = _write_suite(tmp_path, ["tmp/foo/*"])
    suite = load_eval_file(f, kind="skill")
    assert suite.cases[0].cleanup == ["tmp/foo/*"]


def test_cleanup_rejects_absolute_path(tmp_path):
    f = _write_suite(tmp_path, ["/etc/passwd"])
    with pytest.raises(ValueError, match="absolute"):
        load_eval_file(f, kind="skill")


def test_cleanup_rejects_parent_traversal(tmp_path):
    f = _write_suite(tmp_path, ["../secrets/*"])
    with pytest.raises(ValueError, match=r"\.\."):
        load_eval_file(f, kind="skill")


def test_cleanup_rejects_unsafe_root(tmp_path):
    f = _write_suite(tmp_path, ["skills/*"])
    with pytest.raises(ValueError, match="allowed roots"):
        load_eval_file(f, kind="skill")


def test_cleanup_rejects_bare_star(tmp_path):
    f = _write_suite(tmp_path, ["*"])
    with pytest.raises(ValueError, match="allowed roots"):
        load_eval_file(f, kind="skill")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/support/harness/test_discovery.py -k cleanup -v`
Expected: all six new tests FAIL (current `load_eval_file` does no validation).

- [ ] **Step 3: Implement cleanup validation in discovery.py**

Add near the top of `tests/support/harness/discovery.py`, under the existing imports:

```python
_CLEANUP_ALLOWED_ROOTS = ("references/specs/", "tmp/")


def _validate_cleanup(patterns: list[str], source: Path) -> list[str]:
    """Reject cleanup globs that could touch files outside the safe allowlist.

    Patterns must be relative, contain no `..` segments, and start with one of
    the allowed roots. This runs at load time so bad configs fail loudly.
    """
    if not isinstance(patterns, list):
        raise ValueError(
            f"eval case in {source}: 'cleanup' must be a list of glob strings."
        )
    for p in patterns:
        if not isinstance(p, str) or not p:
            raise ValueError(
                f"eval case in {source}: cleanup entries must be non-empty strings."
            )
        if p.startswith("/"):
            raise ValueError(
                f"eval case in {source}: cleanup glob '{p}' is absolute; "
                f"use a path relative to project_root."
            )
        if ".." in Path(p).parts:
            raise ValueError(
                f"eval case in {source}: cleanup glob '{p}' contains '..'; "
                f"parent traversal is not allowed."
            )
        if not any(p.startswith(root) for root in _CLEANUP_ALLOWED_ROOTS):
            raise ValueError(
                f"eval case in {source}: cleanup glob '{p}' is not under an "
                f"allowed root. Allowed roots: {_CLEANUP_ALLOWED_ROOTS}."
            )
    return patterns
```

Then change the `EvalCase` construction inside `load_eval_file` from:

```python
cleanup=c.get("cleanup", []),
```

to:

```python
cleanup=_validate_cleanup(c.get("cleanup", []), path),
```

- [ ] **Step 4: Run the new tests**

Run: `uv run pytest tests/support/harness/test_discovery.py -k cleanup -v`
Expected: PASS (6/6).

- [ ] **Step 5: Run the full discovery suite**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: PASS for all tests including pre-existing ones.

- [ ] **Step 6: Spot-check that existing eval JSONs still load**

Run: `uv run python -c "from pathlib import Path; from tests.support.harness.discovery import discover_suites; print([s.name for s in discover_suites(Path('tests'))])"`
Expected: prints a list including `ghostwrite`, `scope`, `summarize`, `prompt-engineer`, `no-ai-attribution`, `skill-triggers`. No exceptions. If scope fails because its `cleanup` glob starts with `references/specs/`, confirm the allowlist check recognizes it.

- [ ] **Step 7: Commit**

```bash
git add tests/support/harness/discovery.py tests/support/harness/test_discovery.py
git commit -m "fix(harness): restrict cleanup globs to safe allowlist"
```

---

## Task 3: Fix `_run_one` so artifacts are persisted inside the tempdir scope

**Files:**
- Modify: `tests/support/harness/orchestrator.py`

The current structure is:

```python
with tempfile.TemporaryDirectory(prefix="eval-cwd-") as tmp:
    cwd = Path(tmp)
    run = await run_claude(...)
# tmp is GONE here
for pattern in plan.case.cleanup: ...
adir = _artifact_dir(...)
(adir / "outputs" / "output.md").write_text(run.stdout)
```

We want: cleanup and artifact persistence **inside** the `with` block, then exit.

- [ ] **Step 1: Move cleanup and artifact writes inside the `with` block**

Replace the body of `_run_one` from the `async with sem:` line through the `return result` line with this (keep the outer `async with sem:` and `reporter.case_started(plan)`):

```python
    async with sem:
        reporter.case_started(plan)
        with tempfile.TemporaryDirectory(prefix="eval-cwd-") as tmp:
            cwd = Path(tmp)
            run = await run_claude(
                turns=plan.turns,
                cwd=cwd,
                context_paths=plan.context_paths,
                project_root=project_root,
            )

            original_prompt = "\n\n".join(
                f"[turn {i}] {t}" for i, t in enumerate(plan.case.turns, start=1)
            )
            grading = await grade(
                run,
                plan.case.assertions,
                model=plan.case.grader_model,
                original_prompt=original_prompt,
            )

            adir = _artifact_dir(artifact_root, plan, run_id)
            (adir / "outputs").mkdir(exist_ok=True)
            (adir / "outputs" / "output.md").write_text(run.stdout)
            (adir / "files_written.json").write_text(
                json.dumps(run.files_written, indent=2)
            )
            (adir.parent / "eval_metadata.json").write_text(json.dumps({
                "id": plan.case_id,
                "turns": plan.case.turns,
                "turn_count": len(plan.case.turns),
                "assertions": plan.case.assertions,
            }, indent=2))
            (adir / "grading.json").write_text(json.dumps({
                "expectations": grading.expectations,
                "summary": {
                    "passed": grading.passed,
                    "failed": grading.failed,
                    "total": grading.total,
                    "pass_rate": (grading.passed / grading.total) if grading.total else 0.0,
                },
            }, indent=2))

            result = CaseResult(plan=plan, run=run, grading=grading)

        # Post-run cleanup: safe globs only (validated at discovery time).
        for pattern in plan.case.cleanup:
            for match in project_root.glob(pattern):
                if match.is_dir():
                    shutil.rmtree(match, ignore_errors=True)
                else:
                    match.unlink(missing_ok=True)

        reporter.case_finished(result)
        return result
```

Also add `import shutil` to the module-level imports at the top of `orchestrator.py` (remove the inline `import shutil; shutil.rmtree(...)`).

- [ ] **Step 2: Run the existing harness unit tests**

Run: `uv run pytest tests/support -v`
Expected: all pre-existing tests still PASS.

- [ ] **Step 3: Smoke-run a single eval**

Run: `uv run python -m tests.support.harness ghostwrite --no-baseline`
Expected: completes without exception; `tmp/evals/<latest>/ghostwrite/eval-sponsor-email/with_skill/` contains `outputs/output.md`, `grading.json`, and a new `files_written.json` (likely `{}` for ghostwrite).

- [ ] **Step 4: Commit**

```bash
git add tests/support/harness/orchestrator.py
git commit -m "fix(harness): persist artifacts inside tempdir scope"
```

---

## Task 4: Add orchestrator end-to-end test with fake runner/grader

**Files:**
- Create: `tests/support/harness/test_orchestrator.py`

This test monkey-patches `runner.run_claude` and `grader.grade` so we exercise `run_evals` without touching the real SDK. It asserts:
1. Each discovered plan produces an artifact directory with `output.md` and `grading.json`.
2. A cleanup glob under `references/specs/` is honored post-run.
3. Exit code is 0 when all assertions pass, 1 when any fail.

- [ ] **Step 1: Write the test file**

Create `tests/support/harness/test_orchestrator.py`:

```python
import asyncio
import json
from pathlib import Path

import pytest

from tests.support.harness import orchestrator
from tests.support.harness.models import Grading
from tests.support.harness.reporter import DotsReporter
from tests.support.harness.runner import RunResult


def _make_project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / "tests" / "skills" / "demo").mkdir(parents=True)
    (root / "skills" / "demo").mkdir(parents=True)
    (root / "skills" / "demo" / "SKILL.md").write_text("demo skill")
    (root / "references" / "specs").mkdir(parents=True)
    (root / "AGENTS.md").write_text("agents")
    (root / "tests" / "skills" / "demo" / "evals.json").write_text(json.dumps({
        "name": "demo",
        "evals": [
            {
                "id": "happy",
                "turns": ["do the thing"],
                "assertions": [{"text": "output says hello"}],
                "cleanup": ["references/specs/demo-*.md"],
            },
        ],
    }))
    # Seed a spec file that the cleanup glob should remove after the run.
    (root / "references" / "specs" / "demo-artifact.md").write_text("stale")
    return root


@pytest.fixture
def fake_run_and_grade(monkeypatch):
    async def fake_run_claude(turns, cwd, context_paths, project_root, timeout_s=300):
        return RunResult(
            stdout="hello world",
            files_written={},
            input_tokens=1,
            output_tokens=1,
            duration_s=0.01,
            exit_code=0,
            tool_trace=[],
            turn_count=len(turns),
        )

    async def fake_grade(run, assertions, model=None, original_prompt=""):
        exps = [{"text": a["text"], "passed": True, "evidence": "ok"} for a in assertions]
        return Grading.from_expectations(exps)

    monkeypatch.setattr(orchestrator, "run_claude", fake_run_claude)
    monkeypatch.setattr(orchestrator, "grade", fake_grade)


def test_run_evals_writes_artifacts_and_honors_cleanup(tmp_path, fake_run_and_grade):
    root = _make_project(tmp_path)
    reporter = DotsReporter()

    exit_code = asyncio.run(
        orchestrator.run_evals(
            project_root=root,
            names=["demo"],
            baseline=False,
            verbose=False,
            reporter=reporter,
        )
    )

    assert exit_code == 0

    run_dirs = list((root / "tmp" / "evals").iterdir())
    assert len(run_dirs) == 1
    case_dir = run_dirs[0] / "demo" / "eval-happy" / "with_skill"
    assert (case_dir / "outputs" / "output.md").read_text() == "hello world"
    grading = json.loads((case_dir / "grading.json").read_text())
    assert grading["summary"]["passed"] == 1
    assert grading["summary"]["failed"] == 0

    assert not (root / "references" / "specs" / "demo-artifact.md").exists()


def test_run_evals_returns_1_when_assertion_fails(tmp_path, monkeypatch):
    root = _make_project(tmp_path)

    async def fake_run_claude(turns, cwd, context_paths, project_root, timeout_s=300):
        return RunResult(
            stdout="nope", files_written={}, input_tokens=0, output_tokens=0,
            duration_s=0.0, exit_code=0, tool_trace=[], turn_count=1,
        )

    async def fake_grade(run, assertions, model=None, original_prompt=""):
        exps = [{"text": a["text"], "passed": False, "evidence": "no"} for a in assertions]
        return Grading.from_expectations(exps)

    monkeypatch.setattr(orchestrator, "run_claude", fake_run_claude)
    monkeypatch.setattr(orchestrator, "grade", fake_grade)

    exit_code = asyncio.run(
        orchestrator.run_evals(
            project_root=root, names=["demo"], baseline=False,
            verbose=False, reporter=DotsReporter(),
        )
    )
    assert exit_code == 1
```

- [ ] **Step 2: Run the new test**

Run: `uv run pytest tests/support/harness/test_orchestrator.py -v`
Expected: both tests PASS.

- [ ] **Step 3: Run the full harness test suite as a regression check**

Run: `uv run pytest tests/support -v`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/support/harness/test_orchestrator.py
git commit -m "test(harness): add orchestrator end-to-end test with fake runner"
```

---

## Verification

- [ ] `uv run pytest tests/support -v` — all green
- [ ] `uv run python -m tests.support.harness ghostwrite --no-baseline` — completes, writes artifacts including `files_written.json`
- [ ] Spot-check one `tmp/evals/<latest>/…/with_skill/` directory contains `outputs/output.md`, `grading.json`, `files_written.json`
- [ ] `git status references/specs/` clean after running scope eval (no stray spec files from the harness)

## Out of scope for this plan

- Deterministic tool-trace assertions (plan 02)
- Eval content gaps (plans 03, 04)
- Grader truncation (plan 05)
- Code-quality sweep / ruff / mypy (plan 06)
