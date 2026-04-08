# Eval Harness Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `/eval` Claude Code workflow with a deterministic Python harness (`make test`) that runs MechaSwift skill and core evals in parallel via the Claude Agent SDK, with live `rich`/dots reporting.

**Architecture:** A `tests/support/harness/` Python package run from the terminal (not Claude Code) shells out per case via the Claude Agent SDK. Eval files live under a top-level `tests/` tree mirroring the project (`tests/skills/<name>/evals.json`, `tests/core/<name>.json`). A skill-agnostic `runner` copies context paths into a temp cwd and runs a prompt; `discovery` is the only layer that knows about skills, baselines, and core evals; `grader` runs an LLM judge per case via structured output; `reporter` auto-detects TTY vs CI.

**Tech Stack:** Python 3.11+, `uv` for dependency management, `claude-agent-sdk` (Claude runs + grader), `rich` (live table), stdlib `asyncio` for concurrency, `pytest` for harness unit tests.

**Spec:** `references/specs/2026-04-07-eval-harness-overhaul.md`

---

## Migration notes (read before starting)

Existing files this plan deletes or migrates:

- `evals/no-ai-attribution.json` → `tests/core/no-ai-attribution.json` (rename `eval_name` → `name`, ids 1/2 → slugs, drop `assertions[].type`)
- `skills/ghostwrite/evals/evals.json` → `tests/skills/ghostwrite/evals.json` (rename `skill_name` → `name`, slugify ids, drop `assertions[].type`, drop `expected_output`)
- `skills/scope/evals/evals.json` → `tests/skills/scope/evals.json` (same)
- `skills/summarize/evals/evals.json` → `tests/skills/summarize/evals.json` (same; also move `test-paper.pdf` fixture)
- `skills/prompt-engineer/evals/evals.json` → `tests/skills/prompt-engineer/evals.json` (same)
- `.claude/commands/eval.md` → deleted
- `docs/evals.md` → rewritten

`AGENTS.md` is the canonical context file; `CLAUDE.md` is a symlink to it. The harness should resolve symlinks when copying.

The `tmp/` directory is already gitignored.

---

## Task 1: Project scaffolding (uv, pyproject, gitignore)

**Files:**
- Create: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/support/__init__.py`
- Create: `tests/support/harness/__init__.py`
- Modify: `.gitignore`

- [ ] **Step 1: Initialize uv project with pyproject.toml**

Create `pyproject.toml`:

```toml
[project]
name = "mechaswift-tests"
version = "0.1.0"
description = "Eval harness for MechaSwift skills"
requires-python = ">=3.11"
dependencies = [
    "claude-agent-sdk>=0.1.0",
    "rich>=13.7.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests/support"]
python_files = ["test_*.py"]
```

- [ ] **Step 2: Create empty package init files**

```bash
mkdir -p tests/support/harness
touch tests/__init__.py tests/support/__init__.py tests/support/harness/__init__.py
```

- [ ] **Step 3: Update .gitignore**

Append to `.gitignore`:

```
# Python harness
__pycache__/
*.pyc
.pytest_cache/
.venv/
uv.lock
```

(Note: `uv.lock` is debatable — for an internal tool checking it in is fine. Leave it gitignored for v1; flip later if needed.)

- [ ] **Step 4: Resolve dependencies**

Run: `uv sync`
Expected: Creates `.venv/`, installs `claude-agent-sdk`, `rich`, `pytest`, `pytest-asyncio`. No errors.

- [ ] **Step 5: Verify the package imports**

Run: `uv run python -c "import tests.support.harness; print('ok')"`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tests/ .gitignore
git commit -m "chore: scaffold tests/support/harness package with uv"
```

---

## Task 2: Eval file format + discovery (data layer, no SDK calls)

This task builds the in-memory representation of an eval suite and the discovery walker. No Claude calls yet — pure Python over JSON files. We'll write the data classes, then a parser, then the discovery walker, all TDD.

**Files:**
- Create: `tests/support/harness/models.py`
- Create: `tests/support/harness/discovery.py`
- Create: `tests/support/harness/test_discovery.py`
- Create: `tests/support/fixtures/sample-skill-eval.json` (test fixture)
- Create: `tests/support/fixtures/sample-core-eval.json` (test fixture)

- [ ] **Step 1: Write the failing test for parsing a skill eval file**

Create `tests/support/fixtures/sample-skill-eval.json`:

```json
{
  "name": "ghostwrite",
  "evals": [
    {
      "id": "sponsor-email",
      "prompt": "Rewrite this in Swift's voice: hello world",
      "files": [],
      "assertions": [
        { "text": "Output is short" }
      ]
    }
  ]
}
```

Create `tests/support/fixtures/sample-core-eval.json`:

```json
{
  "name": "no-ai-attribution",
  "evals": [
    {
      "id": "throwaway-commit",
      "prompt": "Make a commit in tmp/fake-repo",
      "files": [],
      "grader_model": "claude-haiku-4-5-20251001",
      "cleanup": ["tmp/fake-repo"],
      "assertions": [
        { "text": "Commit has no AI attribution" }
      ]
    }
  ]
}
```

Create `tests/support/harness/test_discovery.py`:

```python
from pathlib import Path
from tests.support.harness.discovery import load_eval_file, EvalSuite, EvalCase

FIXTURES = Path(__file__).parent.parent / "fixtures"

def test_load_skill_eval_file():
    suite = load_eval_file(FIXTURES / "sample-skill-eval.json", kind="skill")
    assert isinstance(suite, EvalSuite)
    assert suite.name == "ghostwrite"
    assert suite.kind == "skill"
    assert len(suite.cases) == 1
    case = suite.cases[0]
    assert case.id == "sponsor-email"
    assert case.prompt.startswith("Rewrite this")
    assert case.files == []
    assert case.assertions == [{"text": "Output is short"}]
    assert case.grader_model is None
    assert case.cleanup == []

def test_load_core_eval_file():
    suite = load_eval_file(FIXTURES / "sample-core-eval.json", kind="core")
    assert suite.kind == "core"
    case = suite.cases[0]
    assert case.grader_model == "claude-haiku-4-5-20251001"
    assert case.cleanup == ["tmp/fake-repo"]
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.support.harness.discovery'`

- [ ] **Step 3: Create the models module**

Create `tests/support/harness/models.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

EvalKind = Literal["skill", "core"]

@dataclass
class EvalCase:
    id: str
    prompt: str
    files: list[str] = field(default_factory=list)
    assertions: list[dict] = field(default_factory=list)
    grader_model: str | None = None
    cleanup: list[str] = field(default_factory=list)

@dataclass
class EvalSuite:
    name: str
    kind: EvalKind
    source_path: Path
    cases: list[EvalCase]
```

- [ ] **Step 4: Implement load_eval_file**

Create `tests/support/harness/discovery.py`:

```python
import json
from pathlib import Path
from .models import EvalCase, EvalSuite, EvalKind

def load_eval_file(path: Path, kind: EvalKind) -> EvalSuite:
    data = json.loads(path.read_text())
    cases = [
        EvalCase(
            id=str(c["id"]),
            prompt=c["prompt"],
            files=c.get("files", []),
            assertions=c.get("assertions", []),
            grader_model=c.get("grader_model"),
            cleanup=c.get("cleanup", []),
        )
        for c in data["evals"]
    ]
    return EvalSuite(
        name=data["name"],
        kind=kind,
        source_path=path,
        cases=cases,
    )
```

- [ ] **Step 5: Run tests to confirm pass**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: 2 passed.

- [ ] **Step 6: Write the failing test for tree discovery**

Append to `tests/support/harness/test_discovery.py`:

```python
def test_discover_walks_tests_tree(tmp_path):
    # Build a fake tests/ tree
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    (tmp_path / "tests" / "core").mkdir(parents=True)
    (tmp_path / "tests" / "core" / "no-ai-attribution.json").write_text(
        (FIXTURES / "sample-core-eval.json").read_text()
    )

    from tests.support.harness.discovery import discover_suites
    suites = discover_suites(tmp_path / "tests")
    assert len(suites) == 2
    by_name = {s.name: s for s in suites}
    assert by_name["ghostwrite"].kind == "skill"
    assert by_name["no-ai-attribution"].kind == "core"

def test_discover_filters_by_name(tmp_path):
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    (tmp_path / "tests" / "core").mkdir(parents=True)
    (tmp_path / "tests" / "core" / "no-ai-attribution.json").write_text(
        (FIXTURES / "sample-core-eval.json").read_text()
    )

    from tests.support.harness.discovery import discover_suites
    suites = discover_suites(tmp_path / "tests", names=["ghostwrite"])
    assert len(suites) == 1
    assert suites[0].name == "ghostwrite"
```

- [ ] **Step 7: Run tests to confirm failure**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: 2 fail with `ImportError: cannot import name 'discover_suites'`.

- [ ] **Step 8: Implement discover_suites**

Append to `tests/support/harness/discovery.py`:

```python
def discover_suites(tests_root: Path, names: list[str] | None = None) -> list[EvalSuite]:
    suites: list[EvalSuite] = []

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

- [ ] **Step 9: Run all discovery tests**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: 4 passed.

- [ ] **Step 10: Commit**

```bash
git add tests/support/harness/models.py tests/support/harness/discovery.py tests/support/harness/test_discovery.py tests/support/fixtures/
git commit -m "feat(harness): add eval file models and discovery walker"
```

---

## Task 3: Run plan builder (assembles context_paths and prompts)

The discovery layer turns a `EvalSuite` into a list of `RunPlan` objects. Each `RunPlan` is one subprocess invocation. A skill case produces two `RunPlan`s (with-skill + baseline) unless `--no-baseline` is set; a core case produces one.

**Files:**
- Modify: `tests/support/harness/models.py`
- Modify: `tests/support/harness/discovery.py`
- Modify: `tests/support/harness/test_discovery.py`

- [ ] **Step 1: Write failing tests for run plan generation**

Append to `tests/support/harness/test_discovery.py`:

```python
def test_build_run_plans_skill_with_baseline(tmp_path):
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    # Pretend AGENTS.md and the skill dir exist at the project root
    (tmp_path / "AGENTS.md").write_text("# project context")
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "skills" / "ghostwrite" / "SKILL.md").write_text("# skill")

    from tests.support.harness.discovery import discover_suites, build_run_plans
    suites = discover_suites(tmp_path / "tests")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=True)

    # one skill case, baseline=True → two plans
    assert len(plans) == 2
    by_variant = {p.variant: p for p in plans}
    assert "with_skill" in by_variant and "baseline" in by_variant

    with_skill = by_variant["with_skill"]
    assert with_skill.suite_name == "ghostwrite"
    assert with_skill.case_id == "sponsor-email"
    assert with_skill.prompt.startswith("Before responding, read and follow skills/ghostwrite/SKILL.md.")
    assert (tmp_path / "skills" / "ghostwrite") in with_skill.context_paths
    assert (tmp_path / "AGENTS.md") in with_skill.context_paths

    baseline = by_variant["baseline"]
    assert baseline.prompt == "Rewrite this in Swift's voice: hello world"
    assert (tmp_path / "skills" / "ghostwrite") not in baseline.context_paths
    assert (tmp_path / "AGENTS.md") in baseline.context_paths

def test_build_run_plans_skill_no_baseline(tmp_path):
    (tmp_path / "tests" / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "tests" / "skills" / "ghostwrite" / "evals.json").write_text(
        (FIXTURES / "sample-skill-eval.json").read_text()
    )
    (tmp_path / "AGENTS.md").write_text("# project context")
    (tmp_path / "skills" / "ghostwrite").mkdir(parents=True)
    (tmp_path / "skills" / "ghostwrite" / "SKILL.md").write_text("# skill")

    from tests.support.harness.discovery import discover_suites, build_run_plans
    suites = discover_suites(tmp_path / "tests")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=False)
    assert len(plans) == 1
    assert plans[0].variant == "with_skill"

def test_build_run_plans_core(tmp_path):
    (tmp_path / "tests" / "core").mkdir(parents=True)
    (tmp_path / "tests" / "core" / "no-ai-attribution.json").write_text(
        (FIXTURES / "sample-core-eval.json").read_text()
    )
    (tmp_path / "AGENTS.md").write_text("# project context")

    from tests.support.harness.discovery import discover_suites, build_run_plans
    suites = discover_suites(tmp_path / "tests")
    plans = build_run_plans(suites, project_root=tmp_path, baseline=True)
    assert len(plans) == 1
    plan = plans[0]
    assert plan.variant == "run"
    assert plan.suite_name == "no-ai-attribution"
    assert plan.case_id == "throwaway-commit"
    assert (tmp_path / "AGENTS.md") in plan.context_paths
```

- [ ] **Step 2: Run tests to confirm failure**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: 3 new tests fail with `ImportError: cannot import name 'build_run_plans'`.

- [ ] **Step 3: Add RunPlan model**

Append to `tests/support/harness/models.py`:

```python
RunVariant = Literal["with_skill", "baseline", "run"]

@dataclass
class RunPlan:
    suite_name: str
    suite_kind: EvalKind
    case_id: str
    variant: RunVariant
    prompt: str
    context_paths: list[Path]
    case: EvalCase  # full case for grader/reporter access
```

- [ ] **Step 4: Implement build_run_plans**

Append to `tests/support/harness/discovery.py`:

```python
from .models import RunPlan

SKILL_PREAMBLE = "Before responding, read and follow skills/{name}/SKILL.md.\n\n"

def build_run_plans(
    suites: list[EvalSuite],
    project_root: Path,
    baseline: bool,
) -> list[RunPlan]:
    plans: list[RunPlan] = []
    agents_md = project_root / "AGENTS.md"

    for suite in suites:
        for case in suite.cases:
            eval_dir = suite.source_path.parent
            case_files = [eval_dir / f for f in case.files]

            if suite.kind == "skill":
                skill_dir = project_root / "skills" / suite.name
                with_skill_paths = [skill_dir, agents_md, *case_files]
                with_skill_prompt = SKILL_PREAMBLE.format(name=suite.name) + case.prompt
                plans.append(RunPlan(
                    suite_name=suite.name,
                    suite_kind=suite.kind,
                    case_id=case.id,
                    variant="with_skill",
                    prompt=with_skill_prompt,
                    context_paths=with_skill_paths,
                    case=case,
                ))
                if baseline:
                    plans.append(RunPlan(
                        suite_name=suite.name,
                        suite_kind=suite.kind,
                        case_id=case.id,
                        variant="baseline",
                        prompt=case.prompt,
                        context_paths=[agents_md, *case_files],
                        case=case,
                    ))
            else:  # core
                plans.append(RunPlan(
                    suite_name=suite.name,
                    suite_kind=suite.kind,
                    case_id=case.id,
                    variant="run",
                    prompt=case.prompt,
                    context_paths=[agents_md, *case_files],
                    case=case,
                ))

    return plans
```

- [ ] **Step 5: Run tests to confirm pass**

Run: `uv run pytest tests/support/harness/test_discovery.py -v`
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add tests/support/harness/models.py tests/support/harness/discovery.py tests/support/harness/test_discovery.py
git commit -m "feat(harness): build run plans with skill/baseline/core variants"
```

---

## Task 4: Runner — context_paths copy + cwd setup (no SDK call yet)

Before wiring the SDK, build the deterministic file-handling primitives the runner needs: copying `context_paths` into a temp cwd, resolving symlinks, and snapshotting file changes after a run.

**Files:**
- Create: `tests/support/harness/runner.py`
- Create: `tests/support/harness/test_runner.py`

- [ ] **Step 1: Write failing test for context_paths copy**

Create `tests/support/harness/test_runner.py`:

```python
from pathlib import Path

def test_copy_context_files_and_dirs(tmp_path):
    # Source layout
    src = tmp_path / "src"
    src.mkdir()
    (src / "AGENTS.md").write_text("# agents")
    skill = src / "skills" / "ghostwrite"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill")
    (skill / "references").mkdir()
    (skill / "references" / "voice.md").write_text("# voice")

    cwd = tmp_path / "cwd"
    cwd.mkdir()

    from tests.support.harness.runner import copy_context_paths
    copy_context_paths(
        [src / "AGENTS.md", src / "skills" / "ghostwrite"],
        project_root=src,
        cwd=cwd,
    )

    assert (cwd / "AGENTS.md").read_text() == "# agents"
    assert (cwd / "skills" / "ghostwrite" / "SKILL.md").read_text() == "# skill"
    assert (cwd / "skills" / "ghostwrite" / "references" / "voice.md").read_text() == "# voice"

def test_copy_context_resolves_symlinks(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "AGENTS.md").write_text("# real")
    (src / "CLAUDE.md").symlink_to(src / "AGENTS.md")

    cwd = tmp_path / "cwd"
    cwd.mkdir()

    from tests.support.harness.runner import copy_context_paths
    copy_context_paths([src / "CLAUDE.md"], project_root=src, cwd=cwd)

    target = cwd / "CLAUDE.md"
    assert target.read_text() == "# real"
    assert not target.is_symlink()
```

- [ ] **Step 2: Run to confirm failure**

Run: `uv run pytest tests/support/harness/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement copy_context_paths**

Create `tests/support/harness/runner.py`:

```python
import shutil
from pathlib import Path

def copy_context_paths(paths: list[Path], project_root: Path, cwd: Path) -> None:
    """Copy each path into cwd preserving its position relative to project_root.

    Symlinks are resolved (we copy the target, not the link).
    """
    for src in paths:
        resolved = src.resolve()
        rel = src.relative_to(project_root) if src.is_absolute() else src
        dest = cwd / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if resolved.is_dir():
            shutil.copytree(resolved, dest, symlinks=False, dirs_exist_ok=True)
        else:
            shutil.copy2(resolved, dest)
```

- [ ] **Step 4: Run tests to confirm pass**

Run: `uv run pytest tests/support/harness/test_runner.py -v`
Expected: 2 passed.

- [ ] **Step 5: Write failing test for snapshot_new_files**

Append to `tests/support/harness/test_runner.py`:

```python
def test_snapshot_captures_only_new_or_modified(tmp_path):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "existing.md").write_text("original")

    from tests.support.harness.runner import snapshot_files, capture_changes
    before = snapshot_files(cwd)

    # Simulate the agent modifying one file and creating another
    (cwd / "existing.md").write_text("modified")
    (cwd / "new.md").write_text("brand new")
    (cwd / "subdir").mkdir()
    (cwd / "subdir" / "deep.md").write_text("deep")

    after = capture_changes(cwd, before)
    assert set(after.keys()) == {"existing.md", "new.md", "subdir/deep.md"}
    assert after["existing.md"] == "modified"
    assert after["new.md"] == "brand new"
    assert after["subdir/deep.md"] == "deep"
```

- [ ] **Step 6: Run to confirm failure**

Run: `uv run pytest tests/support/harness/test_runner.py::test_snapshot_captures_only_new_or_modified -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 7: Implement snapshot/capture_changes**

Append to `tests/support/harness/runner.py`:

```python
def snapshot_files(cwd: Path) -> dict[str, tuple[float, int]]:
    """Return {relative_path: (mtime, size)} for every file under cwd."""
    snap: dict[str, tuple[float, int]] = {}
    for p in cwd.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(cwd))
            stat = p.stat()
            snap[rel] = (stat.st_mtime, stat.st_size)
    return snap

def capture_changes(cwd: Path, before: dict[str, tuple[float, int]]) -> dict[str, str]:
    """Return {relative_path: content} for files added or modified since `before`."""
    changes: dict[str, str] = {}
    for p in cwd.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(cwd))
        stat = p.stat()
        prev = before.get(rel)
        if prev is None or prev != (stat.st_mtime, stat.st_size):
            try:
                changes[rel] = p.read_text()
            except UnicodeDecodeError:
                changes[rel] = f"<binary file, {stat.st_size} bytes>"
    return changes
```

- [ ] **Step 8: Run all runner tests**

Run: `uv run pytest tests/support/harness/test_runner.py -v`
Expected: 3 passed.

- [ ] **Step 9: Commit**

```bash
git add tests/support/harness/runner.py tests/support/harness/test_runner.py
git commit -m "feat(harness): add context copy and file snapshot helpers"
```

---

## Task 5: RunResult dataclass + Claude SDK runner

This is the first task that hits the network. Test it with a tiny live call gated by `ANTHROPIC_API_KEY` (skip when missing) — we don't try to mock the SDK.

**Files:**
- Modify: `tests/support/harness/runner.py`
- Modify: `tests/support/harness/test_runner.py`

- [ ] **Step 1: Add RunResult dataclass**

Append to `tests/support/harness/runner.py`:

```python
import asyncio
import os
import tempfile
import time
from dataclasses import dataclass, field

@dataclass
class RunResult:
    stdout: str
    files_written: dict[str, str]
    input_tokens: int
    output_tokens: int
    duration_s: float
    exit_code: int  # 0 = success, 1 = error, 124 = timeout
    tool_trace: list[dict] = field(default_factory=list)
    error: str | None = None
```

- [ ] **Step 2: Implement run_claude using the Agent SDK**

Append to `tests/support/harness/runner.py`:

```python
async def run_claude(
    prompt: str,
    cwd: Path,
    context_paths: list[Path],
    project_root: Path,
    timeout_s: float = 300,
) -> RunResult:
    """Run a single prompt through Claude Agent SDK in an isolated cwd."""
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ToolUseBlock, ResultMessage

    copy_context_paths(context_paths, project_root=project_root, cwd=cwd)
    before = snapshot_files(cwd)

    stdout_parts: list[str] = []
    tool_trace: list[dict] = []
    input_tokens = 0
    output_tokens = 0
    error: str | None = None
    exit_code = 0

    options = ClaudeAgentOptions(cwd=str(cwd))

    start = time.monotonic()
    try:
        async with asyncio.timeout(timeout_s):
            async for message in query(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, ToolUseBlock):
                            tool_trace.append({
                                "name": block.name,
                                "input": block.input,
                            })
                        elif hasattr(block, "text"):
                            stdout_parts.append(block.text)
                elif isinstance(message, ResultMessage):
                    usage = getattr(message, "usage", None) or {}
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
    except TimeoutError:
        exit_code = 124
        error = f"timed out after {timeout_s}s"
    except Exception as e:  # noqa: BLE001
        exit_code = 1
        error = f"{type(e).__name__}: {e}"

    duration = time.monotonic() - start
    files_written = capture_changes(cwd, before)

    return RunResult(
        stdout="".join(stdout_parts),
        files_written=files_written,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_s=duration,
        exit_code=exit_code,
        tool_trace=tool_trace,
        error=error,
    )

async def run_codex(*args, **kwargs) -> RunResult:
    raise NotImplementedError("Codex runner not implemented yet")

async def run_gemini(*args, **kwargs) -> RunResult:
    raise NotImplementedError("Gemini runner not implemented yet")
```

- [ ] **Step 3: Write a live smoke test gated on env var**

Append to `tests/support/harness/test_runner.py`:

```python
import os
import pytest

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    reason="requires Claude credentials",
)
async def test_run_claude_smoke(tmp_path):
    from tests.support.harness.runner import run_claude
    result = await run_claude(
        prompt="Reply with exactly the word 'pong' and nothing else.",
        cwd=tmp_path,
        context_paths=[],
        project_root=tmp_path,
        timeout_s=60,
    )
    assert result.exit_code == 0
    assert "pong" in result.stdout.lower()
    assert result.duration_s > 0
    assert result.input_tokens > 0
```

- [ ] **Step 4: Run the smoke test**

Run: `uv run pytest tests/support/harness/test_runner.py::test_run_claude_smoke -v -s`
Expected: PASS (or SKIP if no credentials in this shell — that's fine, run it manually before committing).

If the SDK signature differs from what's coded above (it's evolving), inspect with `uv run python -c "import claude_agent_sdk; help(claude_agent_sdk)"` and adjust the message-iteration loop. Acceptable variations: `query()` may return an async iterator directly or a context manager — adapt to what the installed version exposes. Token usage location in `ResultMessage` may also differ; inspect a printed message and pull the right attribute.

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/runner.py tests/support/harness/test_runner.py
git commit -m "feat(harness): add run_claude via Agent SDK with timeout and tool trace"
```

---

## Task 6: Grader (LLM judge with structured output)

The grader takes a `RunResult` + a list of assertions and returns a `Grading` with pass/fail/evidence per assertion. One SDK call per run, structured JSON output, model configurable.

**Files:**
- Create: `tests/support/harness/grader.py`
- Create: `tests/support/harness/test_grader.py`

- [ ] **Step 1: Add Grading dataclass to models**

Append to `tests/support/harness/models.py`:

```python
@dataclass
class Grading:
    expectations: list[dict]   # [{text, passed, evidence}]
    passed: int
    failed: int
    total: int

    @classmethod
    def from_expectations(cls, expectations: list[dict]) -> "Grading":
        passed = sum(1 for e in expectations if e.get("passed"))
        return cls(
            expectations=expectations,
            passed=passed,
            failed=len(expectations) - passed,
            total=len(expectations),
        )
```

- [ ] **Step 2: Write the grader prompt as a constant**

Create `tests/support/harness/grader.py`:

```python
import json
from .models import Grading
from .runner import RunResult

DEFAULT_GRADER_MODEL = "claude-haiku-4-5-20251001"

GRADER_PROMPT = """\
You are a strict eval grader. Read the AGENT OUTPUT below and grade each ASSERTION as PASS or FAIL.

Rules:
- PASS only with clear evidence the assertion is true. The evidence must reflect genuine task completion, not surface-level compliance.
- FAIL if no evidence is found, evidence contradicts the assertion, or evidence is superficial (correct format but wrong content).
- When uncertain, FAIL. The burden of proof is on the assertion.
- No partial credit.
- Cite specific evidence from the output for each judgment.

Return ONLY a JSON object matching this schema (no prose, no markdown fences):
{{
  "expectations": [
    {{"text": "<assertion text>", "passed": true|false, "evidence": "<specific quote or observation>"}}
  ]
}}

ASSERTIONS:
{assertions_json}

AGENT OUTPUT (stdout):
{stdout}

FILES WRITTEN BY AGENT:
{files_block}

TOOL TRACE:
{tool_trace_json}
"""

def _build_prompt(run: RunResult, assertions: list[dict]) -> str:
    files_block = (
        "\n\n".join(f"--- {p} ---\n{c}" for p, c in run.files_written.items())
        or "(none)"
    )
    return GRADER_PROMPT.format(
        assertions_json=json.dumps(assertions, indent=2),
        stdout=run.stdout or "(empty)",
        files_block=files_block,
        tool_trace_json=json.dumps(run.tool_trace, indent=2),
    )

async def grade(
    run: RunResult,
    assertions: list[dict],
    model: str | None = None,
) -> Grading:
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage

    if not assertions:
        return Grading.from_expectations([])

    options = ClaudeAgentOptions(model=model or DEFAULT_GRADER_MODEL)
    prompt = _build_prompt(run, assertions)

    parts: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    parts.append(block.text)

    raw = "".join(parts).strip()
    # Tolerate optional ```json fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`")

    data = json.loads(raw)
    return Grading.from_expectations(data["expectations"])
```

(Note: the spec mentions structured `output_format` with a JSON schema. If the installed SDK exposes that field on `ClaudeAgentOptions`, prefer it over the fence-stripping fallback. Replace the parser with a single `json.loads(raw)` after setting the schema and remove the fence-tolerance logic.)

- [ ] **Step 3: Write a live grader test**

Create `tests/support/harness/test_grader.py`:

```python
import os
import pytest
from tests.support.harness.runner import RunResult
from tests.support.harness.grader import grade

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    reason="requires Claude credentials",
)
async def test_grader_passes_obviously_true_assertion():
    run = RunResult(
        stdout="The answer is 42.",
        files_written={},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.1,
        exit_code=0,
    )
    assertions = [{"text": "The output mentions the number 42"}]
    g = await grade(run, assertions)
    assert g.passed == 1
    assert g.failed == 0
    assert g.expectations[0]["passed"] is True

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    reason="requires Claude credentials",
)
async def test_grader_fails_obviously_false_assertion():
    run = RunResult(
        stdout="hello world",
        files_written={},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.1,
        exit_code=0,
    )
    assertions = [{"text": "The output mentions the number 42"}]
    g = await grade(run, assertions)
    assert g.passed == 0
    assert g.failed == 1
```

- [ ] **Step 4: Run the grader tests**

Run: `uv run pytest tests/support/harness/test_grader.py -v -s`
Expected: 2 passed (or SKIP if no credentials).

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/grader.py tests/support/harness/test_grader.py tests/support/harness/models.py
git commit -m "feat(harness): add LLM-judge grader with structured JSON output"
```

---

## Task 7: Reporter (Rich live table + dots fallback)

**Files:**
- Create: `tests/support/harness/reporter.py`
- Create: `tests/support/harness/test_reporter.py`

- [ ] **Step 1: Define CaseResult and Reporter protocol**

Create `tests/support/harness/reporter.py`:

```python
import sys
from dataclasses import dataclass
from typing import Protocol
from .models import Grading, RunPlan
from .runner import RunResult

@dataclass
class CaseResult:
    plan: RunPlan
    run: RunResult
    grading: Grading

class Reporter(Protocol):
    def start(self, total: int) -> None: ...
    def case_started(self, plan: RunPlan) -> None: ...
    def case_finished(self, result: CaseResult) -> None: ...
    def finish(self, results: list[CaseResult], verbose: bool) -> int: ...

def make_reporter() -> Reporter:
    return RichReporter() if sys.stdout.isatty() else DotsReporter()
```

- [ ] **Step 2: Implement DotsReporter**

Append to `tests/support/harness/reporter.py`:

```python
class DotsReporter:
    def __init__(self) -> None:
        self._count = 0

    def start(self, total: int) -> None:
        print(f"Running {total} cases...")

    def case_started(self, plan: RunPlan) -> None:
        pass

    def case_finished(self, result: CaseResult) -> None:
        symbol = "."
        if result.run.exit_code != 0:
            symbol = "E"
        elif result.grading.failed > 0:
            symbol = "F"
        print(symbol, end="", flush=True)
        self._count += 1
        if self._count % 50 == 0:
            print()

    def finish(self, results: list[CaseResult], verbose: bool) -> int:
        print()
        return _print_summary(results, verbose)
```

- [ ] **Step 3: Implement the shared summary printer**

Append to `tests/support/harness/reporter.py`:

```python
def _print_summary(results: list[CaseResult], verbose: bool) -> int:
    skill_results = [r for r in results if r.plan.suite_kind == "skill"]
    core_results = [r for r in results if r.plan.suite_kind == "core"]

    exit_code = 0

    if skill_results:
        print("\n## Skill Eval Results\n")
        print(f"{'Skill':<20} {'Eval':<30} {'With Skill':<14} {'Baseline':<14} {'Delta':<8}")
        # Pair up with_skill and baseline by (suite, case)
        by_key: dict[tuple[str, str], dict[str, CaseResult]] = {}
        for r in skill_results:
            key = (r.plan.suite_name, r.plan.case_id)
            by_key.setdefault(key, {})[r.plan.variant] = r
        for (suite, case_id), variants in sorted(by_key.items()):
            ws = variants.get("with_skill")
            bl = variants.get("baseline")
            ws_str = _fmt_score(ws.grading) if ws else "—"
            bl_str = _fmt_score(bl.grading) if bl else "—"
            delta = ""
            if ws and bl and bl.grading.total:
                d = (ws.grading.passed / ws.grading.total) - (bl.grading.passed / bl.grading.total)
                delta = f"{d*100:+.0f}%"
            print(f"{suite:<20} {case_id:<30} {ws_str:<14} {bl_str:<14} {delta:<8}")
            if ws and ws.grading.failed > 0:
                exit_code = 1
            if ws and ws.run.exit_code != 0:
                exit_code = 1

    if core_results:
        print("\n## Core Eval Results\n")
        print(f"{'Eval':<25} {'Case':<30} {'Result':<14}")
        for r in sorted(core_results, key=lambda x: (x.plan.suite_name, x.plan.case_id)):
            print(f"{r.plan.suite_name:<25} {r.plan.case_id:<30} {_fmt_score(r.grading):<14}")
            if r.grading.failed > 0 or r.run.exit_code != 0:
                exit_code = 1

    # Failures detail
    failures: list[CaseResult] = []
    for r in results:
        if r.plan.suite_kind == "skill" and r.plan.variant == "baseline":
            continue  # don't surface baseline failures
        if r.grading.failed > 0 or r.run.exit_code != 0:
            failures.append(r)
    if failures:
        print("\n### Failures\n")
        for r in failures:
            label = f"{r.plan.suite_name} > {r.plan.case_id} > {r.plan.variant}"
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

    return exit_code

def _fmt_score(g: Grading) -> str:
    if g.total == 0:
        return "n/a"
    pct = int(round(100 * g.passed / g.total))
    return f"{g.passed}/{g.total} ({pct}%)"
```

- [ ] **Step 4: Implement RichReporter**

Append to `tests/support/harness/reporter.py`:

```python
class RichReporter:
    def __init__(self) -> None:
        from rich.console import Console
        from rich.live import Live
        from rich.table import Table
        self._Console = Console
        self._Live = Live
        self._Table = Table
        self._console = Console()
        self._rows: dict[tuple[str, str, str], dict] = {}
        self._live = None

    def _table(self):
        t = self._Table(title="Eval Runs")
        t.add_column("Suite")
        t.add_column("Case")
        t.add_column("Variant")
        t.add_column("Status")
        t.add_column("Duration", justify="right")
        t.add_column("Tokens", justify="right")
        t.add_column("Pass Rate", justify="right")
        for key, row in self._rows.items():
            t.add_row(*row["cells"])
        return t

    def start(self, total: int) -> None:
        self._live = self._Live(self._table(), console=self._console, refresh_per_second=4)
        self._live.__enter__()

    def case_started(self, plan: RunPlan) -> None:
        key = (plan.suite_name, plan.case_id, plan.variant)
        self._rows[key] = {"cells": [
            plan.suite_name, plan.case_id, plan.variant, "[yellow]running[/yellow]", "—", "—", "—"
        ]}
        if self._live:
            self._live.update(self._table())

    def case_finished(self, result: CaseResult) -> None:
        key = (result.plan.suite_name, result.plan.case_id, result.plan.variant)
        if result.run.exit_code != 0:
            status = "[red]error[/red]"
        elif result.grading.failed > 0:
            status = "[red]fail[/red]"
        else:
            status = "[green]pass[/green]"
        tokens = f"{result.run.input_tokens + result.run.output_tokens}"
        self._rows[key] = {"cells": [
            result.plan.suite_name,
            result.plan.case_id,
            result.plan.variant,
            status,
            f"{result.run.duration_s:.1f}s",
            tokens,
            _fmt_score(result.grading),
        ]}
        if self._live:
            self._live.update(self._table())

    def finish(self, results: list[CaseResult], verbose: bool) -> int:
        if self._live:
            self._live.__exit__(None, None, None)
            self._live = None
        return _print_summary(results, verbose)
```

- [ ] **Step 5: Write a smoke test for DotsReporter**

Create `tests/support/harness/test_reporter.py`:

```python
from pathlib import Path
from tests.support.harness.models import EvalCase, Grading, RunPlan
from tests.support.harness.runner import RunResult
from tests.support.harness.reporter import DotsReporter, CaseResult

def _mk_result(suite, case_id, variant, kind, passed, failed, exit_code=0):
    case = EvalCase(id=case_id, prompt="x", assertions=[])
    plan = RunPlan(
        suite_name=suite, suite_kind=kind, case_id=case_id, variant=variant,
        prompt="x", context_paths=[], case=case,
    )
    run = RunResult(stdout="", files_written={}, input_tokens=10, output_tokens=10, duration_s=1.0, exit_code=exit_code)
    grading = Grading.from_expectations(
        [{"text": "x", "passed": True, "evidence": "y"}] * passed
        + [{"text": "x", "passed": False, "evidence": "y"}] * failed
    )
    return CaseResult(plan=plan, run=run, grading=grading)

def test_dots_reporter_summary_skill_pass(capsys):
    r = DotsReporter()
    r.start(2)
    results = [
        _mk_result("ghostwrite", "sponsor-email", "with_skill", "skill", passed=3, failed=0),
        _mk_result("ghostwrite", "sponsor-email", "baseline", "skill", passed=1, failed=2),
    ]
    for res in results:
        r.case_finished(res)
    exit_code = r.finish(results, verbose=False)
    out = capsys.readouterr().out
    assert ".." in out
    assert "Skill Eval Results" in out
    assert "ghostwrite" in out
    assert exit_code == 0  # baseline failures don't break exit code

def test_dots_reporter_exit_code_on_with_skill_fail(capsys):
    r = DotsReporter()
    r.start(1)
    results = [_mk_result("ghostwrite", "sponsor-email", "with_skill", "skill", passed=1, failed=1)]
    for res in results:
        r.case_finished(res)
    exit_code = r.finish(results, verbose=False)
    assert exit_code == 1
```

- [ ] **Step 6: Run reporter tests**

Run: `uv run pytest tests/support/harness/test_reporter.py -v`
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add tests/support/harness/reporter.py tests/support/harness/test_reporter.py
git commit -m "feat(harness): add Rich live reporter with dots fallback"
```

---

## Task 8: Orchestrator + CLI entry point

Wires discovery → runner → grader → reporter together. Concurrency cap of 4. Writes artifacts to `tmp/evals/<timestamp>/`.

**Files:**
- Create: `tests/support/harness/orchestrator.py`
- Create: `tests/support/harness/__main__.py`

- [ ] **Step 1: Implement the orchestrator**

Create `tests/support/harness/orchestrator.py`:

```python
import asyncio
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from .discovery import discover_suites, build_run_plans
from .grader import grade
from .models import RunPlan
from .reporter import CaseResult, Reporter
from .runner import run_claude

CONCURRENCY = 4

def _artifact_dir(root: Path, plan: RunPlan, run_id: str) -> Path:
    if plan.suite_kind == "core":
        base = root / run_id / "_core" / plan.suite_name / f"eval-{plan.case_id}" / "run"
    else:
        base = root / run_id / plan.suite_name / f"eval-{plan.case_id}" / plan.variant
    base.mkdir(parents=True, exist_ok=True)
    return base

async def _run_one(
    plan: RunPlan,
    project_root: Path,
    artifact_root: Path,
    run_id: str,
    reporter: Reporter,
    sem: asyncio.Semaphore,
) -> CaseResult:
    async with sem:
        reporter.case_started(plan)
        with tempfile.TemporaryDirectory(prefix="eval-cwd-") as tmp:
            cwd = Path(tmp)
            run = await run_claude(
                prompt=plan.prompt,
                cwd=cwd,
                context_paths=plan.context_paths,
                project_root=project_root,
            )

        # Honor cleanup globs (relative to project_root)
        for pattern in plan.case.cleanup:
            for match in project_root.glob(pattern):
                if match.is_dir():
                    import shutil; shutil.rmtree(match, ignore_errors=True)
                else:
                    match.unlink(missing_ok=True)

        grading = await grade(run, plan.case.assertions, model=plan.case.grader_model)

        # Persist artifacts
        adir = _artifact_dir(artifact_root, plan, run_id)
        (adir / "outputs").mkdir(exist_ok=True)
        (adir / "outputs" / "output.md").write_text(run.stdout)
        (adir.parent / "eval_metadata.json").write_text(json.dumps({
            "id": plan.case_id,
            "prompt": plan.case.prompt,
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
        reporter.case_finished(result)
        return result

async def run_evals(
    project_root: Path,
    names: list[str] | None,
    baseline: bool,
    verbose: bool,
    reporter: Reporter,
) -> int:
    tests_root = project_root / "tests"
    suites = discover_suites(tests_root, names=names)
    if not suites:
        print(f"No eval suites found under {tests_root}")
        return 1

    plans = build_run_plans(suites, project_root=project_root, baseline=baseline)
    artifact_root = project_root / "tmp" / "evals"
    artifact_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

    reporter.start(len(plans))
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [_run_one(p, project_root, artifact_root, run_id, reporter, sem) for p in plans]
    results = await asyncio.gather(*tasks)
    exit_code = reporter.finish(list(results), verbose=verbose)
    print(f"\nFull results: tmp/evals/{run_id}/")
    return exit_code
```

- [ ] **Step 2: Implement the CLI entry point**

Create `tests/support/harness/__main__.py`:

```python
import argparse
import asyncio
import sys
from pathlib import Path
from .orchestrator import run_evals
from .reporter import make_reporter

def main() -> int:
    parser = argparse.ArgumentParser(prog="tests.support.harness")
    parser.add_argument("names", nargs="*", help="filter by suite name")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--no-baseline", action="store_true")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[3]
    reporter = make_reporter()

    return asyncio.run(run_evals(
        project_root=project_root,
        names=args.names or None,
        baseline=not args.no_baseline,
        verbose=args.verbose,
        reporter=reporter,
    ))

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Sanity-check the entry point compiles**

Run: `uv run python -c "from tests.support.harness.__main__ import main; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add tests/support/harness/orchestrator.py tests/support/harness/__main__.py
git commit -m "feat(harness): add orchestrator, CLI, and artifact persistence"
```

---

## Task 9: Makefile

**Files:**
- Create: `Makefile`

- [ ] **Step 1: Write the Makefile**

Create `Makefile`:

```makefile
.PHONY: test

test:
	uv run python -m tests.support.harness $(ARGS)
```

- [ ] **Step 2: Verify make test runs (against an empty tests tree, should report no suites)**

Run: `make test ARGS="nonexistent-suite"`
Expected: prints "No eval suites found under ..." then exits 1. (Will exit 1 before any migration; that's correct.)

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: add Makefile with test target"
```

---

## Task 10: Migrate eval files (skills + core)

Move and reformat existing eval files. Each migration: drop `assertions[].type`, drop `expected_output`, rename `skill_name`/`eval_name` → `name`, slugify integer ids.

**Files (per skill — repeat for ghostwrite, scope, summarize, prompt-engineer):**
- Create: `tests/skills/<name>/evals.json`
- Delete: `skills/<name>/evals/`

**Files (core):**
- Create: `tests/core/no-ai-attribution.json`
- Delete: `evals/no-ai-attribution.json`, `evals/`

- [ ] **Step 1: Migrate ghostwrite**

Read `skills/ghostwrite/evals/evals.json`. Create `tests/skills/ghostwrite/evals.json` with the new format. The two existing cases become ids `sponsor-email` and `linkedin-from-scratch`. Drop every `"type"` field on assertions. Drop `expected_output`. Rename `skill_name` → `name`.

```json
{
  "name": "ghostwrite",
  "evals": [
    {
      "id": "sponsor-email",
      "prompt": "Rewrite this as an email to our sponsor contact Sarah:\n\nHey so I wanted to reach out because we just wrapped up Season 3 of the Fellowship and the numbers were really strong. We had 450 fellows complete the program which is up 30% from last season. 92% of them said they'd recommend it to a friend. I think this is a great opportunity for us to talk about renewing the sponsorship for next season and maybe even expanding the scope of what we do together. Let me know if you'd be open to hopping on a call next week to discuss.",
      "files": [],
      "assertions": [
        { "text": "Output contains a greeting in the format 'Hey, Sarah --'" },
        { "text": "Output leads with the results or the ask in the first sentence, not a preamble like 'I wanted to reach out'" },
        { "text": "Output does not contain any em dashes (—)" },
        { "text": "Output contains a sign-off of '- Swift' or 'Happy Hacking,\\nSwift'" },
        { "text": "Output is significantly shorter than the input, cutting filler and over-explanation" },
        { "text": "Output preserves all key facts: 450 fellows, 30% increase, 92% recommendation rate" },
        { "text": "Output uses contractions (e.g., we're, don't, that's) rather than formal language" }
      ]
    },
    {
      "id": "linkedin-from-scratch",
      "prompt": "Write a LinkedIn post announcing that MLH is partnering with a new AI company to offer hackathon participants access to their API.",
      "files": [],
      "assertions": [
        { "text": "Output does NOT contain a full LinkedIn post draft" },
        { "text": "Output asks the user to provide source content, notes, bullet points, or details to rewrite" },
        { "text": "Output explains that the skill is a rewriter, not a creator" },
        { "text": "Output does not invent the name of the AI company or fabricate partnership details" }
      ]
    }
  ]
}
```

Delete `skills/ghostwrite/evals/`.

- [ ] **Step 2: Migrate scope**

Read `skills/scope/evals/evals.json`. Apply the same transformation. Pick descriptive slug ids based on each case's intent. Write to `tests/skills/scope/evals.json`. Delete `skills/scope/evals/`.

- [ ] **Step 3: Migrate summarize**

Read `skills/summarize/evals/evals.json`. Apply the same transformation. Pick descriptive slug ids. The fixture `skills/summarize/evals/test-paper.pdf` moves to `tests/skills/summarize/test-paper.pdf` — update any case whose `files` field references it. Write to `tests/skills/summarize/evals.json`. Delete `skills/summarize/evals/`.

- [ ] **Step 4: Migrate prompt-engineer**

Read `skills/prompt-engineer/evals/evals.json`. Apply the same transformation. Pick descriptive slug ids. Write to `tests/skills/prompt-engineer/evals.json`. Delete `skills/prompt-engineer/evals/`.

- [ ] **Step 5: Migrate no-ai-attribution**

Read `evals/no-ai-attribution.json`. Rename `eval_name` → `name`. Slug ids become `throwaway-commit` and `pr-draft`. Drop `assertions[].type`. Keep `cleanup` arrays as-is. Write to `tests/core/no-ai-attribution.json`. Delete the entire `evals/` directory.

- [ ] **Step 6: Verify discovery sees all five suites**

Run: `uv run python -c "from pathlib import Path; from tests.support.harness.discovery import discover_suites; print([s.name for s in discover_suites(Path('tests'))])"`
Expected: `['ghostwrite', 'prompt-engineer', 'scope', 'summarize', 'no-ai-attribution']` (skills sorted, then core).

- [ ] **Step 7: Commit**

```bash
git add tests/skills/ tests/core/
git rm -r skills/ghostwrite/evals skills/scope/evals skills/summarize/evals skills/prompt-engineer/evals evals/
git commit -m "refactor(tests): migrate eval files to tests/ tree with new format"
```

---

## Task 11: Add tests/core/skill-triggers.json

One core eval with one case per skill. Each case prompts something the skill should fire on. The assertion checks the tool trace for a `Skill` invocation matching the expected name.

**Files:**
- Create: `tests/core/skill-triggers.json`

- [ ] **Step 1: Write the file**

Create `tests/core/skill-triggers.json`:

```json
{
  "name": "skill-triggers",
  "evals": [
    {
      "id": "ghostwrite-on-rewrite-request",
      "prompt": "rewrite this in my voice: we're going to crush it this quarter and the team is fired up about the new launch",
      "files": [],
      "assertions": [
        { "text": "The Skill tool was invoked with a skill name matching 'ghostwrite' (check the TOOL TRACE)" },
        { "text": "The output is a rewritten version of the input, not a refusal or clarifying question" }
      ]
    },
    {
      "id": "scope-on-design-request",
      "prompt": "help me scope a new feature where users can schedule recurring exports of their data",
      "files": [],
      "assertions": [
        { "text": "The Skill tool was invoked with a skill name matching 'scope' (check the TOOL TRACE)" },
        { "text": "The response engages with scoping the idea (asking clarifying questions or proposing approaches), not jumping to implementation" }
      ]
    },
    {
      "id": "summarize-on-tldr-request",
      "prompt": "tl;dr this for me: https://www.anthropic.com/news/claude-4",
      "files": [],
      "assertions": [
        { "text": "The Skill tool was invoked with a skill name matching 'summarize' (check the TOOL TRACE)" }
      ]
    },
    {
      "id": "prompt-engineer-on-prompt-request",
      "prompt": "write me a prompt for an LLM that extracts structured JSON from invoices",
      "files": [],
      "assertions": [
        { "text": "The Skill tool was invoked with a skill name matching 'prompt-engineer' (check the TOOL TRACE)" },
        { "text": "The response produces or asks clarifying questions to produce a structured prompt, not a generic answer" }
      ]
    }
  ]
}
```

- [ ] **Step 2: Commit**

```bash
git add tests/core/skill-triggers.json
git commit -m "test(core): add skill-triggers eval covering all four skills"
```

---

## Task 12: End-to-end verification run

Run the full harness against the migrated suites and confirm parity.

- [ ] **Step 1: Run the full suite**

Run: `make test`
Expected: All five suites discovered. Live `rich` table appears (assuming TTY). All cases run and grade. Final summary printed. Exit code reflects pass/fail status.

- [ ] **Step 2: Run a single suite to verify filtering**

Run: `make test ARGS="ghostwrite"`
Expected: Only ghostwrite cases run.

- [ ] **Step 3: Run with `--no-baseline` to verify the flag**

Run: `make test ARGS="--no-baseline ghostwrite"`
Expected: Only `with_skill` plans run; no baseline rows in summary.

- [ ] **Step 4: Pipe output to verify dots reporter**

Run: `make test ARGS="ghostwrite" | cat`
Expected: dots-style output (`.`/`F`/`E`) instead of the live table; final summary still printed.

- [ ] **Step 5: Inspect artifacts**

Run: `ls tmp/evals/ | tail -1` then `find tmp/evals/$(ls tmp/evals/ | tail -1) -type f`
Expected: per-case directories with `outputs/output.md`, `eval_metadata.json`, `grading.json`. Core evals nested under `_core/`.

- [ ] **Step 6: Document any regressions in plan-as-you-go**

For any case that previously passed under `/eval` but now fails:
- Inspect `tmp/evals/<run-id>/<suite>/eval-<case>/with_skill/outputs/output.md`
- Decide: (a) the eval was implicitly relying on `CLAUDE.md` context — add it to the case's `files` field; (b) the eval was poorly written — update the prompt; (c) it's a real harness bug — fix the harness.

Do not skip this step. The point of the migration is parity.

- [ ] **Step 7: Commit any eval fixes from Step 6**

```bash
git add tests/
git commit -m "fix(tests): adjust migrated evals to pass against new harness"
```

(Skip the commit if no fixes were needed.)

---

## Task 13: Delete old `/eval` command and rewrite docs/evals.md

**Files:**
- Delete: `.claude/commands/eval.md`
- Modify: `docs/evals.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Delete the old command**

Run: `git rm .claude/commands/eval.md`

- [ ] **Step 2: Rewrite docs/evals.md**

Replace `docs/evals.md` with new content describing the harness:

```markdown
# Skill Evals

How we test skills and project rules in MechaSwift.

## Running

```bash
make test                              # all suites
make test ARGS="ghostwrite"            # one suite
make test ARGS="--no-baseline scope"   # skip baseline runs (faster)
make test ARGS="--verbose"             # show passing assertion evidence too
```

The harness discovers eval files under `tests/`, runs each case in parallel through the Claude Agent SDK (concurrency cap 4), grades with an LLM judge, and prints a live table (TTY) or pytest dots (CI).

## Layout

- `tests/skills/<name>/evals.json` — skill quality evals. Each case runs twice: once with the skill loaded (preamble + skill dir copied into the temp cwd), once as a baseline. The summary reports both and the delta.
- `tests/core/<name>.json` — core evals. Single run per case in a temp cwd seeded with `AGENTS.md`. The agent discovers skills on its own. Used for global rules (e.g. `no-ai-attribution`) and the `skill-triggers` discovery test.
- `tests/support/harness/` — the Python harness itself. Has its own pytest unit tests (`uv run pytest tests/support`).

## Eval file format

```json
{
  "name": "ghostwrite",
  "evals": [
    {
      "id": "sponsor-email",
      "prompt": "...",
      "files": [],
      "grader_model": "claude-haiku-4-5-20251001",
      "assertions": [
        { "text": "Output preserves all factual claims" }
      ],
      "cleanup": []
    }
  ]
}
```

- `name` — used for filtering on the CLI.
- `id` — slug, used in artifact paths and surfaced in the summary.
- `files` — relative paths from the eval file dir; copied into the run's temp cwd.
- `grader_model` — optional, defaults to Haiku. Override for subjective skills like ghostwrite.
- `assertions` — graded by an LLM judge (one call per run). Be specific.
- `cleanup` — optional glob patterns deleted after the run.

## Artifacts

Every run writes to `tmp/evals/<ISO-timestamp>/`:

```
tmp/evals/2026-04-07T14-30-00/
  ghostwrite/
    eval-sponsor-email/
      with_skill/outputs/output.md
      with_skill/grading.json
      without_skill/outputs/output.md
      without_skill/grading.json
      eval_metadata.json
  _core/
    no-ai-attribution/
      eval-throwaway-commit/run/...
```

`tmp/` is gitignored.

## Writing good evals

- At least 3 cases per skill: happy path, edge case, adversarial/negative.
- Assertions describe observable properties of the output, not subjective vibes. The grader is an LLM judge; "Output uses Swift's voice" is too soft. "Output contains no em dashes" is graded reliably.
- Skill triggers: keep `tests/core/skill-triggers.json` updated when you add a skill.

## Adding a new skill

1. Create `tests/skills/<name>/evals.json` with at least 3 cases.
2. Add a case to `tests/core/skill-triggers.json` that prompts a realistic trigger and asserts the Skill tool fires.
3. `make test ARGS="<name>"` to verify.
```

- [ ] **Step 3: Update CLAUDE.md `## Commands` section**

Read `CLAUDE.md`. Find the `## Commands` section (currently lists `/eval`). Replace the `/eval` bullet with:

```markdown
- **make test** -- Run all skill and core evals via the Python harness. See `docs/evals.md`.
```

- [ ] **Step 4: Commit**

```bash
git add docs/evals.md CLAUDE.md .claude/commands/eval.md
git commit -m "docs: rewrite evals guide for the new harness, drop /eval command"
```

---

## Self-review

After writing this plan, I checked it against the spec:

- **Spec coverage:** All seven sections of the spec map to tasks. Layout (Task 1+10+13), eval format (Task 2+10), runner interface (Task 4+5), discovery + run plan (Task 2+3), grader (Task 6), reporter (Task 7), CLI/Makefile (Task 8+9), artifacts (Task 8), self-bootstrap test (Task 12), skill-triggers (Task 11). Migration of old files (Task 10), deletion of `/eval` and docs rewrite (Task 13).
- **Placeholder scan:** No TBDs. Every code step has runnable code. The one place that says "pick descriptive slug ids based on each case's intent" (Task 10) is a deliberate human judgment call during migration, not a placeholder — the engineer will read the old `expected_output` field and pick an obvious slug.
- **Type consistency:** `RunResult`, `RunPlan`, `EvalCase`, `EvalSuite`, `Grading`, `CaseResult` are defined once and used consistently. Function names (`load_eval_file`, `discover_suites`, `build_run_plans`, `copy_context_paths`, `snapshot_files`, `capture_changes`, `run_claude`, `grade`, `make_reporter`, `run_evals`) match across tasks.

One acknowledged risk: the Claude Agent SDK API surface is evolving. Task 5 includes guidance to inspect the installed version and adapt the message-iteration loop if `ResultMessage` / `usage` fields differ. Task 6 has the same caveat for structured output. This is unavoidable when integrating against a pre-1.0 SDK.
