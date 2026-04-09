# Pytest Eval Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address all PR review feedback and fix the 23 failing eval tests from the pytest eval rewrite.

**Architecture:** Mechanical renames and refactors first (no behavior change, unit tests verify), then test assertion adjustments for LLM-behavior-dependent evals, then docs and build improvements.

**Tech Stack:** Python 3.12, pytest 8+, claude-agent-sdk

---

## File Map

**Harness files to modify:**
- `tests/support/harness/matchers.py` — rename `passes_rubric` → `llm_judge`
- `tests/support/harness/_rubric_judge.py` — refactor for readability
- `tests/support/harness/reporter.py` — remove unhelpful comments
- `tests/conftest.py` — no changes needed (already correct)

**Test files to modify:**
- `tests/skills/ghostwrite/core_checks.py` — rename file → `ghostwrite_helpers.py`, remove output length check
- `tests/skills/ghostwrite/test_blog_format.py` — update import, add per-format length test, fix backslashes
- `tests/skills/ghostwrite/test_email_format.py` — update import, add per-format length test, fix backslashes
- `tests/skills/ghostwrite/test_linkedin_format.py` — update import, add per-format length test, fix bold test, fix backslashes
- `tests/skills/ghostwrite/test_slack_format.py` — update import, add per-format length test, fix backslashes
- `tests/skills/ghostwrite/test_refuses_from_scratch.py` — update import
- `tests/skills/scope/conftest.py` — increase timeout
- `tests/skills/prompt-engineer/test_fix_bad_prompt.py` — relax assertions
- `tests/skills/summarize/structural_checks.py` — rename method call
- `tests/skills/summarize/test_local_pdf.py` — rename method call
- `tests/skills/summarize/test_pasted_text.py` — rename method call (if used)
- `tests/skills/summarize/test_web_article.py` — rename method call (if used)
- `tests/skills/scope/test_scoping_process.py` — rename method call
- `tests/skills/prompt-engineer/test_structured_extraction.py` — rename method call
- `tests/core/test_no_ai_attribution.py` — rename method call (if used)
- `tests/core/test_skill_triggers.py` — rename method call (if used)

**Config/docs to modify:**
- `pyproject.toml` — remove `*_test.py` pattern
- `Makefile` — add parallel flag
- `docs/evals.md` — consolidate tables, add example output, rename method in docs

**Harness unit tests to update:**
- `tests/support/harness/tests/test_matchers.py` — no changes (doesn't test `passes_rubric`)

---

### Task 1: Rename `passes_rubric` → `llm_judge`

PR feedback: "Let's rename `passes_rubric` to `llm_judge`" — clearer name for the LLM-judged assertion method.

**Files:**
- Modify: `tests/support/harness/matchers.py:145`
- Modify: all test files that call `passes_rubric` (see grep output)
- Modify: `docs/evals.md:52`

- [ ] **Step 1: Grep for all usages of `passes_rubric`**

Run: `grep -r "passes_rubric" tests/ docs/ --include="*.py" --include="*.md" -n`

Record every file and line number.

- [ ] **Step 2: Rename the method in matchers.py**

In `tests/support/harness/matchers.py`, rename the method:

```python
# old
def passes_rubric(
    self, item: str, on: str, model: str | None = None
) -> bool:

# new
def llm_judge(
    self, item: str, on: str, model: str | None = None
) -> bool:
```

The docstring and implementation stay the same — only the method name changes.

- [ ] **Step 3: Update every test file that calls `passes_rubric`**

In every file found in Step 1, replace `passes_rubric(` with `llm_judge(` and `.passes_rubric(` with `.llm_judge(`. This is a mechanical find-and-replace across all files. Key files:

- `tests/skills/ghostwrite/test_blog_format.py`
- `tests/skills/ghostwrite/test_email_format.py`
- `tests/skills/ghostwrite/test_linkedin_format.py`
- `tests/skills/ghostwrite/test_slack_format.py`
- `tests/skills/scope/test_scoping_process.py`
- `tests/skills/prompt-engineer/test_fix_bad_prompt.py`
- `tests/skills/prompt-engineer/test_structured_extraction.py`
- `tests/skills/summarize/structural_checks.py`
- `tests/skills/summarize/test_local_pdf.py`
- `tests/skills/summarize/test_pasted_text.py`
- `tests/skills/summarize/test_web_article.py`
- `tests/core/test_no_ai_attribution.py`
- `tests/core/test_skill_triggers.py`

- [ ] **Step 4: Update docs/evals.md**

In `docs/evals.md`, line 52, change:

```markdown
# old
| `passes_rubric(item, on, model=None)` | LLM judge (default Haiku) grades pass/fail |

# new
| `llm_judge(item, on, model=None)` | LLM judge (default Haiku) grades pass/fail |
```

- [ ] **Step 5: Run harness unit tests**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: all pass (unit tests don't directly test this method by name)

- [ ] **Step 6: Verify no remaining references**

Run: `grep -r "passes_rubric" tests/ docs/ --include="*.py" --include="*.md"`
Expected: zero results

- [ ] **Step 7: Commit**

```bash
git add tests/support/harness/matchers.py docs/evals.md
git add tests/skills/ tests/core/
git commit -m "refactor: rename passes_rubric to llm_judge"
```

---

### Task 2: Rename `core_checks.py` → `ghostwrite_helpers.py`

PR feedback: "Let's rename this file to be more descriptive: `ghostwrite_helpers.py`"

**Files:**
- Rename: `tests/skills/ghostwrite/core_checks.py` → `tests/skills/ghostwrite/ghostwrite_helpers.py`
- Modify: `tests/skills/ghostwrite/test_blog_format.py:6`
- Modify: `tests/skills/ghostwrite/test_email_format.py:6`
- Modify: `tests/skills/ghostwrite/test_linkedin_format.py:6`
- Modify: `tests/skills/ghostwrite/test_slack_format.py:6`
- Modify: `tests/skills/ghostwrite/test_refuses_from_scratch.py` (if it imports)

- [ ] **Step 1: Check all imports of core_checks**

Run: `grep -r "core_checks" tests/ --include="*.py" -n`

- [ ] **Step 2: Rename the file**

```bash
mv tests/skills/ghostwrite/core_checks.py tests/skills/ghostwrite/ghostwrite_helpers.py
```

- [ ] **Step 3: Update imports in all ghostwrite test files**

In each file that imports from `core_checks`, change:

```python
# old
from tests.skills.ghostwrite.core_checks import assert_core_rules

# new
from tests.skills.ghostwrite.ghostwrite_helpers import assert_core_rules
```

Files to update:
- `tests/skills/ghostwrite/test_blog_format.py`
- `tests/skills/ghostwrite/test_email_format.py`
- `tests/skills/ghostwrite/test_linkedin_format.py`
- `tests/skills/ghostwrite/test_slack_format.py`

- [ ] **Step 4: Verify no remaining references**

Run: `grep -r "core_checks" tests/ --include="*.py"`
Expected: zero results

- [ ] **Step 5: Commit**

```bash
git add tests/skills/ghostwrite/
git commit -m "refactor: rename core_checks.py to ghostwrite_helpers.py"
```

---

### Task 3: Fix ghostwrite output length assertions

3 tests fail because `output_len_lte(len(source_text))` is too strict — blog posts with headers and formatting can reasonably be longer than raw bullet notes. Move the length check out of shared helpers and into per-format tests with appropriate thresholds.

**Files:**
- Modify: `tests/skills/ghostwrite/ghostwrite_helpers.py` (formerly `core_checks.py`)
- Modify: `tests/skills/ghostwrite/test_blog_format.py`
- Modify: `tests/skills/ghostwrite/test_email_format.py`
- Modify: `tests/skills/ghostwrite/test_linkedin_format.py`
- Modify: `tests/skills/ghostwrite/test_slack_format.py`

- [ ] **Step 1: Remove output length check from ghostwrite_helpers.py**

Remove the last line of `assert_core_rules`:

```python
# delete this line from ghostwrite_helpers.py
    assert result.output_len_lte(len(source_text), on="final_message")
```

The function signature stays the same (`result, source_text`) — `source_text` is still used by the caller but no longer checked for length inside the helper. Actually, `source_text` is not used anywhere else in the function, so also remove it from the signature:

```python
# old
def assert_core_rules(result, source_text: str):
    """Core voice rules that apply to every ghostwrite output (from lint.py)."""

# new
def assert_core_rules(result):
    """Core voice rules that apply to every ghostwrite output."""
```

- [ ] **Step 2: Update all callers to drop source_text argument**

In every test file that calls `assert_core_rules(result, SOURCE)`, change to `assert_core_rules(result)`:

`tests/skills/ghostwrite/test_blog_format.py`:
```python
# old
def test_core_rules(result):
    assert_core_rules(result, SOURCE)

# new
def test_core_rules(result):
    assert_core_rules(result)
```

Repeat for:
- `tests/skills/ghostwrite/test_email_format.py`
- `tests/skills/ghostwrite/test_linkedin_format.py`
- `tests/skills/ghostwrite/test_slack_format.py`

- [ ] **Step 3: Add per-format output length tests**

Add a `test_output_length` function to each format test file with format-appropriate thresholds. Blog posts can be longer than input (headers, structure add length). Emails and LinkedIn should be roughly same length or shorter. Slack must be radically shorter.

`tests/skills/ghostwrite/test_blog_format.py` — blog posts add structure, allow 1.5x:
```python
def test_output_length(result):
    assert result.output_len_lte(int(len(SOURCE) * 1.5), on="final_message")
```

`tests/skills/ghostwrite/test_email_format.py` — emails should be concise, allow 1.2x:
```python
def test_output_length(result):
    assert result.output_len_lte(int(len(SOURCE) * 1.2), on="final_message")
```

`tests/skills/ghostwrite/test_linkedin_format.py` — LinkedIn should be concise, allow 1.2x:
```python
def test_output_length(result):
    assert result.output_len_lte(int(len(SOURCE) * 1.2), on="final_message")
```

`tests/skills/ghostwrite/test_slack_format.py` — Slack must be radically shorter, allow 1.0x:
```python
def test_output_length(result):
    assert result.output_len_lte(len(SOURCE), on="final_message")
```

- [ ] **Step 4: Run harness unit tests**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add tests/skills/ghostwrite/
git commit -m "fix: move output length check to per-format tests with appropriate thresholds"
```

---

### Task 4: Fix LinkedIn bold test

The test `test_no_markdown_bold` asserts zero bold text (`**text**`), but the SKILL.md says "Bold only for genuinely critical phrases (1-3 per post max)" — some bold IS allowed. The test is stricter than the skill.

**Files:**
- Modify: `tests/skills/ghostwrite/test_linkedin_format.py:29-30`

- [ ] **Step 1: Fix the assertion**

```python
# old
def test_no_markdown_bold(result):
    assert result.not_matches_regex(r"\*\*[^*]+\*\*", on="final_message")

# new
def test_limited_markdown_bold(result):
    """LinkedIn skill allows bold for 1-3 genuinely critical phrases max."""
    assert result.matches_regex(r"\*\*[^*]+\*\*", on="final_message", min=0, max=3)
```

- [ ] **Step 2: Commit**

```bash
git add tests/skills/ghostwrite/test_linkedin_format.py
git commit -m "fix: allow up to 3 bold phrases in LinkedIn test per SKILL.md"
```

---

### Task 5: Fix prompt engineer test assertions

3 tests fail due to overly strict assertions that don't account for LLM output variation.

**Files:**
- Modify: `tests/skills/prompt-engineer/test_fix_bad_prompt.py:30-39`

- [ ] **Step 1: Broaden the Changes section regex**

The current regex looks for `**changes**`, `## changes`, or `## what changed` at the start of a line. The LLM might use other formats like `**What I changed**`, `Changes:`, or inline changes description. Broaden to also match `**what` patterns and `changes:`:

```python
# old
def test_has_changes_section(result):
    assert result.matches_regex(
        r"(?im)(^\*\*changes\*\*|^##?\s*changes|^##?\s*what changed)",
        on="final_message",
    )

# new
def test_has_changes_section(result):
    assert result.matches_regex(
        r"(?im)(^\*\*changes\*\*|^\*\*what\s+(i\s+)?changed\*\*|^##?\s*changes|^##?\s*what\s+(i\s+)?changed|^changes:)",
        on="final_message",
    )
```

- [ ] **Step 2: Fix the removes_padding test**

The test checks that "helpful AI assistant" doesn't appear anywhere in `final_message`. But the LLM might quote the original prompt to show what was wrong before presenting the rewrite. Use `llm_judge` instead of a literal match — what matters is the *rewritten prompt* doesn't contain padding, not that the explanation avoids quoting the original.

```python
# old
def test_removes_padding(result):
    assert result.not_matches_regex(
        r"(?i)helpful AI assistant", on="final_message"
    )
    assert result.not_matches_regex(r"\bPlease\b", on="final_message")
    assert result.not_matches_regex(r"\bThank you\b", on="final_message")

# new
def test_removes_padding(result):
    assert result.llm_judge(
        "The rewritten prompt inside the code block does not contain "
        "politeness padding like 'please', 'thank you', or vague roles "
        "like 'helpful AI assistant'. It is acceptable for the explanation "
        "outside the code block to quote the original text.",
        on="final_message",
    )
```

- [ ] **Step 3: Commit**

```bash
git add tests/skills/prompt-engineer/test_fix_bad_prompt.py
git commit -m "fix: relax prompt engineer assertions for LLM output variation"
```

---

### Task 6: Fix scope eval fixture

The scope eval has two issues: (1) fixture uses `scope="session"` while depending on module-scoped `run_eval`, which risks a `ScopeMismatch`; (2) 6-turn conversation may exceed the 300s default timeout, causing the agent to never reach the spec-writing turns.

**Files:**
- Modify: `tests/skills/scope/conftest.py`
- Modify: `tests/support/harness/runner.py:141` (add `timeout_s` param to `run_eval`)

- [ ] **Step 1: Add `timeout_s` parameter to `run_eval`**

In `tests/support/harness/runner.py`, add `timeout_s` to the `run_eval` function signature and pass it through to `run_claude`:

```python
# old
def run_eval(
    project_root: Path,
    turns: list[str],
    setup: _Callable[[Path], None] | None = None,
    cleanup: _Callable[[Path], None] | None = None,
    model: str | None = None,
) -> "EvalResult":

# new
def run_eval(
    project_root: Path,
    turns: list[str],
    setup: _Callable[[Path], None] | None = None,
    cleanup: _Callable[[Path], None] | None = None,
    model: str | None = None,
    timeout_s: float = 300,
) -> "EvalResult":
```

And pass it through in the `run_claude` call:

```python
# old
run = _asyncio.run(
    run_claude(
        turns=actual_turns,
        cwd=cwd,
        context_paths=[],
        project_root=project_root,
        model=model,
    )
)

# new
run = _asyncio.run(
    run_claude(
        turns=actual_turns,
        cwd=cwd,
        context_paths=[],
        project_root=project_root,
        model=model,
        timeout_s=timeout_s,
    )
)
```

- [ ] **Step 2: Fix scope conftest.py fixture scope and timeout**

Change `scope="session"` to `scope="module"` to match `run_eval`'s scope, and add an increased timeout for the 6-turn conversation:

```python
import textwrap

import pytest

from tests.support.harness.setup import cleanup_globs, skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Scope a GitHub webhook system for MechaSwift that listens for \
                PR events and posts summaries to Slack. It should handle retries, \
                filter by repo, and be configurable per-channel. We're using \
                Node.js and already have a Slack bot token.\
            """),
            textwrap.dedent("""\
                Purpose is surfacing PR activity in Slack so reviews don't stall. \
                Internal eng team, around 15 people. We run a long-running Node.js \
                service on Fly.io and have Redis available there. Per-repo allowlist \
                routing each repo to one channel. Events we care about: opened, \
                ready_for_review, closed. Crash-safety and retries are required -- \
                no in-memory-only queues. Config via a single YAML file at startup, \
                no hot reload. Out of scope: two-way interaction, review assignment, \
                backfill, config UI.\
            """),
            "Go with your recommendation. Walk me through the design.",
            "Looks good, keep going.",
            "Design is approved. Write the spec.",
            "Spec looks good. Nothing else for now.",
        ],
        setup=skill_setup("scope", project_root),
        cleanup=cleanup_globs("references/specs/2026-*-github-webhook*.md"),
        timeout_s=600,
    )
```

Note: changing from `session` to `module` scope means each test file in `tests/skills/scope/` runs the eval independently. This costs one extra eval run but avoids scope mismatch issues. The two test files (`test_scoping_process.py` and `test_spec_structure.py`) test different aspects of the same eval, so running twice is acceptable.

- [ ] **Step 3: Run harness unit tests**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add tests/support/harness/runner.py tests/skills/scope/conftest.py
git commit -m "fix: add timeout_s param to run_eval, fix scope fixture scope and timeout"
```

---

### Task 7: Refactor `_rubric_judge.py` for readability

PR feedback: "This function is tough to read. Let's refactor for readability." The `_judge_async` function mixes streaming, structured output parsing, and fallback logic in one dense block.

**Files:**
- Modify: `tests/support/harness/_rubric_judge.py`

- [ ] **Step 1: Refactor the module**

Rewrite `_rubric_judge.py` with clearer structure — separate the prompt building, response collection, and result parsing:

```python
import asyncio
import json

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

DEFAULT_JUDGE_MODEL = "claude-haiku-4-5-20251001"

_JUDGE_PROMPT = """\
You are a strict rubric grader. Evaluate the CONTENT below against the RUBRIC ITEM.

Return ONLY a JSON object: {{"pass": true}} or {{"pass": false, "reasoning": "..."}}

RUBRIC ITEM: {item}

CONTENT:
{content}
"""

_JUDGE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "pass": {"type": "boolean"},
            "reasoning": {"type": "string"},
        },
        "required": ["pass"],
        "additionalProperties": False,
    },
}


def _extract_verdict(structured: dict | None, raw_parts: list[str]) -> bool:
    """Extract pass/fail from either structured output or raw text."""
    if structured is not None:
        return structured.get("pass", False)

    raw = "".join(raw_parts).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`")

    return json.loads(raw).get("pass", False)


async def _judge_async(item: str, content: str, model: str) -> bool:
    """Send content + rubric item to an LLM judge, return pass/fail."""
    prompt = _JUDGE_PROMPT.format(item=item, content=content[:40_000])
    options = ClaudeAgentOptions(model=model, output_format=_JUDGE_SCHEMA)

    structured: dict | None = None
    raw_parts: list[str] = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if getattr(message, "structured_output", None):
                structured = message.structured_output
            elif getattr(message, "result", None):
                raw_parts.append(message.result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    raw_parts.append(block.text)

    return _extract_verdict(structured, raw_parts)


def judge_rubric_item(item: str, content: str, model: str | None = None) -> bool:
    """Synchronous entry point for rubric judging."""
    return asyncio.run(_judge_async(item, content, model or DEFAULT_JUDGE_MODEL))
```

- [ ] **Step 2: Run harness unit tests**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add tests/support/harness/_rubric_judge.py
git commit -m "refactor: improve _rubric_judge.py readability"
```

---

### Task 8: Clean up reporter.py

PR feedback: "These comments don't seem helpful." Remove comments that just restate the code.

**Files:**
- Modify: `tests/support/harness/reporter.py`

- [ ] **Step 1: Remove unhelpful comments**

Remove the inline comments that restate what the code does. Keep the module docstring and the `_parse_module` docstring since those explain non-obvious logic. Specifically, remove:

```python
# Remove these comments:
# {module_nodeid: [report, ...]}
# {module_nodeid: max_duration}
# Extract the module path (everything before ::)
# tests/skills/<skill>/test_xxx.py -> (skill, test_xxx)
# tests/core/test_xxx.py -> (core, test_xxx)
# test_xxx
# Verbose flag is registered by root conftest.py via --verbose
# Pick up --verbose from root conftest after all options are registered.
```

The cleaned-up file:

```python
"""Pytest plugin for eval result reporting.

Registered via conftest.py: pytest_plugins = ["tests.support.harness.reporter"]
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath


class EvalReporter:
    """Collects test results and formats a summary table."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose
        self._results: dict[str, list] = defaultdict(list)
        self._durations: dict[str, float] = defaultdict(float)

    def record_result(self, report) -> None:
        module = report.nodeid.split("::")[0]
        self._results[module].append(report)
        if report.duration > self._durations[module]:
            self._durations[module] = report.duration

    def _parse_module(self, module: str) -> tuple[str, str]:
        """Extract (skill_name, test_name) from a module path."""
        parts = PurePosixPath(module).parts
        filename = PurePosixPath(module).stem
        if "skills" in parts:
            idx = list(parts).index("skills")
            skill = parts[idx + 1] if idx + 1 < len(parts) else "unknown"
            return (skill, filename)
        if "core" in parts:
            return ("core", filename)
        return ("other", filename)

    def build_table_rows(self) -> list[dict]:
        rows = []
        for module, reports in sorted(self._results.items()):
            skill, test = self._parse_module(module)
            passed = sum(1 for r in reports if r.passed)
            total = len(reports)
            duration = self._durations[module]
            failures = [r for r in reports if r.failed]
            rows.append({
                "skill": skill,
                "test": test,
                "passed": passed,
                "total": total,
                "duration": duration,
                "failures": failures,
                "module": module,
            })
        return rows

    def compute_totals(self) -> dict:
        all_reports = [r for reports in self._results.values() for r in reports]
        return {
            "passed": sum(1 for r in all_reports if r.passed),
            "total": len(all_reports),
        }

    def format_table(self) -> str:
        rows = self.build_table_rows()
        totals = self.compute_totals()
        lines = []
        lines.append(
            f"{'Skill':<17}{'Test':<28}{'Result':<9}{'Time'}"
        )
        total_duration = 0.0
        for row in rows:
            result = f"{row['passed']}/{row['total']}"
            time_str = f"{row['duration']:.1f}s"
            total_duration += row["duration"]
            lines.append(
                f"{row['skill']:<17}{row['test']:<28}{result:<9}{time_str}"
            )
        lines.append(
            f"{'':<17}{'':<28}{totals['passed']}/{totals['total']:<9}{total_duration:.1f}s"
        )
        return "\n".join(lines)

    def format_failures(self) -> str:
        lines = []
        for row in self.build_table_rows():
            for report in row["failures"]:
                lines.append(f"\n{report.nodeid}")
                if report.longreprtext:
                    lines.append(f"  {report.longreprtext}")
        return "\n".join(lines)


# --- Pytest plugin hooks ---

_reporter: EvalReporter | None = None


def pytest_configure(config) -> None:
    global _reporter
    _reporter = EvalReporter(verbose=False)


def pytest_report_header(config) -> None:
    if _reporter is not None:
        _reporter.verbose = config.getoption("verbose", default=False)


def pytest_runtest_logreport(report) -> None:
    if _reporter is None:
        return
    if report.when != "call":
        return
    _reporter.record_result(report)


def pytest_terminal_summary(terminalreporter, config) -> None:
    if _reporter is None:
        return
    rows = _reporter.build_table_rows()
    if not rows:
        return

    tw = terminalreporter._tw
    tw.sep("=", "Eval Summary")
    tw.line()
    tw.line(_reporter.format_table())

    failure_text = _reporter.format_failures()
    if failure_text.strip():
        tw.line()
        tw.sep("=", "FAILURES")
        tw.line(failure_text)
```

- [ ] **Step 2: Run harness unit tests**

Run: `uv run pytest tests/support/harness/tests/test_reporter.py -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add tests/support/harness/reporter.py
git commit -m "cleanup: remove unhelpful comments from reporter.py"
```

---

### Task 9: Fix pyproject.toml and trailing backslashes

PR feedback: "`test_` not `_test`" — remove the `*_test.py` discovery pattern. Also: "The trailing `\`s on every line is strange."

**Files:**
- Modify: `pyproject.toml:19`
- Modify: `tests/skills/ghostwrite/test_blog_format.py`
- Modify: `tests/skills/ghostwrite/test_email_format.py`
- Modify: `tests/skills/ghostwrite/test_linkedin_format.py`
- Modify: `tests/skills/ghostwrite/test_slack_format.py`
- Modify: `tests/skills/scope/conftest.py`

- [ ] **Step 1: Fix pyproject.toml**

```toml
# old
python_files = ["test_*.py", "*_test.py"]

# new
python_files = ["test_*.py"]
```

- [ ] **Step 2: Remove trailing backslashes from test strings**

The `textwrap.dedent` + trailing `\` pattern forces lines to join. Use regular multi-line strings instead — `dedent` handles the indentation and Python string literals naturally join adjacent lines.

In each ghostwrite test file, replace the SOURCE string. Example for `test_blog_format.py`:

```python
# old
SOURCE = textwrap.dedent("""\
    MLH ran Global Hack Week in March 2026. It was our biggest one yet -- \
    18,000 participants across 120 countries over 7 days. We tried a new \
    format this time where each day had a themed challenge (Day 1 was AI, \
    Day 2 was open source, Day 3 was hardware, etc). The daily themes drove \
    way more engagement than the old format where everything was open-ended. \
    Completion rates went from 34% to 61%. The most popular challenge was \
    the Day 5 "ship a CLI tool" challenge with 4,200 submissions. We're \
    going to keep the themed format for future GHWs.\
""")

# new
SOURCE = textwrap.dedent("""\
    MLH ran Global Hack Week in March 2026. It was our biggest one yet --
    18,000 participants across 120 countries over 7 days. We tried a new
    format this time where each day had a themed challenge (Day 1 was AI,
    Day 2 was open source, Day 3 was hardware, etc). The daily themes drove
    way more engagement than the old format where everything was open-ended.
    Completion rates went from 34% to 61%. The most popular challenge was
    the Day 5 "ship a CLI tool" challenge with 4,200 submissions. We're
    going to keep the themed format for future GHWs.
""")
```

Apply the same pattern to the SOURCE strings in:
- `tests/skills/ghostwrite/test_email_format.py`
- `tests/skills/ghostwrite/test_linkedin_format.py`
- `tests/skills/ghostwrite/test_slack_format.py`

And to the turns strings in:
- `tests/skills/scope/conftest.py`
- `tests/skills/prompt-engineer/test_fix_bad_prompt.py`

**Important:** Removing `\` changes the string content — lines will now have `\n` between them instead of being joined. This means `len(SOURCE)` will be slightly different, which affects the `test_output_length` tests. Since we already set format-appropriate thresholds in Task 3, this is fine.

- [ ] **Step 3: Run harness unit tests**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml tests/skills/
git commit -m "cleanup: remove *_test.py pattern, remove trailing backslashes from test strings"
```

---

### Task 10: Add Makefile parallelism

PR feedback: "There's no parallelism in the tests." Add `pytest-xdist` for parallel test execution.

**Files:**
- Modify: `pyproject.toml` (add pytest-xdist dependency)
- Modify: `Makefile:7`

- [ ] **Step 1: Add pytest-xdist dependency**

```toml
# old
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.15.9",
]

# new
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-xdist>=3.5.0",
    "ruff>=0.15.9",
]
```

- [ ] **Step 2: Update Makefile**

```makefile
# old
test:
	uv run pytest tests/skills/ tests/core/ $(ARGS)

# new
test:
	uv run pytest tests/skills/ tests/core/ -n auto $(ARGS)
```

The `-n auto` flag runs tests in parallel using all available CPU cores. Each test module gets its own worker, so module-scoped fixtures (which run the agent once per file) naturally parallelize.

- [ ] **Step 3: Install and verify**

Run: `uv sync && uv run pytest tests/support/harness/tests/ -n auto -v`
Expected: all harness unit tests pass in parallel

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml Makefile
git commit -m "feat: add parallel test execution with pytest-xdist"
```

---

### Task 11: Update docs/evals.md

PR feedback: consolidate tables, add example output.

**Files:**
- Modify: `docs/evals.md`

- [ ] **Step 1: Consolidate matcher tables and add example output**

Rewrite `docs/evals.md` with a single combined table and an example test run:

```markdown
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
| `output_len_lte(n, on)` | yes | Character count <= n |
| `output_len_gte(n, on)` | yes | Character count >= n |
| `llm_judge(item, on, model=None)` | yes | LLM judge (default Haiku) grades pass/fail |
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
```

- [ ] **Step 2: Commit**

```bash
git add docs/evals.md
git commit -m "docs: consolidate evals.md tables, add example output"
```

---

### Task 12: Final verification

- [ ] **Step 1: Run all harness unit tests**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: all pass

- [ ] **Step 2: Run linter**

Run: `uv run ruff check --fix . && uv run ruff format .`
Expected: clean

- [ ] **Step 3: Verify no stale references**

Run these in parallel:
```bash
grep -r "passes_rubric" tests/ docs/ --include="*.py" --include="*.md"
grep -r "core_checks" tests/ --include="*.py"
grep -r "_test\.py" pyproject.toml
```
Expected: zero results for all three

- [ ] **Step 4: Commit any linter fixes**

```bash
git add -u
git commit -m "cleanup: linter fixes"
```
