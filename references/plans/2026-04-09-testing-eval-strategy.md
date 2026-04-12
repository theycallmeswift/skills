# Testing & Eval Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pytest-based eval suite for the ghostwrite skill that verifies rule compliance and content preservation, using deterministic assertions and an LLM judge.

**Architecture:** Three layers — a generic `ClaudeRunner` harness that shells out to `claude -p`, a library of deterministic + LLM-judge assertion helpers, and pytest test cases organized per skill. Tests run in parallel by default via `pytest-xdist`.

**Tech Stack:** Python 3.11+, pytest, pytest-xdist, uv

---

## File Structure

```
tests/
├── conftest.py                              # Session-scoped runner fixture
├── support/
│   ├── __init__.py
│   ├── harness/
│   │   ├── __init__.py
│   │   └── claude_runner.py                 # ClaudeRunner class
│   └── assertions/
│       ├── __init__.py
│       ├── deterministic.py                 # Pure-Python assertion helpers
│       └── judge.py                         # LLM judge assertion
└── skills/
    └── ghostwrite/
        ├── conftest.py                      # Ghostwrite fixtures (source content per medium)
        ├── test_ghostwrite_rules.py         # General compliance + content preservation (~6 tests)
        └── test_ghostwrite_mediums.py       # Medium-specific formatting (~10 tests)
```

Also modified:
- `pyproject.toml` — add pytest + pytest-xdist deps, pytest config
- `Makefile` — add `test` target
- `docs/evals.md` — testing guide

---

## Task 1: Project Config — pytest + xdist + Makefile

**Files:**
- Modify: `pyproject.toml`
- Modify: `Makefile`

- [ ] **Step 1: Write a smoke test file to prove pytest works**

Create `tests/test_smoke.py`:

```python
def test_smoke():
    assert 1 + 1 == 2
```

- [ ] **Step 2: Add pytest and pytest-xdist to dev dependencies in pyproject.toml**

In `pyproject.toml`, change the `[dependency-groups]` section:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-xdist>=3.5",
    "ruff>=0.15.9",
]
```

Add pytest configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["slow: tests that make multiple LLM calls"]
addopts = "-n auto"
```

`-n auto` makes parallel execution the default via pytest-xdist. Every `pytest` invocation runs workers equal to CPU count unless overridden with `-n0` (serial).

- [ ] **Step 3: Add test target to Makefile**

Add to `Makefile`:

```makefile
.PHONY: install lint format test

test:
	uv run pytest tests/ -v
```

Update the `.PHONY` line to include `test`.

- [ ] **Step 4: Install deps and run smoke test**

Run:
```bash
uv sync && uv run pytest tests/test_smoke.py -v
```

Expected: `1 passed`

- [ ] **Step 5: Verify parallel execution works**

Run:
```bash
uv run pytest tests/test_smoke.py -v -n auto
```

Expected: `1 passed` with `[gw0]` worker prefix in output.

- [ ] **Step 6: Delete smoke test and commit**

Remove `tests/test_smoke.py`.

```bash
git add pyproject.toml Makefile
git commit -m "feat: add pytest + pytest-xdist config and test Makefile target"
```

---

## Task 2: ClaudeRunner Harness

**Files:**
- Create: `tests/support/__init__.py`
- Create: `tests/support/harness/__init__.py`
- Create: `tests/support/harness/claude_runner.py`

- [ ] **Step 1: Write the failing test**

Create `tests/support/harness/test_claude_runner.py`:

```python
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from tests.support.harness.claude_runner import ClaudeRunner


class TestClaudeRunnerInit:
    def test_default_model_is_haiku(self):
        runner = ClaudeRunner()
        assert runner.model == "haiku"

    def test_default_timeout_is_30(self):
        runner = ClaudeRunner()
        assert runner.timeout == 30

    def test_custom_model(self):
        runner = ClaudeRunner(model="sonnet")
        assert runner.model == "sonnet"

    def test_custom_timeout(self):
        runner = ClaudeRunner(timeout=60)
        assert runner.timeout == 60

    def test_run_id_is_8_hex_chars(self):
        runner = ClaudeRunner()
        assert len(runner.run_id) == 8
        int(runner.run_id, 16)  # raises if not hex

    def test_default_cwd_under_tmp(self):
        runner = ClaudeRunner()
        assert "tmp/tests" in str(runner.cwd)
        assert runner.run_id in str(runner.cwd)

    def test_cwd_from_env(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_CWD": "/tmp/custom"}):
            runner = ClaudeRunner()
            assert runner.cwd == Path("/tmp/custom")

    def test_explicit_cwd_overrides_env(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_CWD": "/tmp/custom"}):
            runner = ClaudeRunner(cwd="/tmp/explicit")
            assert runner.cwd == Path("/tmp/explicit")

    def test_env_overrides_for_model_and_timeout(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_MODEL": "sonnet", "CLAUDE_TEST_TIMEOUT": "60"}):
            runner = ClaudeRunner()
            assert runner.model == "sonnet"
            assert runner.timeout == 60

    def test_explicit_kwargs_override_env(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_MODEL": "sonnet", "CLAUDE_TEST_TIMEOUT": "60"}):
            runner = ClaudeRunner(model="haiku", timeout=10)
            assert runner.model == "haiku"
            assert runner.timeout == 10


class TestClaudeRunnerRun:
    def test_run_calls_subprocess_with_correct_args(self):
        runner = ClaudeRunner(model="haiku", timeout=30)
        mock_result = MagicMock()
        mock_result.stdout = "  hello world  "

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = runner.run("test prompt")

            mock_run.assert_called_once()
            args = mock_run.call_args
            cmd = args[0][0]
            assert cmd == [
                "claude", "-p", "test prompt",
                "--model", "haiku",
                "--output-format", "text",
            ]
            assert args[1]["timeout"] == 30
            assert args[1]["capture_output"] is True
            assert args[1]["text"] is True
            assert result == "hello world"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/support/harness/test_claude_runner.py -v -n0
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tests.support'`

- [ ] **Step 3: Create package files and implement ClaudeRunner**

Create `tests/support/__init__.py` (empty file).

Create `tests/support/harness/__init__.py`:

```python
from tests.support.harness.claude_runner import ClaudeRunner

__all__ = ["ClaudeRunner"]
```

Create `tests/support/harness/claude_runner.py`:

```python
"""Generic Claude Code test runner. Invokes `claude -p` as a subprocess."""

import os
import subprocess
import uuid
from pathlib import Path


class ClaudeRunner:
    """Runs prompts through Claude CLI and returns text output.

    Config hierarchy: explicit kwargs > env vars > defaults.

    Env vars:
        CLAUDE_TEST_MODEL: model name (default: haiku)
        CLAUDE_TEST_TIMEOUT: seconds (default: 30)
        CLAUDE_TEST_CWD: working directory for subprocess
    """

    def __init__(
        self,
        model: str | None = None,
        timeout: int | None = None,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ):
        self.model = model or os.environ.get("CLAUDE_TEST_MODEL", "haiku")
        self.timeout = timeout or int(os.environ.get("CLAUDE_TEST_TIMEOUT", "30"))
        self.run_id = uuid.uuid4().hex[:8]
        self.cwd = self._resolve_cwd(cwd)
        self.cwd.mkdir(parents=True, exist_ok=True)
        self.env = {**os.environ, **(env or {})}

    def _resolve_cwd(self, explicit: str | Path | None) -> Path:
        if explicit:
            return Path(explicit)
        if env_cwd := os.environ.get("CLAUDE_TEST_CWD"):
            return Path(env_cwd)
        project_root = Path(__file__).parents[3]
        return project_root / "tmp" / "tests" / self.run_id

    def run(self, prompt: str) -> str:
        """Run a prompt through `claude -p` and return stripped stdout.

        Args:
            prompt: The text prompt to send.

        Returns:
            The CLI's stdout, stripped of leading/trailing whitespace.
        """
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", self.model, "--output-format", "text"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=self.cwd,
            env=self.env,
        )
        return result.stdout.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/support/harness/test_claude_runner.py -v -n0
```

Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/support/__init__.py tests/support/harness/__init__.py tests/support/harness/claude_runner.py tests/support/harness/test_claude_runner.py
git commit -m "feat: add ClaudeRunner test harness"
```

---

## Task 3: Session-Scoped Runner Fixture

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_conftest.py`:

```python
def test_runner_fixture_exists(runner):
    from tests.support.harness.claude_runner import ClaudeRunner

    assert isinstance(runner, ClaudeRunner)


def test_runner_default_model_is_haiku(runner):
    assert runner.model == "haiku"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/test_conftest.py -v -n0
```

Expected: FAIL — `fixture 'runner' not found`

- [ ] **Step 3: Create conftest.py with runner fixture**

Create `tests/conftest.py`:

```python
import os

import pytest

from tests.support.harness import ClaudeRunner


@pytest.fixture(scope="session")
def runner():
    """Session-scoped ClaudeRunner. Shared across all tests — each run() is a fresh subprocess."""
    return ClaudeRunner(
        model=os.environ.get("CLAUDE_TEST_MODEL", "haiku"),
        timeout=int(os.environ.get("CLAUDE_TEST_TIMEOUT", "30")),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/test_conftest.py -v -n0
```

Expected: `2 passed`

- [ ] **Step 5: Delete test file and commit**

Remove `tests/test_conftest.py`.

```bash
git add tests/conftest.py
git commit -m "feat: add session-scoped runner fixture"
```

---

## Task 4: Deterministic Assertions

**Files:**
- Create: `tests/support/assertions/__init__.py`
- Create: `tests/support/assertions/deterministic.py`
- Test: `tests/support/assertions/test_deterministic.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/support/assertions/test_deterministic.py`:

```python
from textwrap import dedent

from tests.support.assertions.deterministic import (
    banned_words,
    email_signoff,
    linkedin_hashtag_count,
    long_sentences,
    no_em_dashes,
    slack_word_count,
    stats_preserved,
    urls_preserved,
)


class TestNoEmDashes:
    def test_clean_text(self):
        assert no_em_dashes("Hello, world.") == []

    def test_catches_em_dash(self):
        result = no_em_dashes("Hello — world.")
        assert len(result) == 1
        assert "—" in result[0]

    def test_multiple_lines(self):
        text = dedent("""\
            Line one is fine.
            Line two has — an em dash.
            Line three is fine.
            Line four — also bad.""")
        result = no_em_dashes(text)
        assert len(result) == 2


class TestLongSentences:
    def test_short_sentence(self):
        assert long_sentences("This is short.") == []

    def test_long_sentence(self):
        text = "This is a sentence that has way too many words in it and keeps going on and on and on and on."
        result = long_sentences(text, max_words=25)
        assert len(result) == 1

    def test_custom_max_words(self):
        text = "One two three four five six."
        assert long_sentences(text, max_words=5) == [text.strip()]
        assert long_sentences(text, max_words=10) == []


class TestBannedWords:
    def test_clean_text(self):
        assert banned_words("We built something cool.") == []

    def test_catches_synergy(self):
        result = banned_words("Great synergy between teams.")
        assert "synergy" in result

    def test_catches_delve(self):
        result = banned_words("Let's delve into this topic.")
        assert "delve" in result

    def test_catches_excited_to_share(self):
        result = banned_words("I'm excited to share this news.")
        assert "excited to share" in result

    def test_catches_game_changer(self):
        result = banned_words("This is a real game-changer for us.")
        assert "game-changer" in result

    def test_catches_paradigm_shift(self):
        result = banned_words("A paradigm shift in education.")
        assert "paradigm shift" in result

    def test_case_insensitive(self):
        result = banned_words("SYNERGY is key.")
        assert "synergy" in result


class TestUrlsPreserved:
    def test_all_present(self):
        source = "Check https://mlh.io and https://dev.to for details."
        output = "Visit https://mlh.io and https://dev.to."
        assert urls_preserved(source, output) == []

    def test_missing_url(self):
        source = "Check https://mlh.io and https://dev.to for details."
        output = "Visit https://mlh.io."
        result = urls_preserved(source, output)
        assert "https://dev.to" in result

    def test_no_urls_in_source(self):
        assert urls_preserved("No links here.", "No links here either.") == []


class TestStatsPreserved:
    def test_all_present(self):
        source = "We reached 500,000 developers and 1 in 3 CS students."
        output = "500,000 developers and 1 in 3 CS students joined."
        assert stats_preserved(source, output) == []

    def test_missing_stat(self):
        source = "We reached 500,000 developers and 1 in 3 CS students."
        output = "Many developers and 1 in 3 CS students joined."
        result = stats_preserved(source, output)
        assert "500,000" in result


class TestEmailSignoff:
    def test_dash_swift(self):
        assert email_signoff("Some content.\n\n- Swift") is True

    def test_happy_hacking(self):
        assert email_signoff("Some content.\n\nHappy Hacking,\nSwift") is True

    def test_missing_signoff(self):
        assert email_signoff("Some content.\n\nBest,\nMike") is False

    def test_trailing_whitespace(self):
        assert email_signoff("Some content.\n\n- Swift  \n") is True


class TestSlackWordCount:
    def test_counts_words(self):
        assert slack_word_count("Hello world, this is a test.") == 6

    def test_empty_string(self):
        assert slack_word_count("") == 0


class TestLinkedinHashtagCount:
    def test_counts_hashtags(self):
        assert linkedin_hashtag_count("#MLH #AI #Hackathon #LearnByDoing") == 4

    def test_no_hashtags(self):
        assert linkedin_hashtag_count("No hashtags here.") == 0

    def test_inline_hashtags(self):
        assert linkedin_hashtag_count("Check out #MLH and #DEV today.") == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/support/assertions/test_deterministic.py -v -n auto
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement deterministic assertions**

Create `tests/support/assertions/__init__.py`:

```python
from tests.support.assertions.deterministic import (
    banned_words,
    email_signoff,
    linkedin_hashtag_count,
    long_sentences,
    no_em_dashes,
    slack_word_count,
    stats_preserved,
    urls_preserved,
)

__all__ = [
    "banned_words",
    "email_signoff",
    "linkedin_hashtag_count",
    "long_sentences",
    "no_em_dashes",
    "slack_word_count",
    "stats_preserved",
    "urls_preserved",
]
```

Create `tests/support/assertions/deterministic.py`:

```python
"""Deterministic assertion helpers for skill output validation.

Each function returns a list of violations (empty = pass) or a scalar value.
"""

import re


BANNED_PHRASES = [
    "synergy",
    "leverage",  # as verb — caught by substring
    "ecosystem",
    "paradigm shift",
    "game-changer",
    "delve",
    "excited to share",
]


def no_em_dashes(text: str) -> list[str]:
    """Return lines containing em dashes. Empty list = pass."""
    return [line for line in text.splitlines() if "\u2014" in line]


def long_sentences(text: str, max_words: int = 25) -> list[str]:
    """Return sentences exceeding max_words. Empty list = pass."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.split()) > max_words]


def banned_words(text: str) -> list[str]:
    """Return banned words/phrases found in text. Empty list = pass."""
    lower = text.lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in lower]


def urls_preserved(source: str, output: str) -> list[str]:
    """Return URLs from source missing in output. Empty list = pass."""
    url_pattern = re.compile(r'https?://[^\s)\]>,]+')
    source_urls = set(url_pattern.findall(source))
    output_text = output
    return [url for url in source_urls if url not in output_text]


def stats_preserved(source: str, output: str) -> list[str]:
    """Return numbers/stats from source missing in output. Empty list = pass."""
    stat_pattern = re.compile(r'\d[\d,]*(?:\.\d+)?')
    source_stats = set(stat_pattern.findall(source))
    return [stat for stat in source_stats if stat not in output]


def email_signoff(text: str) -> bool:
    """Check text ends with '- Swift' or 'Happy Hacking,\\nSwift'."""
    stripped = text.rstrip()
    return stripped.endswith("- Swift") or stripped.endswith("Happy Hacking,\nSwift")


def slack_word_count(text: str) -> int:
    """Return total word count."""
    return len(text.split())


def linkedin_hashtag_count(text: str) -> int:
    """Return count of hashtags (#word patterns)."""
    return len(re.findall(r'#\w+', text))
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/support/assertions/test_deterministic.py -v -n auto
```

Expected: all 22 tests PASS, running across multiple workers.

- [ ] **Step 5: Commit**

```bash
git add tests/support/assertions/__init__.py tests/support/assertions/deterministic.py tests/support/assertions/test_deterministic.py
git commit -m "feat: add deterministic assertion helpers with tests"
```

---

## Task 5: LLM Judge

**Files:**
- Create: `tests/support/assertions/judge.py`
- Test: `tests/support/assertions/test_judge.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/support/assertions/test_judge.py`:

```python
import json
from unittest.mock import MagicMock

from tests.support.assertions.judge import JudgeResult, judge


class TestJudgeResult:
    def test_passed_when_all_checks_true(self):
        result = JudgeResult(
            passed=True,
            checks={"clarity": True, "tone": True},
            reasoning={"clarity": "Clear writing", "tone": "Good tone"},
        )
        assert result.passed is True

    def test_failed_when_any_check_false(self):
        result = JudgeResult(
            passed=False,
            checks={"clarity": True, "tone": False},
            reasoning={"clarity": "Clear", "tone": "Too formal"},
        )
        assert result.passed is False


class TestJudge:
    def test_passes_when_all_criteria_met(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = json.dumps({
            "checks": {"main_point_first": True},
            "reasoning": {"main_point_first": "Opens with the key ask"},
        })

        result = judge(
            source="Please review my PR",
            output="Can you review PR #42? It adds the new auth flow.",
            rubric="Opening sentence contains the main point/ask",
            runner=mock_runner,
        )

        assert result.passed is True
        assert result.checks["main_point_first"] is True
        mock_runner.run.assert_called_once()

    def test_fails_when_criteria_not_met(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = json.dumps({
            "checks": {"main_point_first": False},
            "reasoning": {"main_point_first": "Starts with context, not the ask"},
        })

        result = judge(
            source="Please review my PR",
            output="I've been working on auth. Can you review PR #42?",
            rubric="Opening sentence contains the main point/ask",
            runner=mock_runner,
        )

        assert result.passed is False
        assert result.checks["main_point_first"] is False

    def test_prompt_includes_source_output_and_rubric(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = json.dumps({
            "checks": {"test": True},
            "reasoning": {"test": "ok"},
        })

        judge(
            source="my source",
            output="my output",
            rubric="my rubric",
            runner=mock_runner,
        )

        prompt = mock_runner.run.call_args[0][0]
        assert "my source" in prompt
        assert "my output" in prompt
        assert "my rubric" in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/support/assertions/test_judge.py -v -n0
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the LLM judge**

Create `tests/support/assertions/judge.py`:

```python
"""LLM-based judge for semantic assertion checks.

Sends a structured rubric prompt through ClaudeRunner and parses JSON result.
"""

import json
from dataclasses import dataclass
from textwrap import dedent


@dataclass
class JudgeResult:
    """Result from an LLM judge evaluation.

    Attributes:
        passed: True if all checks passed.
        checks: Mapping of criterion name to pass/fail.
        reasoning: Mapping of criterion name to explanation.
    """

    passed: bool
    checks: dict[str, bool]
    reasoning: dict[str, str]


def judge(source: str, output: str, rubric: str, runner) -> JudgeResult:
    """Send a structured rubric prompt through the harness, parse JSON result.

    Args:
        source: The original source content.
        output: The rewritten output to evaluate.
        rubric: Natural-language criteria to judge against.
        runner: A ClaudeRunner instance.

    Returns:
        JudgeResult with pass/fail per criterion and reasoning.
    """
    prompt = dedent(f"""\
        You are a writing quality judge. Evaluate whether the OUTPUT meets the criteria.

        SOURCE (original content):
        {source}

        OUTPUT (rewritten content):
        {output}

        RUBRIC (criteria to evaluate):
        {rubric}

        Respond with ONLY a JSON object, no markdown fences, no explanation outside the JSON:
        {{
            "checks": {{"criterion_name": true/false}},
            "reasoning": {{"criterion_name": "brief explanation"}}
        }}

        Use short, descriptive criterion names derived from the rubric (e.g., "main_point_first").
        Be strict: only pass if the criterion is clearly met.""")

    raw = runner.run(prompt)

    # Strip markdown fences if the model wraps the JSON
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("\n", 1)[0]
    cleaned = cleaned.strip()

    data = json.loads(cleaned)
    checks = data["checks"]
    reasoning = data["reasoning"]

    return JudgeResult(
        passed=all(checks.values()),
        checks=checks,
        reasoning=reasoning,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/support/assertions/test_judge.py -v -n0
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Update assertions __init__.py and commit**

Update `tests/support/assertions/__init__.py` to also export judge:

```python
from tests.support.assertions.deterministic import (
    banned_words,
    email_signoff,
    linkedin_hashtag_count,
    long_sentences,
    no_em_dashes,
    slack_word_count,
    stats_preserved,
    urls_preserved,
)
from tests.support.assertions.judge import JudgeResult, judge

__all__ = [
    "JudgeResult",
    "banned_words",
    "email_signoff",
    "judge",
    "linkedin_hashtag_count",
    "long_sentences",
    "no_em_dashes",
    "slack_word_count",
    "stats_preserved",
    "urls_preserved",
]
```

```bash
git add tests/support/assertions/judge.py tests/support/assertions/test_judge.py tests/support/assertions/__init__.py
git commit -m "feat: add LLM judge assertion helper"
```

---

## Task 6: Ghostwrite Fixtures

**Files:**
- Create: `tests/skills/__init__.py`
- Create: `tests/skills/ghostwrite/__init__.py`
- Create: `tests/skills/ghostwrite/conftest.py`

- [ ] **Step 1: Write the failing test**

Create `tests/skills/ghostwrite/test_fixtures.py`:

```python
def test_email_source_fixture(email_source):
    assert len(email_source) > 50
    assert "https://" in email_source  # has a URL to preserve


def test_email_prompt_fixture(email_prompt):
    assert "email" in email_prompt.lower()


def test_linkedin_source_fixture(linkedin_source):
    assert len(linkedin_source) > 50


def test_linkedin_prompt_fixture(linkedin_prompt):
    assert "linkedin" in linkedin_prompt.lower()


def test_slack_source_fixture(slack_source):
    assert len(slack_source) > 20


def test_slack_prompt_fixture(slack_prompt):
    assert "slack" in slack_prompt.lower()


def test_blog_source_fixture(blog_source):
    assert len(blog_source) > 100


def test_blog_prompt_fixture(blog_prompt):
    assert "blog" in blog_prompt.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/skills/ghostwrite/test_fixtures.py -v -n0
```

Expected: FAIL — `fixture 'email_source' not found`

- [ ] **Step 3: Create package files and ghostwrite fixtures**

Create `tests/skills/__init__.py` (empty file).

Create `tests/skills/ghostwrite/__init__.py` (empty file).

Create `tests/skills/ghostwrite/conftest.py`:

```python
from textwrap import dedent

import pytest


# --- Source content per medium ---


@pytest.fixture(scope="session")
def email_source():
    return dedent("""\
        Hey team, wanted to give a quick update on the hackathon season.
        We've now supported 500,000 developers across 1,500 events this year.
        The new platform features are driving 30% more signups compared to last quarter.
        Check out the dashboard at https://mlh.io/dashboard for the full breakdown.
        Also, Sarah from DevRel mentioned that the sponsor satisfaction scores
        are the highest they've ever been, which is great news for renewals.
        Let me know if you have any questions about the numbers.
        Best regards,
        Mike""")


@pytest.fixture(scope="session")
def linkedin_source():
    return dedent("""\
        I wanted to share some exciting news about what we've been building at MLH.
        This year we reached an incredible milestone of supporting 500,000 developers
        through 1,500 hackathons across 65 countries. Our community now includes
        1 in 3 computer science students globally. We've also launched a new
        fellowship program that has placed 200 early-career developers at companies
        like GitHub, Meta, and Shopify. The feedback from both fellows and companies
        has been overwhelmingly positive, with a 95% satisfaction rate.
        I'm so grateful to our team and community for making this possible.
        None of this happens without the organizers, mentors, and sponsors who
        believe in learning by doing. Here's to the next million developers.""")


@pytest.fixture(scope="session")
def slack_source():
    return dedent("""\
        Hey everyone, I wanted to give a heads up that we're planning to migrate
        the event platform to the new infrastructure next Tuesday. This should
        improve load times by about 40% based on our staging tests. If your team
        has any critical events running that week, please flag them in #ops so
        we can coordinate timing. Thanks!""")


@pytest.fixture(scope="session")
def blog_source():
    return dedent("""\
        The landscape of developer education is changing rapidly. Traditional
        computer science programs are struggling to keep pace with industry demands,
        and students are increasingly turning to hands-on learning experiences to
        build the skills employers actually want. At MLH, we've seen this firsthand
        through our hackathon community, which now reaches 1 in 3 CS students globally.

        Over the past year, we've supported 500,000 developers across 1,500 events
        in 65 countries. But the numbers only tell part of the story. What really
        matters is the transformation we see in participants. Students who attend
        their first hackathon often describe it as a turning point, the moment they
        went from studying code to shipping products.

        Our fellowship program has been another proof point. We've placed 200
        early-career developers at companies like GitHub, Meta, and Shopify, with
        a 95% satisfaction rate from both fellows and host companies. The common
        thread? Learning by doing beats learning by reading every time.

        If you're a student wondering whether to attend a hackathon, or an employer
        considering hands-on hiring, the data speaks for itself. Check out
        https://mlh.io/impact for the full report.""")


# --- Prompts per medium ---


@pytest.fixture(scope="session")
def email_prompt(email_source):
    return f"Rewrite this as an email in my voice:\n\n{email_source}"


@pytest.fixture(scope="session")
def linkedin_prompt(linkedin_source):
    return f"Rewrite this as a LinkedIn post:\n\n{linkedin_source}"


@pytest.fixture(scope="session")
def slack_prompt(slack_source):
    return f"Rewrite this as a Slack message:\n\n{slack_source}"


@pytest.fixture(scope="session")
def blog_prompt(blog_source):
    return f"Rewrite this as a blog post for DEV:\n\n{blog_source}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/skills/ghostwrite/test_fixtures.py -v -n0
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Delete fixture test file and commit**

Remove `tests/skills/ghostwrite/test_fixtures.py`.

```bash
git add tests/skills/__init__.py tests/skills/ghostwrite/__init__.py tests/skills/ghostwrite/conftest.py
git commit -m "feat: add ghostwrite test fixtures with source content per medium"
```

---

## Task 7: Ghostwrite Rules Tests (test_ghostwrite_rules.py)

**Files:**
- Create: `tests/skills/ghostwrite/test_ghostwrite_rules.py`

These tests make real `claude -p` calls. Each test invokes the ghostwrite skill once and runs deterministic assertions on the output. They run in parallel via xdist.

- [ ] **Step 1: Write the failing tests**

Create `tests/skills/ghostwrite/test_ghostwrite_rules.py`:

```python
from tests.support.assertions import (
    banned_words,
    long_sentences,
    no_em_dashes,
    stats_preserved,
    urls_preserved,
)


class TestGhostwriteRules:
    """General rule compliance tests. Each test rewrites email source and checks one rule."""

    def test_no_em_dashes(self, runner, email_prompt):
        output = runner.run(email_prompt)
        violations = no_em_dashes(output)
        assert violations == [], f"Em dashes found in lines: {violations}"

    def test_sentences_under_25_words(self, runner, email_prompt):
        output = runner.run(email_prompt)
        violations = long_sentences(output)
        assert violations == [], f"Sentences over 25 words: {violations}"

    def test_no_banned_words(self, runner, email_prompt):
        output = runner.run(email_prompt)
        violations = banned_words(output)
        assert violations == [], f"Banned words found: {violations}"

    def test_no_ai_tells(self, runner, linkedin_prompt):
        output = runner.run(linkedin_prompt)
        violations = banned_words(output)
        assert violations == [], f"AI tells found: {violations}"

    def test_urls_preserved(self, runner, email_prompt, email_source):
        output = runner.run(email_prompt)
        missing = urls_preserved(email_source, output)
        assert missing == [], f"URLs missing from output: {missing}"

    def test_stats_preserved(self, runner, email_prompt, email_source):
        output = runner.run(email_prompt)
        missing = stats_preserved(email_source, output)
        assert missing == [], f"Stats missing from output: {missing}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run pytest tests/skills/ghostwrite/test_ghostwrite_rules.py -v -n0 --timeout=120
```

Expected: Tests either FAIL (skill not producing compliant output) or PASS if the skill is working well. The point is to verify the test infrastructure works end-to-end with real CLI calls. If tests fail due to timeout or CLI errors, debug the harness.

- [ ] **Step 3: Verify parallel execution**

Run:
```bash
uv run pytest tests/skills/ghostwrite/test_ghostwrite_rules.py -v -n auto
```

Expected: Tests run across multiple workers (look for `[gw0]`, `[gw1]`, etc. prefixes). All 6 tests should execute.

- [ ] **Step 4: Commit**

```bash
git add tests/skills/ghostwrite/test_ghostwrite_rules.py
git commit -m "feat: add ghostwrite rule compliance tests"
```

---

## Task 8: Ghostwrite Mediums Tests (test_ghostwrite_mediums.py)

**Files:**
- Create: `tests/skills/ghostwrite/test_ghostwrite_mediums.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/skills/ghostwrite/test_ghostwrite_mediums.py`:

```python
import re

from tests.support.assertions import (
    email_signoff,
    judge,
    linkedin_hashtag_count,
    slack_word_count,
)


class TestEmailMedium:
    def test_email_has_valid_signoff(self, runner, email_prompt):
        output = runner.run(email_prompt)
        assert email_signoff(output), (
            f"Email missing valid sign-off ('- Swift' or 'Happy Hacking,\\nSwift'). "
            f"Ending: ...{output[-100:]}"
        )

    def test_email_greeting_format(self, runner, email_prompt):
        output = runner.run(email_prompt)
        assert re.search(r"Hey,\s+\w+\s+--", output), (
            f"Email missing 'Hey, [Name] --' greeting. First line: {output.splitlines()[0]}"
        )

    def test_email_opens_with_point(self, runner, email_prompt, email_source):
        output = runner.run(email_prompt)
        result = judge(
            source=email_source,
            output=output,
            rubric="The first sentence after the greeting contains the main point, update, or ask. Not a pleasantry or context-setting preamble.",
            runner=runner,
        )
        assert result.passed, f"Email doesn't open with the point: {result.reasoning}"


class TestLinkedinMedium:
    def test_linkedin_word_count(self, runner, linkedin_prompt):
        output = runner.run(linkedin_prompt)
        words = len(output.split())
        assert 100 <= words <= 200, f"LinkedIn post is {words} words (expected 100-200)"

    def test_linkedin_hashtag_count(self, runner, linkedin_prompt):
        output = runner.run(linkedin_prompt)
        count = linkedin_hashtag_count(output)
        assert 4 <= count <= 7, f"LinkedIn post has {count} hashtags (expected 4-7)"

    def test_linkedin_hooks_first(self, runner, linkedin_prompt, linkedin_source):
        output = runner.run(linkedin_prompt)
        result = judge(
            source=linkedin_source,
            output=output,
            rubric="The opening line is a hook that challenges, quotes, or directly addresses the reader. It does NOT start with 'I'm excited to share' or 'I recently' or similar preamble.",
            runner=runner,
        )
        assert result.passed, f"LinkedIn doesn't hook first: {result.reasoning}"


class TestSlackMedium:
    def test_slack_under_60_words(self, runner, slack_prompt):
        output = runner.run(slack_prompt)
        count = slack_word_count(output)
        assert count <= 60, f"Slack message is {count} words (max 60)"

    def test_slack_is_chat_prose(self, runner, slack_prompt):
        output = runner.run(slack_prompt)
        bullet_lines = [
            line for line in output.splitlines()
            if re.match(r'^\s*[-*]\s', line) or re.match(r'^\s*\d+\.\s', line)
        ]
        bold_matches = re.findall(r'\*\*[^*]+\*\*', output)
        header_lines = [line for line in output.splitlines() if re.match(r'^#+\s', line)]
        violations = bullet_lines + bold_matches + header_lines
        assert violations == [], (
            f"Slack should be plain chat prose, no bullets/bold/headers: {violations}"
        )

    def test_slack_ask_first(self, runner, slack_prompt, slack_source):
        output = runner.run(slack_prompt)
        result = judge(
            source=slack_source,
            output=output,
            rubric="The first sentence contains the request or ask. Context and explanation come after, not before.",
            runner=runner,
        )
        assert result.passed, f"Slack doesn't put ask first: {result.reasoning}"


class TestBlogMedium:
    def test_blog_has_section_headers(self, runner, blog_prompt):
        output = runner.run(blog_prompt)
        headers = [line for line in output.splitlines() if re.match(r'^#{1,3}\s', line)]
        assert len(headers) >= 2, (
            f"Blog post should have section headers (## or ###). Found {len(headers)}"
        )
```

- [ ] **Step 2: Run tests to verify they execute**

Run:
```bash
uv run pytest tests/skills/ghostwrite/test_ghostwrite_mediums.py -v -n auto
```

Expected: 10 tests execute across workers. Some may fail depending on model output quality — that's expected and validates the assertions are working.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/ghostwrite/test_ghostwrite_mediums.py
git commit -m "feat: add ghostwrite medium-specific formatting tests"
```

---

## Task 9: Documentation — docs/evals.md

**Files:**
- Create: `docs/evals.md`

- [ ] **Step 1: Write docs/evals.md**

Create `docs/evals.md`:

```markdown
# Testing & Evals

## Quick Start

```bash
make test
```

Runs the full pytest suite with parallel execution (pytest-xdist). Target runtime: under 2 minutes with haiku.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_TEST_MODEL` | `haiku` | Model to use for test runs |
| `CLAUDE_TEST_TIMEOUT` | `30` | Timeout in seconds per CLI call |
| `CLAUDE_TEST_CWD` | `tmp/tests/<run_id>` | Working directory for subprocess |

## Test Structure

```
tests/
├── conftest.py                        # Session-scoped runner fixture
├── support/
│   ├── harness/claude_runner.py       # ClaudeRunner — invokes `claude -p`
│   └── assertions/
│       ├── deterministic.py           # Pure-Python checks (regex, string matching)
│       └── judge.py                   # LLM judge for semantic checks
└── skills/
    └── ghostwrite/
        ├── conftest.py                # Source content fixtures per medium
        ├── test_ghostwrite_rules.py   # Rule compliance (~6 tests)
        └── test_ghostwrite_mediums.py # Medium formatting (~10 tests)
```

## Writing a New Test

1. Add a test function in the appropriate `test_*.py` file
2. Use the `runner` fixture to call Claude: `output = runner.run("your prompt")`
3. Assert with deterministic helpers or the LLM judge

```python
def test_my_rule(self, runner, email_prompt, email_source):
    output = runner.run(email_prompt)
    violations = no_em_dashes(output)
    assert violations == [], f"Em dashes found: {violations}"
```

## Adding a Deterministic Assertion

Add a function to `tests/support/assertions/deterministic.py`:

```python
def my_check(text: str) -> list[str]:
    """Return violations. Empty list = pass."""
    return [line for line in text.splitlines() if some_condition(line)]
```

Export it from `tests/support/assertions/__init__.py`.

## Using the LLM Judge

For semantic checks that regex can't handle:

```python
from tests.support.assertions import judge

result = judge(
    source=original_text,
    output=rewritten_text,
    rubric="The opening sentence contains the main point or ask.",
    runner=runner,
)
assert result.passed, f"Failed: {result.reasoning}"
```

Judge tests make an additional LLM call, so use sparingly.

## Adding Tests for a New Skill

1. Create `tests/skills/<skill_name>/conftest.py` with source content fixtures
2. Create `tests/skills/<skill_name>/test_<skill_name>_*.py` with test cases
3. Tests automatically pick up the shared `runner` fixture from `tests/conftest.py`

## Running Options

```bash
# Full suite, parallel (default)
make test

# Serial execution (debugging)
uv run pytest tests/ -v -n0

# Single test file
uv run pytest tests/skills/ghostwrite/test_ghostwrite_rules.py -v

# Single test
uv run pytest tests/skills/ghostwrite/test_ghostwrite_rules.py::TestGhostwriteRules::test_no_em_dashes -v

# With different model
CLAUDE_TEST_MODEL=sonnet make test
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/evals.md
git commit -m "docs: add testing and evals guide"
```

---

## Task 10: Full Suite Verification

- [ ] **Step 1: Run the full suite with make test**

Run:
```bash
make test
```

Expected: ~16 tests execute in parallel. Deterministic assertion unit tests (Tasks 2, 4, 5) should all pass. Integration tests (Tasks 7, 8) depend on model output quality.

- [ ] **Step 2: Run lint to confirm code quality**

Run:
```bash
make lint && make format
```

Expected: No errors, no formatting changes (or auto-fixed).

- [ ] **Step 3: Fix any lint issues and commit**

If lint or format made changes:

```bash
git add -u
git commit -m "style: fix lint and formatting"
```

- [ ] **Step 4: Final commit — verify clean state**

Run:
```bash
git status
```

Expected: clean working tree, all changes committed.
