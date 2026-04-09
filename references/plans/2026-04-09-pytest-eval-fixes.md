# Pytest Eval Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address PR review feedback from the pytest eval rewrite. Test failures are out of scope — they'll be investigated separately.

**Architecture:** Mechanical renames and refactors first (no behavior change, unit tests verify), then harness code quality, then docs and build improvements.

**Tech Stack:** Python 3.12, pytest 8+, claude-agent-sdk, pydantic

---

## File Map

**Harness files to modify:**
- `tests/support/harness/matchers.py` — rename `passes_rubric` → `llm_judge`, add `parse()` method and `content` param
- `tests/support/harness/_rubric_judge.py` — refactor for readability
- `tests/support/harness/reporter.py` — remove unhelpful comments

**New harness files:**
- `tests/support/harness/extractor.py` — LLM-based structured field extraction (Pydantic + Haiku)

**Test files to modify (rename only — no behavior changes):**
- `tests/skills/ghostwrite/core_checks.py` — rename file → `ghostwrite_helpers.py`
- `tests/skills/ghostwrite/test_blog_format.py` — update import, fix backslashes
- `tests/skills/ghostwrite/test_email_format.py` — update import, fix backslashes
- `tests/skills/ghostwrite/test_linkedin_format.py` — update import, fix backslashes
- `tests/skills/ghostwrite/test_slack_format.py` — update import, fix backslashes
- `tests/skills/ghostwrite/test_refuses_from_scratch.py` — update import (if applicable)
- `tests/skills/summarize/structural_checks.py` — rename method call
- `tests/skills/summarize/test_local_pdf.py` — rename method call
- `tests/skills/summarize/test_pasted_text.py` — rename method call (if used)
- `tests/skills/summarize/test_web_article.py` — rename method call (if used)
- `tests/skills/scope/test_scoping_process.py` — rename method call
- `tests/skills/prompt-engineer/test_fix_bad_prompt.py` — rename method call
- `tests/skills/prompt-engineer/test_structured_extraction.py` — rename method call
- `tests/core/test_no_ai_attribution.py` — rename method call (if used)
- `tests/core/test_skill_triggers.py` — rename method call (if used)

**Config/docs to modify:**
- `pyproject.toml` — remove `*_test.py` pattern
- `Makefile` — add parallel flag
- `docs/evals.md` — consolidate tables, add example output, rename method in docs

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

In every file found in Step 1, replace `.passes_rubric(` with `.llm_judge(`. This is a mechanical find-and-replace across all files. Key files:

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
- Modify: all ghostwrite test files that import from `core_checks`

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

### Task 3: Refactor `_rubric_judge.py` for readability

PR feedback: "This function is tough to read. Let's refactor for readability." The `_judge_async` function mixes streaming, structured output parsing, and fallback logic in one dense block.

**Files:**
- Modify: `tests/support/harness/_rubric_judge.py`

- [ ] **Step 1: Refactor the module**

Rewrite `_rubric_judge.py` with clearer structure — separate the response collection from result parsing:

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

### Task 4: Clean up reporter.py

PR feedback: "These comments don't seem helpful." Remove comments that restate the code.

**Files:**
- Modify: `tests/support/harness/reporter.py`

- [ ] **Step 1: Remove unhelpful comments**

Remove inline comments that restate what the code does. Keep the module docstring and `_parse_module` docstring. Specifically, remove:

```python
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

### Task 5: Fix pyproject.toml and trailing backslashes

PR feedback: "`test_` not `_test`" and "The trailing `\`s on every line is strange."

**Files:**
- Modify: `pyproject.toml:19`
- Modify: ghostwrite test files (SOURCE strings)
- Modify: `tests/skills/scope/conftest.py` (turns strings)
- Modify: `tests/skills/prompt-engineer/test_fix_bad_prompt.py` (turns strings)

- [ ] **Step 1: Fix pyproject.toml**

```toml
# old
python_files = ["test_*.py", "*_test.py"]

# new
python_files = ["test_*.py"]
```

- [ ] **Step 2: Remove trailing backslashes from test strings**

The `textwrap.dedent` + trailing `\` pattern forces lines to join into one long line. Use regular multi-line strings instead — `dedent` handles indentation and the newlines are fine for prompt input.

In each ghostwrite test file, remove the trailing `\` from each line in the SOURCE string. Example for `tests/skills/ghostwrite/test_blog_format.py`:

```python
# old
SOURCE = textwrap.dedent("""\
    MLH ran Global Hack Week in March 2026. It was our biggest one yet -- \
    18,000 participants across 120 countries over 7 days. We tried a new \
    ...
    going to keep the themed format for future GHWs.\
""")

# new
SOURCE = textwrap.dedent("""\
    MLH ran Global Hack Week in March 2026. It was our biggest one yet --
    18,000 participants across 120 countries over 7 days. We tried a new
    ...
    going to keep the themed format for future GHWs.
""")
```

Apply to all SOURCE strings and turns strings in:
- `tests/skills/ghostwrite/test_blog_format.py`
- `tests/skills/ghostwrite/test_email_format.py`
- `tests/skills/ghostwrite/test_linkedin_format.py`
- `tests/skills/ghostwrite/test_slack_format.py`
- `tests/skills/scope/conftest.py`
- `tests/skills/prompt-engineer/test_fix_bad_prompt.py`

- [ ] **Step 3: Run harness unit tests**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml tests/skills/
git commit -m "cleanup: remove *_test.py pattern, remove trailing backslashes from test strings"
```

---

### Task 6: Add `dedent` to harness unit tests

PR feedback: "Use `dedent` on multi-line strings like this for readability. Remember this for python code in the future."

**Files:**
- Modify: `tests/support/harness/tests/test_rubric.py` (if multi-line strings exist without dedent)
- Modify: any other harness test files with multi-line strings

- [ ] **Step 1: Find multi-line strings without dedent**

Run: `grep -n '"""' tests/support/harness/tests/*.py`

Review each file for multi-line strings that aren't wrapped in `textwrap.dedent()`.

- [ ] **Step 2: Wrap multi-line strings in dedent**

Add `import textwrap` and wrap any multi-line string literals in `textwrap.dedent()`. Example:

```python
# old
prompt = """
    You are a strict rubric grader.
    Evaluate the content.
"""

# new
prompt = textwrap.dedent("""\
    You are a strict rubric grader.
    Evaluate the content.
""")
```

- [ ] **Step 3: Run harness unit tests**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add tests/support/harness/tests/
git commit -m "cleanup: use dedent for multi-line strings in harness tests"
```

---

### Task 7: Add Makefile parallelism

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

`-n auto` runs tests in parallel using all available CPU cores. Each test module gets its own worker, so module-scoped fixtures naturally parallelize.

- [ ] **Step 3: Install and verify**

Run: `uv sync && uv run pytest tests/support/harness/tests/ -n auto -v`
Expected: all harness unit tests pass in parallel

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml Makefile
git commit -m "feat: add parallel test execution with pytest-xdist"
```

---

### Task 8: Add structured output extractor

Add LLM-based structured field extraction so tests can parse skill output into Pydantic models and validate/assert on individual fields. Uses Haiku with constrained decoding (same pattern as `_rubric_judge.py`).

**Files:**
- Create: `tests/support/harness/extractor.py`
- Modify: `tests/support/harness/matchers.py` — add `parse()` method, add `content` param to `llm_judge`
- Create: `tests/support/harness/tests/test_extractor.py`

- [ ] **Step 1: Write the failing test for extractor**

Create `tests/support/harness/tests/test_extractor.py`. This test uses a mock to avoid real LLM calls:

```python
import textwrap
from unittest.mock import patch

from pydantic import BaseModel, Field, field_validator

from tests.support.harness.extractor import extract_fields


class SimpleOutput(BaseModel):
    title: str
    summary: str
    items: list[str] = Field(min_length=1, max_length=5)


def test_extract_fields_from_mock():
    mock_result = {"title": "Test", "summary": "A summary", "items": ["one", "two"]}
    with patch("tests.support.harness.extractor._extract_async") as mock_extract:
        mock_extract.return_value = mock_result
        result = extract_fields("some content", SimpleOutput)
        assert isinstance(result, SimpleOutput)
        assert result.title == "Test"
        assert result.items == ["one", "two"]


class StrictOutput(BaseModel):
    name: str
    count: int

    @field_validator("count")
    @classmethod
    def count_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("count must be positive")
        return v


def test_extract_fields_validates_with_pydantic():
    mock_result = {"name": "Test", "count": -1}
    with patch("tests.support.harness.extractor._extract_async") as mock_extract:
        mock_extract.return_value = mock_result
        try:
            extract_fields("some content", StrictOutput)
            assert False, "Should have raised ValidationError"
        except Exception as e:
            assert "count must be positive" in str(e)


def test_extract_fields_generates_schema():
    """Verify model_json_schema() produces a usable schema."""
    schema = SimpleOutput.model_json_schema()
    assert "title" in schema["properties"]
    assert "summary" in schema["properties"]
    assert "items" in schema["properties"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/support/harness/tests/test_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.support.harness.extractor'`

- [ ] **Step 3: Write the extractor module**

Create `tests/support/harness/extractor.py`:

```python
import asyncio
import json

from pydantic import BaseModel
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

DEFAULT_EXTRACT_MODEL = "claude-haiku-4-5-20251001"

_EXTRACT_PROMPT = """\
Extract structured fields from the CONTENT below into the specified JSON schema.
Return ONLY a JSON object matching the schema. No commentary.

CONTENT:
{content}
"""


async def _extract_async(content: str, schema: dict, model: str) -> dict:
    """Send content to an LLM with a JSON schema constraint, return parsed dict."""
    prompt = _EXTRACT_PROMPT.format(content=content[:40_000])
    output_format = {"type": "json_schema", "schema": schema}
    options = ClaudeAgentOptions(model=model, output_format=output_format)

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

    if structured is not None:
        return structured

    raw = "".join(raw_parts).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`")

    return json.loads(raw)


def extract_fields(
    content: str,
    model_class: type[BaseModel],
    llm_model: str | None = None,
) -> BaseModel:
    """Extract structured fields from text using an LLM, validate with Pydantic.

    Sends the content to Haiku with the model's JSON schema as a constraint.
    The LLM extracts field values, then Pydantic validates the result.
    """
    schema = model_class.model_json_schema()
    raw = asyncio.run(
        _extract_async(content, schema, llm_model or DEFAULT_EXTRACT_MODEL)
    )
    return model_class.model_validate(raw)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/support/harness/tests/test_extractor.py -v`
Expected: all pass

- [ ] **Step 5: Add `parse()` and `content` param to EvalResult**

In `tests/support/harness/matchers.py`, add to the `EvalResult` class:

```python
def parse(self, model: type, on: str = "final_message"):
    """Extract structured fields from output using an LLM, validate with Pydantic.

    Uses Haiku to read the output and fill in the model's fields.
    Raises ValidationError if the extracted data doesn't match the schema.
    """
    from .extractor import extract_fields

    sources = _resolve_source(self._run, on)
    text = "\n".join(sources)
    return extract_fields(text, model)
```

And update the existing `llm_judge` method (renamed from `passes_rubric` in Task 1) to accept an optional `content` parameter:

```python
# old
def llm_judge(
    self, item: str, on: str, model: str | None = None
) -> bool:
    from ._rubric_judge import judge_rubric_item

    sources = _resolve_source(self._run, on)
    content = "\n".join(sources)
    return judge_rubric_item(item, content, model=model)

# new
def llm_judge(
    self, item: str, on: str | None = None, content: str | None = None,
    model: str | None = None,
) -> bool:
    """Send item + content to an LLM judge, return pass/fail.

    Pass `on` (source selector like "final_message") or `content` (raw text).
    """
    from ._rubric_judge import judge_rubric_item

    if content is None:
        if on is None:
            raise ValueError("llm_judge requires either `on` or `content`")
        sources = _resolve_source(self._run, on)
        content = "\n".join(sources)

    return judge_rubric_item(item, content, model=model)
```

- [ ] **Step 6: Run all harness unit tests**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add tests/support/harness/extractor.py tests/support/harness/matchers.py
git add tests/support/harness/tests/test_extractor.py
git commit -m "feat: add LLM-based structured output extractor with EvalResult.parse()"
```

---

### Task 9: Update docs/evals.md

PR feedback: consolidate tables, add example output.

**Files:**
- Modify: `docs/evals.md`

- [ ] **Step 1: Rewrite evals.md**

Replace `docs/evals.md` with a version that has a single combined matcher table, documents the new `parse()` and `content` param, and includes example output:

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
| `llm_judge(item, on=None, content=None)` | optional | LLM judge (Haiku) grades pass/fail. Pass `on` for a source or `content` for raw text |
| `parse(model, on="final_message")` | yes | Extract fields into a Pydantic model via LLM. Raises ValidationError on shape mismatch |
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

## Structured output parsing

For skills with defined output templates (e.g. summarize, scope), use `parse()` to extract fields into a Pydantic model. Structural validation happens in Pydantic validators. Semantic checks use `llm_judge` on extracted fields.

```python
from pydantic import BaseModel, Field

class SummarizeOutput(BaseModel):
    title: str
    tldr: str
    cliff_notes: list[str] = Field(min_length=1, max_length=8)
    share: str
    comment: str

def test_structure(result):
    result.parse(SummarizeOutput)  # raises if shape is wrong

def test_tldr_quality(result):
    output = result.parse(SummarizeOutput)
    assert result.llm_judge(
        "The TL;DR leads with the single most important takeaway",
        content=output.tldr,
    )
```

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
```

- [ ] **Step 2: Commit**

```bash
git add docs/evals.md
git commit -m "docs: consolidate evals.md tables, add parse() docs and example output"
```

---

### Task 10: Final verification

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
