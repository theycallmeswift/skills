# Pytest Eval Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the custom JSON-based eval harness with idiomatic pytest -- one format, one runner, self-contained test files.

**Architecture:** The harness core (`runner.py`, `models.py`) is adapted for a new `run_eval()` function API. A new `EvalResult` class wraps `RunResult` with assertion methods. Setup/cleanup helpers compose into callables passed to `run_eval`. A pytest reporter plugin prints a summary table. All JSON eval definitions, RUBRIC.md files, and lint scripts are deleted; their logic is inlined into pytest test files.

**Tech Stack:** Python 3.14, pytest, `claude_agent_sdk`, `textwrap.dedent`

---

### Task 1: EvalResult Matchers (tests/support/harness/matchers.py)

Build the `EvalResult` class that wraps `RunResult` and provides assertion methods returning `bool`.

**Files:**
- Create: `tests/support/harness/matchers.py`
- Create: `tests/support/harness/tests/test_matchers.py`
- Read: `tests/support/harness/runner.py` (for `RunResult` dataclass)
- Read: `tests/support/harness/grader.py` (for `_resolve_source`, `_match_tool`, `_match_skill_invocation` logic to port)

The existing `grader.py` has all the assertion logic as dict-in/dict-out functions. `EvalResult` wraps a `RunResult` and exposes the same logic as method calls returning `bool`. Port the logic directly -- don't import from `grader.py` (it will be deleted later).

- [ ] **Step 1: Write failing tests for deterministic matchers**

```python
# tests/support/harness/tests/test_matchers.py
import re
from fnmatch import fnmatch

from tests.support.harness.matchers import EvalResult
from tests.support.harness.runner import RunResult


def _result(
    stdout="",
    final_message="",
    files_written=None,
    tool_trace=None,
    input_tokens=0,
    output_tokens=0,
    exit_code=0,
    turn_count=1,
    duration_s=0.0,
):
    run = RunResult(
        stdout=stdout,
        files_written=files_written or {},
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_s=duration_s,
        exit_code=exit_code,
        tool_trace=tool_trace or [],
        turn_count=turn_count,
        final_message=final_message,
    )
    return EvalResult(run)


# --- matches_regex / not_matches_regex ---


def test_matches_regex_on_final_message():
    r = _result(final_message="Hey, Sarah -- welcome")
    assert r.matches_regex(r"^Hey, Sarah --", on="final_message")


def test_matches_regex_fails_when_absent():
    r = _result(final_message="Hello world")
    assert not r.matches_regex(r"^Hey", on="stdout")


def test_matches_regex_min_count():
    r = _result(final_message="one? two?")
    assert r.matches_regex(r"\?", on="final_message", min=2)
    assert not r.matches_regex(r"\?", on="final_message", min=3)


def test_matches_regex_max_count():
    r = _result(final_message="one? two? three?")
    assert not r.matches_regex(r"\?", on="final_message", max=2)
    assert r.matches_regex(r"\?", on="final_message", max=3)


def test_not_matches_regex_passes_when_absent():
    r = _result(final_message="clean output")
    assert r.not_matches_regex(r"forbidden", on="final_message")


def test_not_matches_regex_fails_when_present():
    r = _result(final_message="forbidden word")
    assert not r.not_matches_regex(r"forbidden", on="final_message")


def test_matches_regex_on_stdout():
    r = _result(stdout="VISIBLE", final_message="HIDDEN")
    assert r.matches_regex("VISIBLE", on="stdout")
    assert not r.matches_regex("VISIBLE", on="final_message")


def test_matches_regex_on_files_glob():
    r = _result(files_written={"a.md": "alpha", "b.md": "beta", "c.txt": "gamma"})
    assert r.matches_regex("alpha", on="files.*.md")
    assert not r.matches_regex("gamma", on="files.*.md")


# --- contains / contains_all / not_contains ---


def test_contains_passes():
    r = _result(final_message="the answer is 42")
    assert r.contains("42", on="final_message")


def test_contains_fails():
    r = _result(final_message="hello")
    assert not r.contains("world", on="final_message")


def test_contains_all_passes():
    r = _result(final_message="450 fellows, 30% up, 92% rec rate")
    assert r.contains_all(["450", "30%", "92%"], on="final_message")


def test_contains_all_fails_on_missing():
    r = _result(final_message="450 fellows, 30% up")
    assert not r.contains_all(["450", "30%", "92%"], on="final_message")


def test_not_contains_passes():
    r = _result(final_message="clean")
    assert r.not_contains("dirty", on="final_message")


def test_not_contains_fails():
    r = _result(final_message="dirty string")
    assert not r.not_contains("dirty", on="final_message")


# --- output_len ---


def test_output_len_lte():
    r = _result(final_message="short")
    assert r.output_len_lte(100, on="final_message")
    assert not r.output_len_lte(3, on="final_message")


def test_output_len_gte():
    r = _result(final_message="hello world")
    assert r.output_len_gte(5, on="final_message")
    assert not r.output_len_gte(100, on="final_message")


# --- token_usage_lte ---


def test_token_usage_lte():
    r = _result(input_tokens=1000, output_tokens=500)
    assert r.token_usage_lte(2000)
    assert not r.token_usage_lte(1000)


# --- tool_called / not_tool_called ---


def test_tool_called():
    r = _result(tool_trace=[
        {"name": "mcp__brightdata__scrape_as_markdown", "input": {}, "turn": 1}
    ])
    assert r.tool_called("scrape_as_markdown")
    assert not r.tool_called("WebFetch")


def test_not_tool_called():
    r = _result(tool_trace=[{"name": "Read", "input": {}, "turn": 1}])
    assert r.not_tool_called("WebFetch")
    assert not r.not_tool_called("Read")


# --- skill_invoked / not_skill_invoked ---


def test_skill_invoked_bare():
    r = _result(tool_trace=[
        {"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1}
    ])
    assert r.skill_invoked("ghostwrite")
    assert not r.skill_invoked("summarize")


def test_skill_invoked_prefixed():
    r = _result(tool_trace=[
        {"name": "Skill", "input": {"skill": "mechaswift:ghostwrite"}, "turn": 1}
    ])
    assert r.skill_invoked("ghostwrite")


def test_not_skill_invoked():
    r = _result(tool_trace=[{"name": "Read", "input": {}, "turn": 1}])
    assert r.not_skill_invoked("ghostwrite")


def test_not_skill_invoked_fails_when_fired():
    r = _result(tool_trace=[
        {"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1}
    ])
    assert not r.not_skill_invoked("ghostwrite")


# --- trace_order ---


def test_trace_order_passes():
    r = _result(tool_trace=[
        {"name": "scrape_as_markdown", "input": {}, "turn": 1},
        {"name": "Bash", "input": {}, "turn": 1},
        {"name": "Write", "input": {}, "turn": 1},
    ])
    assert r.trace_order(["scrape_as_markdown", "Write"])


def test_trace_order_fails_wrong_order():
    r = _result(tool_trace=[
        {"name": "Write", "input": {}, "turn": 1},
        {"name": "scrape_as_markdown", "input": {}, "turn": 1},
    ])
    assert not r.trace_order(["scrape_as_markdown", "Write"])


# --- trace_count_lte ---


def test_trace_count_lte():
    r = _result(tool_trace=[{"name": "Bash", "input": {}, "turn": 1}] * 2)
    assert r.trace_count_lte("Bash", 3)
    assert not r.trace_count_lte("Bash", 1)


# --- turn_count_lte ---


def test_turn_count_lte():
    r = _result(turn_count=2)
    assert r.turn_count_lte(3)
    assert not r.turn_count_lte(1)


# --- file_contains / not_file_contains ---


def test_file_contains_text():
    r = _result(files_written={"references/specs/foo.md": "Out of scope: X"})
    assert r.file_contains("references/specs/*.md", text="Out of scope")
    assert not r.file_contains("references/specs/*.md", text="missing")


def test_file_contains_regex():
    r = _result(files_written={"a.md": "allowlist entry"})
    assert r.file_contains("*.md", regex=r"(?i)(allowlist|routing)")
    assert not r.file_contains("*.md", regex=r"(?i)missing")


def test_file_contains_no_matching_file():
    r = _result(files_written={"other.txt": "x"})
    assert not r.file_contains("*.md", text="x")


def test_not_file_contains():
    r = _result(files_written={"a.md": "clean content"})
    assert r.not_file_contains("*.md", text="forbidden")
    assert not r.not_file_contains("*.md", text="clean")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/support/harness/tests/test_matchers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.support.harness.matchers'`

- [ ] **Step 3: Implement EvalResult**

```python
# tests/support/harness/matchers.py
import fnmatch
import re
from math import inf

from .runner import RunResult


def _resolve_source(run: RunResult, on: str) -> list[str]:
    """Return the list of text sources to check against."""
    if on == "final_message":
        return [run.final_message or ""]
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


def _match_tool(trace: list[dict], needle: str) -> bool:
    return any(needle in entry.get("name", "") for entry in trace)


def _match_skill(trace: list[dict], skill: str) -> bool:
    for entry in trace:
        if entry.get("name") != "Skill":
            continue
        inv = entry.get("input", {}).get("skill", "")
        if inv == skill or inv.endswith(f":{skill}"):
            return True
    return False


class EvalResult:
    """Wraps a RunResult with assertion methods that return bool."""

    def __init__(self, run: RunResult) -> None:
        self._run = run
        self.stdout = run.stdout
        self.final_message = run.final_message
        self.files_written = run.files_written
        self.tool_trace = run.tool_trace
        self.input_tokens = run.input_tokens
        self.output_tokens = run.output_tokens
        self.exit_code = run.exit_code
        self.turn_count = run.turn_count
        self.duration_s = run.duration_s

    # --- Content matchers ---

    def matches_regex(
        self, pattern: str, on: str, min: int = 1, max: float = inf
    ) -> bool:
        sources = _resolve_source(self._run, on)
        count = sum(len(re.findall(pattern, s)) for s in sources)
        return count >= min and count <= max

    def not_matches_regex(self, pattern: str, on: str) -> bool:
        return self.matches_regex(pattern, on, min=0, max=0)

    def contains(self, text: str, on: str) -> bool:
        sources = _resolve_source(self._run, on)
        return any(text in s for s in sources)

    def contains_all(self, texts: list[str], on: str) -> bool:
        sources = _resolve_source(self._run, on)
        haystack = "\n".join(sources)
        return all(t in haystack for t in texts)

    def not_contains(self, text: str, on: str) -> bool:
        return not self.contains(text, on)

    def output_len_lte(self, n: int, on: str) -> bool:
        sources = _resolve_source(self._run, on)
        return sum(len(s) for s in sources) <= n

    def output_len_gte(self, n: int, on: str) -> bool:
        sources = _resolve_source(self._run, on)
        return sum(len(s) for s in sources) >= n

    # --- Token matchers ---

    def token_usage_lte(self, n: int) -> bool:
        return (self.input_tokens + self.output_tokens) <= n

    # --- Trace matchers ---

    def tool_called(self, name: str) -> bool:
        return _match_tool(self.tool_trace, name)

    def not_tool_called(self, name: str) -> bool:
        return not _match_tool(self.tool_trace, name)

    def skill_invoked(self, name: str) -> bool:
        return _match_skill(self.tool_trace, name)

    def not_skill_invoked(self, name: str) -> bool:
        return not _match_skill(self.tool_trace, name)

    def trace_order(self, tools: list[str]) -> bool:
        names = [e.get("name", "") for e in self.tool_trace]
        cursor = 0
        for needle in tools:
            found = False
            for i in range(cursor, len(names)):
                if needle in names[i]:
                    cursor = i + 1
                    found = True
                    break
            if not found:
                return False
        return True

    def trace_count_lte(self, tool: str, n: int) -> bool:
        count = sum(1 for e in self.tool_trace if tool in e.get("name", ""))
        return count <= n

    def turn_count_lte(self, n: int) -> bool:
        return self.turn_count <= n

    # --- File matchers ---

    def file_contains(
        self, path_glob: str, text: str | None = None, regex: str | None = None
    ) -> bool:
        matches = [
            (p, c)
            for p, c in self.files_written.items()
            if fnmatch.fnmatch(p, path_glob)
        ]
        if not matches:
            return False
        for _path, content in matches:
            if text is not None and text in content:
                return True
            if regex is not None and re.search(regex, content):
                return True
        return False

    def not_file_contains(
        self, path_glob: str, text: str | None = None, regex: str | None = None
    ) -> bool:
        return not self.file_contains(path_glob, text=text, regex=regex)

    # --- Rubric matcher ---

    def passes_rubric(
        self, item: str, on: str, model: str | None = None
    ) -> bool:
        """Send item + content to an LLM judge, return pass/fail.

        Uses Haiku by default. The judge sees the item text and the
        targeted content, returns a structured pass/fail verdict.
        """
        from ._rubric_judge import judge_rubric_item

        sources = _resolve_source(self._run, on)
        content = "\n".join(sources)
        return judge_rubric_item(item, content, model=model)
```

- [ ] **Step 4: Create the rubric judge helper**

```python
# tests/support/harness/_rubric_judge.py
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


def _parse_fallback(raw: str) -> dict:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`")
    return json.loads(raw)


async def _judge_async(item: str, content: str, model: str) -> bool:
    prompt = _JUDGE_PROMPT.format(item=item, content=content[:40_000])
    options = ClaudeAgentOptions(model=model, output_format=_JUDGE_SCHEMA)
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
        return structured.get("pass", False)
    raw = "".join(parts).strip()
    return _parse_fallback(raw).get("pass", False)


def judge_rubric_item(
    item: str, content: str, model: str | None = None
) -> bool:
    return asyncio.run(
        _judge_async(item, content, model or DEFAULT_JUDGE_MODEL)
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/support/harness/tests/test_matchers.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add tests/support/harness/matchers.py tests/support/harness/_rubric_judge.py tests/support/harness/tests/test_matchers.py
git commit -m "feat: add EvalResult matchers for pytest eval rewrite"
```

---

### Task 2: Setup Helpers (tests/support/harness/setup.py)

Build composable setup/cleanup callables that `run_eval` will use.

**Files:**
- Create: `tests/support/harness/setup.py`
- Create: `tests/support/harness/tests/test_setup.py`
- Read: `tests/support/harness/runner.py` (for `copy_context_paths`)
- Read: `tests/support/harness/discovery.py` (for `SKILL_PREAMBLE` pattern)

- [ ] **Step 1: Write failing tests**

```python
# tests/support/harness/tests/test_setup.py
import textwrap
from pathlib import Path

from tests.support.harness.setup import (
    cleanup_globs,
    compose,
    copy_files,
    skill_setup,
)


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    root = tmp_path / "project"
    (root / "skills" / "summarize").mkdir(parents=True)
    (root / "skills" / "summarize" / "SKILL.md").write_text("# Summarize")
    (root / "skills" / "summarize" / "references").mkdir()
    (root / "skills" / "summarize" / "references" / "examples.md").write_text(
        "# Examples"
    )
    (root / "AGENTS.md").write_text("# Agents")
    (root / "tests" / "support" / "fixtures").mkdir(parents=True)
    (root / "tests" / "support" / "fixtures" / "test-paper.pdf").write_bytes(
        b"fake pdf"
    )
    return root


def test_skill_setup_copies_skill_dir_and_agents(tmp_path):
    root = _make_project(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    setup_fn = skill_setup("summarize", root)
    setup_fn(cwd)

    assert (cwd / "skills" / "summarize" / "SKILL.md").read_text() == "# Summarize"
    assert (cwd / "skills" / "summarize" / "references" / "examples.md").exists()
    assert (cwd / "AGENTS.md").read_text() == "# Agents"


def test_skill_setup_prepends_preamble(tmp_path):
    root = _make_project(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    setup_fn = skill_setup("summarize", root)
    setup_fn(cwd)

    preamble_file = cwd / ".skill_preamble"
    assert preamble_file.exists()
    assert "skills/summarize/SKILL.md" in preamble_file.read_text()


def test_copy_files_copies_to_cwd(tmp_path):
    root = _make_project(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    copy_fn = copy_files("tests/support/fixtures/test-paper.pdf", project_root=root)
    copy_fn(cwd)

    assert (cwd / "test-paper.pdf").read_text() == "fake pdf"


def test_cleanup_globs_removes_matching_files(tmp_path):
    cwd = tmp_path / "cwd"
    (cwd / "references" / "specs").mkdir(parents=True)
    (cwd / "references" / "specs" / "2026-01-01-demo.md").write_text("x")
    (cwd / "references" / "specs" / "keep.md").write_text("y")

    cleanup_fn = cleanup_globs("references/specs/2026-*-demo*.md")
    cleanup_fn(cwd)

    assert not (cwd / "references" / "specs" / "2026-01-01-demo.md").exists()
    assert (cwd / "references" / "specs" / "keep.md").exists()


def test_compose_runs_all_functions_in_order(tmp_path):
    root = _make_project(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    composed = compose(
        skill_setup("summarize", root),
        copy_files("tests/support/fixtures/test-paper.pdf", project_root=root),
    )
    composed(cwd)

    assert (cwd / "skills" / "summarize" / "SKILL.md").exists()
    assert (cwd / "test-paper.pdf").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/support/harness/tests/test_setup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tests.support.harness.setup'`

- [ ] **Step 3: Implement setup helpers**

```python
# tests/support/harness/setup.py
import shutil
from collections.abc import Callable
from pathlib import Path

SKILL_PREAMBLE = "Before responding, read and follow skills/{name}/SKILL.md.\n\n"


def skill_setup(skill: str, project_root: Path) -> Callable[[Path], None]:
    """Copy skill dir + AGENTS.md into temp cwd, write preamble file."""

    def _setup(cwd: Path) -> None:
        # Copy skill directory
        skill_dir = project_root / "skills" / skill
        dest_skill = cwd / "skills" / skill
        dest_skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, dest_skill, symlinks=False, dirs_exist_ok=True)

        # Copy AGENTS.md
        agents_src = project_root / "AGENTS.md"
        if agents_src.exists():
            shutil.copy2(agents_src, cwd / "AGENTS.md")

        # Write preamble file for runner to prepend to first turn
        preamble = SKILL_PREAMBLE.format(name=skill)
        (cwd / ".skill_preamble").write_text(preamble)

    return _setup


def copy_files(*paths: str, project_root: Path) -> Callable[[Path], None]:
    """Copy files from project into temp cwd (flat, not preserving directory structure)."""

    def _setup(cwd: Path) -> None:
        for rel_path in paths:
            src = project_root / rel_path
            dest = cwd / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    return _setup


def cleanup_globs(*patterns: str) -> Callable[[Path], None]:
    """Delete files matching globs relative to the directory passed in."""

    def _cleanup(cwd: Path) -> None:
        for pattern in patterns:
            for match in cwd.glob(pattern):
                if match.is_dir():
                    shutil.rmtree(match, ignore_errors=True)
                else:
                    match.unlink(missing_ok=True)

    return _cleanup


def compose(*fns: Callable[[Path], None]) -> Callable[[Path], None]:
    """Run multiple setup/cleanup functions in sequence."""

    def _composed(cwd: Path) -> None:
        for fn in fns:
            fn(cwd)

    return _composed
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/support/harness/tests/test_setup.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/setup.py tests/support/harness/tests/test_setup.py
git commit -m "feat: add setup/cleanup helpers for pytest eval rewrite"
```

---

### Task 3: Adapt run_eval Function (tests/support/harness/runner.py)

Add a new `run_eval()` function to `runner.py` that uses the setup/cleanup callable pattern and returns `EvalResult`.

**Files:**
- Modify: `tests/support/harness/runner.py`
- Modify: `tests/support/harness/tests/test_runner.py`

The existing `run_claude()` stays -- it's the low-level SDK caller. `run_eval()` is a higher-level function that creates a temp dir, calls setup, runs `run_claude`, calls cleanup, and returns `EvalResult`.

- [ ] **Step 1: Write failing test for run_eval**

Add to the bottom of `tests/support/harness/tests/test_runner.py`:

```python
def test_run_eval_calls_setup_and_cleanup(tmp_path, monkeypatch):
    from tests.support.harness.matchers import EvalResult
    from tests.support.harness.runner import RunResult, run_eval

    setup_called = []
    cleanup_called = []

    def fake_setup(cwd):
        setup_called.append(str(cwd))
        (cwd / "setup.txt").write_text("done")

    def fake_cleanup(cwd):
        cleanup_called.append(str(cwd))

    async def fake_run_claude(turns, cwd, context_paths, project_root, timeout_s=300, model=None):
        # Verify setup ran before agent
        assert (cwd / "setup.txt").exists()
        return RunResult(
            stdout="hello",
            files_written={},
            input_tokens=1,
            output_tokens=1,
            duration_s=0.01,
            exit_code=0,
            tool_trace=[],
            turn_count=len(turns),
            final_message="hello",
        )

    import tests.support.harness.runner as runner_mod
    monkeypatch.setattr(runner_mod, "run_claude", fake_run_claude)

    result = run_eval(
        project_root=tmp_path,
        turns=["test"],
        setup=fake_setup,
        cleanup=fake_cleanup,
    )

    assert isinstance(result, EvalResult)
    assert result.final_message == "hello"
    assert len(setup_called) == 1
    assert len(cleanup_called) == 1


def test_run_eval_reads_preamble_file(tmp_path, monkeypatch):
    from tests.support.harness.runner import RunResult, run_eval

    captured_turns = []

    def fake_setup(cwd):
        (cwd / ".skill_preamble").write_text("Read SKILL.md first.\n\n")

    async def fake_run_claude(turns, cwd, context_paths, project_root, timeout_s=300, model=None):
        captured_turns.extend(turns)
        return RunResult(
            stdout="ok",
            files_written={},
            input_tokens=1,
            output_tokens=1,
            duration_s=0.01,
            exit_code=0,
            tool_trace=[],
            turn_count=len(turns),
            final_message="ok",
        )

    import tests.support.harness.runner as runner_mod
    monkeypatch.setattr(runner_mod, "run_claude", fake_run_claude)

    run_eval(
        project_root=tmp_path,
        turns=["Summarize this article"],
    )
    # Without setup writing a preamble, turns pass through unchanged
    assert captured_turns == ["Summarize this article"]

    captured_turns.clear()
    run_eval(
        project_root=tmp_path,
        turns=["Summarize this article"],
        setup=fake_setup,
    )
    assert captured_turns[0].startswith("Read SKILL.md first.")
    assert "Summarize this article" in captured_turns[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/support/harness/tests/test_runner.py::test_run_eval_calls_setup_and_cleanup -v`
Expected: FAIL with `ImportError: cannot import name 'run_eval'`

- [ ] **Step 3: Implement run_eval**

Add to the bottom of `tests/support/harness/runner.py`:

```python
import asyncio as _asyncio
import tempfile as _tempfile
from collections.abc import Callable as _Callable


def run_eval(
    project_root: Path,
    turns: list[str],
    setup: _Callable[[Path], None] | None = None,
    cleanup: _Callable[[Path], None] | None = None,
    model: str | None = None,
) -> "EvalResult":
    """High-level eval runner: temp dir, setup, agent run, cleanup, return EvalResult."""
    from .matchers import EvalResult

    with _tempfile.TemporaryDirectory(prefix="eval-cwd-") as tmp:
        cwd = Path(tmp)

        if setup is not None:
            setup(cwd)

        # Check for preamble written by skill_setup
        preamble_path = cwd / ".skill_preamble"
        actual_turns = list(turns)
        if preamble_path.exists():
            preamble = preamble_path.read_text()
            actual_turns[0] = preamble + actual_turns[0]

        run = _asyncio.run(
            run_claude(
                turns=actual_turns,
                cwd=cwd,
                context_paths=[],
                project_root=project_root,
                model=model,
            )
        )

        if cleanup is not None:
            cleanup(cwd)

    return EvalResult(run)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/support/harness/tests/test_runner.py -v -k "run_eval"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/runner.py tests/support/harness/tests/test_runner.py
git commit -m "feat: add run_eval function wrapping agent execution"
```

---

### Task 4: Reporter Plugin (tests/support/harness/reporter.py)

Rewrite the reporter as a pytest plugin that prints a summary table.

**Files:**
- Rewrite: `tests/support/harness/reporter.py`
- Create: `tests/support/harness/tests/test_reporter.py` (rewritten)

The current reporter is tightly coupled to the orchestrator's `CaseResult` / `RunPlan` types. The new reporter is a pytest plugin that hooks into the test reporting lifecycle and builds a table from pytest's own `TestReport` objects.

- [ ] **Step 1: Write failing tests for the reporter plugin**

```python
# tests/support/harness/tests/test_reporter.py
import textwrap

from tests.support.harness.reporter import EvalReporter


def _make_report(nodeid, passed, duration=1.0):
    """Create a minimal mock test report."""

    class FakeReport:
        def __init__(self):
            self.nodeid = nodeid
            self.when = "call"
            self.passed = passed
            self.failed = not passed
            self.duration = duration
            self.longreprtext = "" if passed else "AssertionError: test failed"

    return FakeReport()


def test_reporter_groups_by_module():
    r = EvalReporter(verbose=False)
    r.record_result(_make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_greeting", True))
    r.record_result(_make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_sign_off", False))
    r.record_result(_make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_numbers", True))

    rows = r.build_table_rows()
    assert len(rows) == 1
    row = rows[0]
    assert row["skill"] == "ghostwrite"
    assert row["test"] == "test_sponsor_email"
    assert row["passed"] == 2
    assert row["total"] == 3


def test_reporter_handles_core_tests():
    r = EvalReporter(verbose=False)
    r.record_result(_make_report("tests/core/test_skill_triggers.py::test_ghostwrite_trigger", True))
    r.record_result(_make_report("tests/core/test_skill_triggers.py::test_scope_trigger", True))

    rows = r.build_table_rows()
    assert len(rows) == 1
    assert rows[0]["skill"] == "core"
    assert rows[0]["test"] == "test_skill_triggers"


def test_reporter_computes_totals():
    r = EvalReporter(verbose=False)
    r.record_result(_make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_a", True))
    r.record_result(_make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_b", False))
    r.record_result(_make_report("tests/skills/summarize/test_devto_article.py::test_c", True))

    totals = r.compute_totals()
    assert totals["passed"] == 2
    assert totals["total"] == 3


def test_reporter_format_output():
    r = EvalReporter(verbose=False)
    r.record_result(_make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_a", True, 15.2))
    r.record_result(_make_report("tests/skills/ghostwrite/test_sponsor_email.py::test_b", False, 15.2))

    output = r.format_table()
    assert "ghostwrite" in output
    assert "test_sponsor_email" in output
    assert "1/2" in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/support/harness/tests/test_reporter.py -v`
Expected: FAIL with `ImportError: cannot import name 'EvalReporter'`

- [ ] **Step 3: Implement the reporter plugin**

```python
# tests/support/harness/reporter.py
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
        # {module_nodeid: [report, ...]}
        self._results: dict[str, list] = defaultdict(list)
        # {module_nodeid: max_duration}
        self._durations: dict[str, float] = defaultdict(float)

    def record_result(self, report) -> None:
        # Extract the module path (everything before ::)
        module = report.nodeid.split("::")[0]
        self._results[module].append(report)
        if report.duration > self._durations[module]:
            self._durations[module] = report.duration

    def _parse_module(self, module: str) -> tuple[str, str]:
        """Extract skill name and test name from module path."""
        parts = PurePosixPath(module).parts
        # tests/skills/<skill>/test_xxx.py -> (skill, test_xxx)
        # tests/core/test_xxx.py -> (core, test_xxx)
        filename = PurePosixPath(module).stem  # test_xxx
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
    # Verbose flag is registered by root conftest.py via --verbose
    _reporter = EvalReporter(verbose=False)


def pytest_report_header(config) -> None:
    """Pick up --verbose from root conftest after all options are registered."""
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/support/harness/tests/test_reporter.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/reporter.py tests/support/harness/tests/test_reporter.py
git commit -m "feat: rewrite reporter as pytest plugin with table output"
```

---

### Task 5: Root conftest.py and CLI Options

Wire up the `run_eval` fixture, `--model`, `--verbose` CLI options, and register the reporter plugin.

Tests are auto-tagged by folder via pytest's `rootdir` detection — no subfolder conftest.py files needed just for marks.

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Create tests/conftest.py**

```python
# tests/conftest.py
import pytest
from pathlib import Path

from tests.support.harness.runner import run_eval as harness_run_eval

pytest_plugins = ["tests.support.harness.reporter"]


def pytest_addoption(parser):
    parser.addoption(
        "--model",
        action="store",
        default=None,
        help="Override the model the agent uses for eval runs",
    )


@pytest.fixture(scope="session")
def project_root():
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def eval_model(request):
    return request.config.getoption("--model")


@pytest.fixture(scope="module")
def run_eval(project_root, eval_model):
    def _run(**kwargs):
        if eval_model and "model" not in kwargs:
            kwargs["model"] = eval_model
        return harness_run_eval(project_root=project_root, **kwargs)
    return _run
```

Note: `--verbose` is pytest's built-in flag (`-v`). The reporter plugin reads `config.getoption("verbose")` to detect it. No custom option needed.

- [ ] **Step 2: Verify conftest loads without errors**

Run: `uv run pytest tests/conftest.py --co -q`
Expected: No errors (dry-run collection)

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "feat: add root conftest.py with run_eval fixture and CLI options"
```

---

### Task 6: Ghostwrite Skill Tests

Migrate `tests/ghostwrite.json` to two pytest test files. Inline the lint checks from `skills/ghostwrite/lint.py`.

**Files:**
- Create: `tests/skills/ghostwrite/test_sponsor_email.py`
- Create: `tests/skills/ghostwrite/test_linkedin_from_scratch.py`
- Read: `tests/ghostwrite.json` (source assertions)
- Read: `skills/ghostwrite/lint.py` (checks to inline)

The `script_name: ghostwrite` assertion from the JSON ran `lint.py` which checks: no em dashes, no banned phrases, no AI attribution. These become inline `assert` statements.

- [ ] **Step 1: Create test_sponsor_email.py**

```python
# tests/skills/ghostwrite/test_sponsor_email.py
import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Rewrite this as an email to our sponsor contact Sarah:

                Hey so I wanted to reach out because we just wrapped up Season 3 of the Fellowship and the numbers were really strong. We had 450 fellows complete the program which is up 30% from last season. 92% of them said they'd recommend it to a friend. I think this is a great opportunity for us to talk about renewing the sponsorship for next season and maybe even expanding the scope of what we do together. Let me know if you'd be open to hopping on a call next week to discuss.\
            """),
        ],
        setup=skill_setup("ghostwrite", project_root),
    )


# --- Lint checks (inlined from skills/ghostwrite/lint.py) ---


def test_no_em_dash(result):
    assert result.not_contains("\u2014", on="final_message")


def test_no_banned_phrases(result):
    assert result.not_matches_regex(r"\bexcited to share\b", on="final_message")
    assert result.not_matches_regex(r"\bleverage[ds]?\b", on="final_message")
    assert result.not_matches_regex(r"\becosystem\b", on="final_message")
    assert result.not_matches_regex(r"\bdelve[ds]?\b", on="final_message")
    assert result.not_matches_regex(r"\bsynergy\b", on="final_message")
    assert result.not_matches_regex(r"\bgame[- ]changer\b", on="final_message")
    assert result.not_matches_regex(r"\bparadigm shift\b", on="final_message")
    assert result.not_matches_regex(r"\babsolutely incredible\b", on="final_message")


def test_no_ai_attribution(result):
    assert result.not_matches_regex(r"Generated with \[?Claude", on="final_message")
    assert result.not_matches_regex(r"Co-Authored-By:\s*Claude", on="final_message")
    assert result.not_matches_regex(r"\bAI-assisted\b", on="final_message")


# --- Content assertions (from evals.json) ---


def test_greeting_format(result):
    assert result.matches_regex(r"(?m)^Hey, Sarah --", on="final_message")


def test_sign_off(result):
    assert result.matches_regex(
        r"(?m)(- Swift|Happy Hacking,\s*\nSwift)\s*$", on="final_message"
    )


def test_preserves_key_numbers(result):
    assert result.contains_all(["450", "30%", "92%"], on="final_message")


def test_output_length(result):
    assert result.output_len_lte(600, on="final_message")
```

- [ ] **Step 2: Create test_linkedin_from_scratch.py**

The model should refuse to draft from scratch — lint checks (em dashes, attribution) don't apply since no content is produced.

```python
# tests/skills/ghostwrite/test_linkedin_from_scratch.py
import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Write a LinkedIn post announcing that MLH is partnering with a new AI company to offer hackathon participants access to their API.\
            """),
        ],
        setup=skill_setup("ghostwrite", project_root),
    )


def test_refuses_to_draft(result):
    assert result.passes_rubric(
        "Output does NOT contain a full LinkedIn post draft. Instead, it explains that ghostwrite is a rewriter and asks the user to provide source content.",
        on="final_message",
    )
```

- [ ] **Step 3: Verify tests are collected**

Run: `uv run pytest tests/skills/ghostwrite/ --co -q`
Expected: Lists all test functions without errors

- [ ] **Step 4: Commit**

```bash
git add tests/skills/ghostwrite/test_sponsor_email.py tests/skills/ghostwrite/test_linkedin_from_scratch.py
git commit -m "feat: add ghostwrite skill tests (migrated from evals.json)"
```

---

### Task 7: Summarize Skill Tests

Migrate `tests/summarize.json` to 3 pytest test files. Inline summarize lint checks. The three web-URL cases (dev.to, rust tab orchestrator, anthropic character) are combined into a single `test_web_article.py` using one stable URL — they test the same skill behavior (fetch + summarize). `test_short_input` is dropped as redundant with `test_pasted_text`.

**Files:**
- Create: `tests/skills/summarize/test_web_article.py`
- Create: `tests/skills/summarize/test_local_pdf.py`
- Create: `tests/skills/summarize/test_pasted_text.py`
- Read: `tests/summarize.json`
- Read: `skills/summarize/lint.py`

The `script_name: summarize` lint checks: title format, summary paragraph, bullet count (1-8), share block, comment block, no em dashes, no narration prefix. These become inline assertions.

- [ ] **Step 1: Create test_web_article.py**

Combines the three web-URL cases (dev.to article, rust tab orchestrator, anthropic character) into one test file with one stable URL. They all test the same behavior: fetch a URL via Brightdata and produce a structured summary.

```python
# tests/skills/summarize/test_web_article.py
import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Summarize this page for me https://www.anthropic.com/research/claude-character\
            """),
        ],
        setup=skill_setup("summarize", project_root),
    )


# --- Structural checks (inlined from skills/summarize/lint.py) ---


def test_starts_with_title(result):
    assert result.passes_rubric(
        "Output starts with a markdown H1 title (# ) on the first non-empty line",
        on="final_message",
    )


def test_has_summary_paragraph(result):
    assert result.passes_rubric(
        "There is a non-list paragraph between the title and the first bullet list",
        on="final_message",
    )


def test_has_share_block(result):
    assert result.matches_regex(r"(?im)^\s*(?:#+\s*share\b|\*\*share\*\*)", on="final_message")


def test_has_comment_block(result):
    assert result.matches_regex(r"(?im)^\s*(?:#+\s*comment\b|\*\*comment\*\*)", on="final_message")


def test_no_em_dash(result):
    assert result.not_contains("\u2014", on="final_message")


def test_no_narration_prefix(result):
    assert result.not_matches_regex(
        r"^(Let me|Now I|I'll draft|I have the|Here's the summary)",
        on="final_message",
    )


def test_has_source_link(result):
    assert result.matches_regex(
        r"\[.*\]\(https://www\.anthropic\.com/research/claude-character[^)]*\)",
        on="final_message",
    )


# --- Tool trace assertions ---


def test_uses_brightdata(result):
    assert result.tool_called("scrape_as_markdown")


def test_no_webfetch(result):
    assert result.not_tool_called("WebFetch")


def test_no_websearch(result):
    assert result.not_tool_called("WebSearch")
```

- [ ] **Step 2: Create test_local_pdf.py**

```python
# tests/skills/summarize/test_local_pdf.py
import textwrap

import pytest

from tests.support.harness.setup import compose, copy_files, skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=["Summarize this PDF: test-paper.pdf"],
        setup=compose(
            skill_setup("summarize", project_root),
            copy_files("tests/support/fixtures/test-paper.pdf", project_root=project_root),
        ),
    )


def test_title_from_content(result):
    assert result.passes_rubric(
        "Title is based on the document/paper title or filename, not a generic placeholder",
        on="final_message",
    )


def test_no_em_dash(result):
    assert result.not_contains("\u2014", on="final_message")


def test_no_brightdata(result):
    assert result.not_tool_called("brightdata")


def test_uses_read(result):
    assert result.tool_called("Read")


def test_no_webfetch(result):
    assert result.not_tool_called("WebFetch")


def test_no_websearch(result):
    assert result.not_tool_called("WebSearch")
```

- [ ] **Step 3: Create test_pasted_text.py**

```python
# tests/skills/summarize/test_pasted_text.py
import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Summarize this for me:

                The rise of the pull request has fundamentally reshaped how software teams collaborate. Originally introduced by GitHub in 2008 as a lightweight way to propose changes across forks, the pull request has evolved into the primary unit of code review, discussion, and integration in modern engineering workflows. Teams argue about PR size, PR templates, PR etiquette, and how long a PR can sit in review before it becomes stale. Companies have built entire product lines around PR automation -- linters that comment inline, bots that auto-assign reviewers based on CODEOWNERS, dashboards that show how long each PR spent waiting at each stage.

                But the pull request has a dark side. Large PRs are where bugs hide, because reviewers skim when they should read. Small PRs fragment context, forcing reviewers to hold a mental model across six tabs. Teams that merge PRs too fast ship bugs; teams that merge too slow ship nothing. The median PR in a busy repository sits in review for two days, and those two days are where velocity goes to die. Solving the pull request problem has become a cottage industry: trunk-based development advocates, stacked diff tools like Graphite, and AI review bots all claim to have the answer.

                The real answer is probably boring: small, focused changes; reviewers who actually read; and a team culture that treats a pending PR as a shared problem, not one person's backlog item.\
            """),
        ],
        setup=skill_setup("summarize", project_root),
    )


def test_no_em_dash(result):
    assert result.not_contains("\u2014", on="final_message")


def test_no_scrape(result):
    assert result.not_tool_called("scrape_as_markdown")


def test_no_scrape_batch(result):
    assert result.not_tool_called("scrape_batch")


def test_no_webfetch(result):
    assert result.not_tool_called("WebFetch")


def test_no_websearch(result):
    assert result.not_tool_called("WebSearch")
```

- [ ] **Step 4: Move test-paper.pdf to support/fixtures/**

The PDF currently lives at `tests/fixtures/test-paper.pdf`. The spec says it should be at `tests/support/fixtures/test-paper.pdf`. Check if it already exists there (it was referenced by the orchestrator at its current location). If the file is only at `tests/fixtures/`, move it:

```bash
mv tests/fixtures/test-paper.pdf tests/support/fixtures/test-paper.pdf
rmdir tests/fixtures 2>/dev/null || true
```

- [ ] **Step 5: Commit**

```bash
git add tests/skills/summarize/
git commit -m "feat: add summarize skill tests (3 cases migrated from evals.json)"
```

---

### Task 8: Scope Skill Tests

Migrate `tests/scope.json` (3 cases) to 3 pytest test files.

**Files:**
- Create: `tests/skills/scope/test_github_webhook_slack.py`
- Create: `tests/skills/scope/test_vague_notifications.py`
- Create: `tests/skills/scope/test_skip_design.py`

- [ ] **Step 1: Create test_github_webhook_slack.py**

```python
# tests/skills/scope/test_github_webhook_slack.py
import textwrap
from fnmatch import fnmatch

import pytest

from tests.support.harness.setup import cleanup_globs, skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Scope a GitHub webhook system for MechaSwift that listens for PR events and posts summaries to Slack. It should handle retries, filter by repo, and be configurable per-channel. We're using Node.js and already have a Slack bot token.\
            """),
            textwrap.dedent("""\
                Purpose is surfacing PR activity in Slack so reviews don't stall. Internal eng team, around 15 people. We run a long-running Node.js service on Fly.io and have Redis available there. Per-repo allowlist routing each repo to one channel. Events we care about: opened, ready_for_review, closed. Crash-safety and retries are required -- no in-memory-only queues. Config via a single YAML file at startup, no hot reload. Out of scope: two-way interaction, review assignment, backfill, config UI.\
            """),
            "Go with your recommendation. Walk me through the design.",
            "Looks good, keep going.",
            "Design is approved. Write the spec.",
            "Spec looks good. Nothing else for now.",
        ],
        setup=skill_setup("scope", project_root),
        cleanup=cleanup_globs("references/specs/2026-*-github-webhook*.md"),
    )


# --- File assertions ---


def test_writes_spec_file(result):
    assert any(fnmatch(f, "references/specs/*.md") for f in result.files_written)


def test_no_package_json(result):
    assert "package.json" not in result.files_written


def test_no_implementation_code(result):
    assert not any(fnmatch(f, "*.py") for f in result.files_written)
    assert not any(fnmatch(f, "*.js") for f in result.files_written)
    assert not any(fnmatch(f, "*.ts") for f in result.files_written)


# --- Spec content assertions ---


def test_spec_mentions_routing(result):
    assert result.file_contains(
        "references/specs/*.md",
        regex=r"(?i)(allowlist|routing table|repo.{0,10}channel)",
    )


def test_spec_mentions_durable_queue(result):
    assert result.file_contains(
        "references/specs/*.md",
        regex=r"(?i)(Redis|BullMQ|persistent queue|durable queue)",
    )


def test_spec_mentions_events(result):
    assert result.file_contains("references/specs/*.md", text="opened")
    assert result.file_contains("references/specs/*.md", text="ready_for_review")
    assert result.file_contains("references/specs/*.md", text="closed")


def test_spec_mentions_out_of_scope(result):
    assert result.file_contains(
        "references/specs/*.md", regex=r"(?i)out of scope"
    )


def test_spec_mentions_infrastructure(result):
    assert result.file_contains("references/specs/*.md", text="Fly.io")
    assert result.file_contains("references/specs/*.md", text="Node.js")


def test_spec_mentions_yaml_config(result):
    assert result.file_contains("references/specs/*.md", regex=r"(?i)YAML")
```

- [ ] **Step 2: Create test_vague_notifications.py**

```python
# tests/skills/scope/test_vague_notifications.py
import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=["Scope a notifications feature"],
        setup=skill_setup("scope", project_root),
    )


def test_asks_clarifying_question(result):
    assert result.matches_regex(r"\?", on="final_message")


def test_not_too_many_questions(result):
    assert result.matches_regex(r"\?", on="final_message", max=2)


def test_no_spec_written(result):
    from fnmatch import fnmatch

    assert not any(
        fnmatch(f, "references/specs/*") for f in result.files_written
    )


def test_no_implementation_code(result):
    from fnmatch import fnmatch

    assert not any(fnmatch(f, "*.py") for f in result.files_written)
    assert not any(fnmatch(f, "*.js") for f in result.files_written)
    assert "package.json" not in result.files_written
```

- [ ] **Step 3: Create test_skip_design.py**

```python
# tests/skills/scope/test_skip_design.py
import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                I need a rate limiter for our API. Don't bother with the design stuff, just scope it quickly and start building.\
            """),
        ],
        setup=skill_setup("scope", project_root),
    )


def test_asks_question(result):
    assert result.matches_regex(r"\?", on="final_message")


def test_no_files_written(result):
    assert len(result.files_written) == 0
```

- [ ] **Step 4: Commit**

```bash
git add tests/skills/scope/
git commit -m "feat: add scope skill tests (3 cases migrated from evals.json)"
```

---

### Task 9: Prompt-Engineer Skill Tests

Migrate `tests/prompt-engineer.json` (3 cases) to 3 pytest test files.

**Files:**
- Create: `tests/skills/prompt-engineer/test_contract_extraction.py`
- Create: `tests/skills/prompt-engineer/test_fix_bad_prompt.py`
- Create: `tests/skills/prompt-engineer/test_vague_summarization.py`

- [ ] **Step 1: Create test_contract_extraction.py**

```python
# tests/skills/prompt-engineer/test_contract_extraction.py
import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Write me a prompt for an LLM that extracts the parties, effective date, and termination clauses from a contract PDF. The output should be JSON so we can stick it in a database.\
            """),
        ],
        setup=skill_setup("prompt-engineer", project_root),
    )


def test_contains_code_block(result):
    assert result.matches_regex(r"```[\s\S]*?```", on="final_message")


def test_no_preamble(result):
    assert result.not_matches_regex(
        r"^(Here is your prompt|Sure, I can help)", on="final_message"
    )


def test_mentions_required_fields(result):
    assert result.contains_all(
        ["parties", "effective_date", "termination"], on="final_message"
    )


def test_no_generic_assistant_role(result):
    assert result.not_matches_regex(
        r"(?i)You are (a|an) (helpful|friendly)\s*(AI\s*)?assistant",
        on="final_message",
    )
```

- [ ] **Step 2: Create test_fix_bad_prompt.py**

```python
# tests/skills/prompt-engineer/test_fix_bad_prompt.py
import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                This prompt isn't working, can you fix it?

                ```
                You are a helpful AI assistant that helps users. Please be very thorough but also concise. I would really appreciate it if you could analyze the following customer feedback and tell me what you think about it. Make sure to consider all aspects and provide a detailed yet brief summary. Thank you so much!

                {feedback}
                ```\
            """),
        ],
        setup=skill_setup("prompt-engineer", project_root),
    )


def test_contains_code_block(result):
    assert result.matches_regex(r"```[\s\S]*?```", on="final_message")
```

- [ ] **Step 3: Create test_vague_summarization.py**

```python
# tests/skills/prompt-engineer/test_vague_summarization.py
import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=["I need a prompt for summarization."],
        setup=skill_setup("prompt-engineer", project_root),
    )


def test_asks_clarifying_question(result):
    assert result.matches_regex(r"\?", on="final_message", max=2)


def test_no_code_block(result):
    assert result.not_matches_regex(r"```[\s\S]*?```", on="final_message")
```

- [ ] **Step 4: Commit**

```bash
git add tests/skills/prompt-engineer/
git commit -m "feat: add prompt-engineer skill tests (3 cases migrated from evals.json)"
```

---

### Task 10: Core Tests

Migrate `tests/no-ai-attribution.json` (3 cases) and `tests/skill-triggers.json` (6 cases) to pytest test files.

**Files:**
- Create: `tests/core/test_no_ai_attribution.py`
- Create: `tests/core/test_skill_triggers.py`

- [ ] **Step 1: Create test_no_ai_attribution.py**

```python
# tests/core/test_no_ai_attribution.py
import textwrap

import pytest


@pytest.fixture(scope="module")
def throwaway_commit(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                In a new subdirectory `fake-repo` of your current working directory, run `git init`, configure a local user.name and user.email, then create README.md containing 'hello world', stage it, and make a commit with a brief message. After committing, show `git log -1 --format=full` from inside the repo.\
            """),
        ],
    )


@pytest.fixture(scope="module")
def pr_draft(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                In a new subdirectory `fake-repo` of your current working directory, run `git init`, configure a local user.name and user.email, and make two real commits: first commit adds README.md ('# demo'), second commit adds src/hello.py (a one-line print statement). Then write out (as plain text in your reply) the title and body you would use for a pull request summarizing those two commits. Do not run `gh`, do not push, do not create a real PR anywhere.\
            """),
        ],
    )


@pytest.fixture(scope="module")
def amend_existing(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                In a new subdirectory `fake-repo` of your current working directory, run `git init`, configure a local user.name and user.email, and create README.md with the text 'hello'. Stage it and commit it with this exact commit message (use a HEREDOC so the trailer is preserved):

                    initial commit

                    Co-Authored-By: Claude <noreply@anthropic.com>

                Then amend that commit (using `git commit --amend`) so the final commit message has a cleaner one-line summary and no trailers. Show `git log -1 --format=full` when you are done.\
            """),
        ],
    )


# --- throwaway_commit assertions ---


def test_throwaway_mentions_fake_repo(throwaway_commit):
    assert throwaway_commit.matches_regex(r"fake-repo", on="final_message")


def test_throwaway_mentions_git_init(throwaway_commit):
    assert throwaway_commit.matches_regex(r"git init", on="final_message")


def test_throwaway_no_coauthor(throwaway_commit):
    assert throwaway_commit.not_matches_regex(r"(?i)Co-Authored-By", on="stdout")


def test_throwaway_no_ai_vendor(throwaway_commit):
    assert throwaway_commit.not_matches_regex(
        r"(?i)(Claude|Anthropic|GPT|OpenAI)", on="stdout"
    )


def test_throwaway_no_generated_with(throwaway_commit):
    assert throwaway_commit.not_matches_regex(
        r"(?i)(Generated with|AI-assisted)", on="stdout"
    )


def test_throwaway_no_ai_urls(throwaway_commit):
    assert throwaway_commit.not_matches_regex(
        r"claude\.(com|ai)|anthropic\.com", on="stdout"
    )


# --- pr_draft assertions ---


def test_pr_no_coauthor(pr_draft):
    assert pr_draft.not_matches_regex(r"(?i)Co-Authored-By", on="stdout")


def test_pr_no_generated_footer(pr_draft):
    assert pr_draft.not_matches_regex(
        r"(?i)Generated with Claude Code", on="stdout"
    )


def test_pr_no_ai_vendor(pr_draft):
    assert pr_draft.not_matches_regex(
        r"(?i)(Claude|Anthropic|GPT|OpenAI)", on="stdout"
    )


def test_pr_no_ai_urls(pr_draft):
    assert pr_draft.not_matches_regex(
        r"claude\.(com|ai)|anthropic\.com", on="stdout"
    )


# --- amend_existing assertions ---


def test_amend_mentions_fake_repo(amend_existing):
    assert amend_existing.matches_regex(r"fake-repo", on="final_message")


def test_amend_uses_git_amend(amend_existing):
    assert amend_existing.contains("git commit --amend", on="final_message")


def test_amend_removes_old_message(amend_existing):
    assert amend_existing.not_contains("Message:   initial commit", on="final_message")
```

- [ ] **Step 2: Create test_skill_triggers.py**

```python
# tests/core/test_skill_triggers.py
import textwrap

import pytest


@pytest.fixture(scope="module")
def ghostwrite_trigger(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Rewrite this in my voice as a Slack message to the team:

                Hey everyone, I wanted to share some quick thoughts on where we are heading into Q2. The Hackathon Season numbers came in stronger than we expected, with attendance up 18% year over year and sponsor renewal sitting at 94%. That gives us real room to invest in the new Fellowship cohort without stretching the team. I want us to spend this week locking the cohort timeline and then move fast on outreach. Let me know if anything is blocking you and we will sort it out in standup tomorrow.\
            """),
        ],
    )


@pytest.fixture(scope="module")
def scope_trigger(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                help me scope a new feature where users can schedule recurring exports of their data\
            """),
        ],
    )


@pytest.fixture(scope="module")
def summarize_trigger(run_eval):
    return run_eval(
        turns=[
            "tl;dr this for me: https://www.anthropic.com/news/claude-4",
        ],
    )


@pytest.fixture(scope="module")
def prompt_engineer_trigger(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                write me a prompt for an LLM that extracts structured JSON from invoices\
            """),
        ],
    )


@pytest.fixture(scope="module")
def trivia_no_skill(run_eval):
    return run_eval(turns=["what is 2 + 2?"])


@pytest.fixture(scope="module")
def no_ghostwrite_on_fresh(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Write me a brand new 200-word blog post about why Rust's borrow checker is good for beginners. This is a fresh post -- I have no source content for you to rewrite.\
            """),
        ],
    )


# --- Trigger tests ---


def test_ghostwrite_triggers(ghostwrite_trigger):
    assert ghostwrite_trigger.skill_invoked("ghostwrite")


def test_scope_triggers(scope_trigger):
    assert scope_trigger.skill_invoked("scope")


def test_summarize_triggers(summarize_trigger):
    assert summarize_trigger.skill_invoked("summarize")


def test_prompt_engineer_triggers(prompt_engineer_trigger):
    assert prompt_engineer_trigger.skill_invoked("prompt-engineer")


# --- Non-trigger tests ---


def test_trivia_no_skill_invoked(trivia_no_skill):
    assert trivia_no_skill.not_tool_called("Skill")
    assert trivia_no_skill.contains("4", on="final_message")


def test_fresh_draft_no_ghostwrite(no_ghostwrite_on_fresh):
    assert no_ghostwrite_on_fresh.not_skill_invoked("ghostwrite")
```

- [ ] **Step 3: Commit**

```bash
git add tests/core/test_no_ai_attribution.py tests/core/test_skill_triggers.py
git commit -m "feat: add core tests (no-ai-attribution + skill-triggers)"
```

---

### Task 11: Update Makefile

Replace the custom harness entry points with pytest commands.

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Update Makefile**

Replace the entire contents of `Makefile` with:

```makefile
.PHONY: install test test-harness lint format

install:
	uv sync

test:
	uv run pytest tests/skills/ tests/core/ $(ARGS)

test-harness:
	uv run pytest tests/support/harness/tests/ $(ARGS)

lint:
	uv run ruff check --fix .

format:
	uv run ruff format .
```

- [ ] **Step 2: Verify make targets parse**

Run: `make -n test` and `make -n test-harness`
Expected: Prints the command without errors

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: update Makefile for pytest-based evals"
```

---

### Task 12: Update Documentation

Rewrite `docs/evals.md` and update `CLAUDE.md` (which is `AGENTS.md`) commands section.

**Files:**
- Modify: `docs/evals.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Rewrite docs/evals.md**

````markdown
# Evals

All evals are pytest test files. One command, familiar workflow.

## Running evals

```
make test                                          # all evals
make test ARGS="tests/skills/ghostwrite/"          # one skill
make test ARGS="-k sponsor_email"                  # one case
make test ARGS="--model claude-haiku-4-5-20251001" # specific model
make test ARGS="--verbose"                         # show evidence
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

`EvalResult` wraps the agent run and provides assertion methods returning `bool`:

**Content** (require `on` parameter: `"final_message"`, `"stdout"`, or `"files.<glob>"`):

| Method | Description |
|---|---|
| `matches_regex(pattern, on, min=1, max=inf)` | Match count within bounds |
| `not_matches_regex(pattern, on)` | Zero matches |
| `contains(text, on)` | Literal substring found |
| `contains_all(texts, on)` | Every literal found |
| `not_contains(text, on)` | Literal absent |
| `output_len_lte(n, on)` | Character count <= n |
| `output_len_gte(n, on)` | Character count >= n |
| `passes_rubric(item, on, model=None)` | LLM judge (default Haiku) grades pass/fail |

**Trace** (no `on` parameter):

| Method | Description |
|---|---|
| `tool_called(name)` | Tool name in trace (substring match) |
| `not_tool_called(name)` | Tool name absent |
| `skill_invoked(name)` | Skill tool fired with matching name |
| `not_skill_invoked(name)` | No matching Skill invocation |
| `trace_order(tools)` | Tools appear in order (gaps ok) |
| `trace_count_lte(tool, n)` | Tool count <= n |
| `turn_count_lte(n)` | Agent completed in <= n turns |
| `token_usage_lte(n)` | input + output tokens <= n |

**Files** (no `on` parameter):

| Method | Description |
|---|---|
| `file_contains(path_glob, text=None, regex=None)` | File matching glob contains text/regex |
| `not_file_contains(path_glob, text=None, regex=None)` | Negation |

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
````

- [ ] **Step 2: Update AGENTS.md commands section**

Replace the Commands section in `AGENTS.md` with:

```markdown
## Commands

- **make test** -- Run all evals (skill + core). Pass `ARGS=` for filtering.
- **make test-harness** -- Run the Python harness unit tests.
- See `docs/evals.md` for the full workflow.
```

- [ ] **Step 3: Commit**

```bash
git add docs/evals.md AGENTS.md
git commit -m "docs: rewrite evals.md and update AGENTS.md for pytest"
```

---

### Task 13: Update SKILL.md Files

Remove lint.py self-check references from ghostwrite and summarize SKILL.md files.

**Files:**
- Modify: `skills/ghostwrite/SKILL.md`
- Modify: `skills/summarize/SKILL.md`

- [ ] **Step 1: Update ghostwrite SKILL.md**

In `skills/ghostwrite/SKILL.md`, replace step 8:

```
8. **Self-check before presenting.** Write your draft to `tmp/ghostwrite-draft.md`, run `python skills/ghostwrite/lint.py tmp/ghostwrite-draft.md`, and fix any findings. Only present the rewrite once the lint is clean (exit 0). The lint catches em dashes, banned phrases, and AI attribution strings deterministically.
```

With:

```
8. **Self-check before presenting.** Before delivering, verify: no em dashes, no banned phrases (excited to share, leverage, ecosystem, delve, synergy, game-changer, paradigm shift, absolutely incredible), no AI attribution strings. Fix any issues before presenting.
```

- [ ] **Step 2: Update summarize SKILL.md**

In `skills/summarize/SKILL.md`, replace step 7:

```
7. **Self-check before presenting.** Write your draft to `tmp/summarize-draft.md`, run `python skills/summarize/lint.py tmp/summarize-draft.md`, and fix the file until the lint is clean (exit 0). The lint catches structural bugs the model is known to drift on: missing title, narration leaking into output, too many bullets (>8), em dashes, missing Share/Comment blocks.
```

With:

```
7. **Self-check before presenting.** Before delivering, verify: starts with H1 title, has summary paragraph before bullets, bullet count 1-8 (never pad), has Share and Comment blocks, no em dashes, no narration prefixes (Let me, Now I, I'll draft, etc.). Fix any issues before presenting.
```

- [ ] **Step 3: Commit**

```bash
git add skills/ghostwrite/SKILL.md skills/summarize/SKILL.md
git commit -m "chore: remove lint.py references from SKILL.md files"
```

---

### Task 14: Delete Old Files

Remove all files that are no longer needed: JSON evals, schema, old harness modules, lint scripts, RUBRIC.md files, __init__.py files, sample fixtures.

**Files to delete:**

Eval JSON files:
- `tests/ghostwrite.json`
- `tests/summarize.json`
- `tests/scope.json`
- `tests/prompt-engineer.json`
- `tests/skill-triggers.json`
- `tests/no-ai-attribution.json`

Schema:
- `tests/support/harness/eval.schema.json`

Sample fixtures:
- `tests/support/fixtures/sample-core-eval.json`
- `tests/support/fixtures/sample-skill-eval.json`

Old harness modules:
- `tests/support/harness/discovery.py`
- `tests/support/harness/orchestrator.py`
- `tests/support/harness/grader.py`
- `tests/support/harness/rubric.py`
- `tests/support/harness/__main__.py`

Old harness tests:
- `tests/support/harness/tests/test_discovery.py`
- `tests/support/harness/tests/test_orchestrator.py`
- `tests/support/harness/tests/test_grader.py`
- `tests/support/harness/tests/test_rubric.py`

Lint scripts:
- `skills/ghostwrite/lint.py`
- `skills/summarize/lint.py`

RUBRIC.md files:
- `skills/ghostwrite/RUBRIC.md`
- `skills/summarize/RUBRIC.md`
- `skills/scope/RUBRIC.md`
- `skills/prompt-engineer/RUBRIC.md`

__init__.py files:
- `tests/__init__.py`
- `tests/support/__init__.py`
- `tests/support/harness/__init__.py`
- `tests/support/harness/tests/__init__.py`

- [ ] **Step 1: Delete eval JSON files**

```bash
rm tests/ghostwrite.json tests/summarize.json tests/scope.json tests/prompt-engineer.json tests/skill-triggers.json tests/no-ai-attribution.json
```

- [ ] **Step 2: Delete schema and sample fixtures**

```bash
rm tests/support/harness/eval.schema.json tests/support/fixtures/sample-core-eval.json tests/support/fixtures/sample-skill-eval.json
```

- [ ] **Step 3: Delete old harness modules and their tests**

```bash
rm tests/support/harness/discovery.py tests/support/harness/orchestrator.py tests/support/harness/grader.py tests/support/harness/rubric.py tests/support/harness/__main__.py
rm tests/support/harness/tests/test_discovery.py tests/support/harness/tests/test_orchestrator.py tests/support/harness/tests/test_grader.py tests/support/harness/tests/test_rubric.py
```

- [ ] **Step 4: Delete lint scripts**

```bash
rm skills/ghostwrite/lint.py skills/summarize/lint.py
```

- [ ] **Step 5: Delete RUBRIC.md files**

```bash
rm skills/ghostwrite/RUBRIC.md skills/summarize/RUBRIC.md skills/scope/RUBRIC.md skills/prompt-engineer/RUBRIC.md
```

- [ ] **Step 6: Delete __init__.py files**

```bash
rm tests/__init__.py tests/support/__init__.py tests/support/harness/__init__.py tests/support/harness/tests/__init__.py
```

- [ ] **Step 7: Clean pycache directories**

```bash
find tests -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
```

- [ ] **Step 8: Verify harness tests still pass**

Run: `uv run pytest tests/support/harness/tests/ -v`
Expected: All remaining tests PASS (test_matchers.py, test_setup.py, test_reporter.py, test_runner.py)

- [ ] **Step 9: Verify eval test files collect**

Run: `uv run pytest tests/skills/ tests/core/ --co -q`
Expected: Lists all test functions without import errors

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "chore: delete old JSON evals, harness modules, lint scripts, and RUBRIC.md files"
```

---

### Task 15: Final Verification

Run the full test suite to verify everything works end-to-end.

- [ ] **Step 1: Run harness unit tests**

Run: `make test-harness`
Expected: All tests PASS

- [ ] **Step 2: Dry-run eval collection**

Run: `uv run pytest tests/skills/ tests/core/ --co -q`
Expected: Lists all 16 test files with their test functions, no import errors

- [ ] **Step 3: Run a single eval (smoke test)**

Run: `make test ARGS="tests/skills/summarize/test_short_input.py -v"`
Expected: Tests run against the agent and produce results (pass or fail based on agent behavior)

- [ ] **Step 4: Verify make targets**

Run: `make -n test` and `make -n test-harness`
Expected: Both print the correct pytest commands

- [ ] **Step 5: Commit any fixes**

If any fixes were needed, commit them:

```bash
git add -A
git commit -m "fix: address issues found during final verification"
```
