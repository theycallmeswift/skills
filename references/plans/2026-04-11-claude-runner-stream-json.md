# ClaudeRunner stream-json Migration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Switch ClaudeRunner from `--output-format text` to `--output-format stream-json --verbose` so test runs capture the full conversation trace (tool calls, cost, tokens) via a `RunResult` dataclass.

**Architecture:** Add `RunResult` frozen dataclass and `_parse_stream()` parser to `claude_runner.py`. Update `run()` to pass `--output-format stream-json --verbose` and return `RunResult` instead of `str`. Update all test assertions to access `.text` for the final output string.

**Tech Stack:** Python 3.12, dataclasses, pytest, subprocess

**Spec:** `references/specs/2026-04-11-claude-runner-stream-json.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `tests/support/harness/claude_runner.py` | Modify | Add `RunResult` dataclass, `_parse_stream()`, update `run()` |
| `tests/support/harness/__init__.py` | Modify | Export `RunResult` |
| `tests/support/harness/test_claude_runner.py` | Modify | Update mock tests, add `RunResult` + `_parse_stream` unit tests |
| `tests/skills/ghostwrite/test_ghostwrite_rules.py` | Modify | Add `.text` to all assertion arguments |
| `tests/skills/ghostwrite/test_ghostwrite_mediums.py` | Modify | Add `.text` to all assertion arguments |
| `tests/skills/summarize/test_summarize_structure.py` | Modify | Add `.text` to all assertion arguments |
| `tests/skills/summarize/test_summarize_input_types.py` | Modify | Add `.text` to all assertion arguments |

No new files. No fixture or conftest changes (fixtures return `runner.run()` which changes from `str` to `RunResult` — call sites stay the same).

---

### Task 1: RunResult dataclass + _parse_stream — tests

**Files:**
- Test: `tests/support/harness/test_claude_runner.py`

- [ ] **Step 1: Write failing tests for `_parse_stream` and `RunResult` properties**

Add these test classes to `tests/support/harness/test_claude_runner.py`. The imports and test data constants go at the top of the file (after existing imports).

```python
import json
from textwrap import dedent

# Add to existing imports at top:
from tests.support.harness.claude_runner import ClaudeRunner, RunResult, _parse_stream

# ---- Synthetic NDJSON fixtures ----

SIMPLE_STREAM = "\n".join([
    json.dumps({"type": "system", "subtype": "init", "session_id": "s1"}),
    json.dumps({
        "type": "assistant",
        "message": {
            "id": "msg_01",
            "role": "assistant",
            "content": [{"type": "text", "text": "hello world"}],
            "stop_reason": "end_turn",
        },
        "session_id": "s1",
    }),
    json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 1000,
        "num_turns": 1,
        "result": "hello world",
        "stop_reason": "end_turn",
        "total_cost_usd": 0.01,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 20,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
        },
    }),
])

TOOL_USE_STREAM = "\n".join([
    json.dumps({"type": "system", "subtype": "init", "session_id": "s1"}),
    json.dumps({
        "type": "assistant",
        "message": {
            "id": "msg_01",
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "toolu_01", "name": "Read", "input": {"file_path": "/tmp/test.txt"}}],
            "stop_reason": None,
        },
        "session_id": "s1",
    }),
    json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"tool_use_id": "toolu_01", "type": "tool_result", "content": "file contents here"}],
        },
        "tool_use_result": {"type": "text", "file": {"filePath": "/tmp/test.txt", "content": "file contents here", "numLines": 1}},
        "session_id": "s1",
    }),
    json.dumps({
        "type": "assistant",
        "message": {
            "id": "msg_02",
            "role": "assistant",
            "content": [{"type": "text", "text": "The file says hello"}],
            "stop_reason": "end_turn",
        },
        "session_id": "s1",
    }),
    json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 2000,
        "num_turns": 2,
        "result": "The file says hello",
        "stop_reason": "end_turn",
        "total_cost_usd": 0.02,
        "usage": {
            "input_tokens": 30,
            "output_tokens": 40,
            "cache_read_input_tokens": 100,
            "cache_creation_input_tokens": 0,
        },
    }),
])

MULTI_BLOCK_STREAM = "\n".join([
    json.dumps({"type": "system", "subtype": "init", "session_id": "s1"}),
    json.dumps({
        "type": "assistant",
        "message": {
            "id": "msg_01",
            "role": "assistant",
            "content": [{"type": "thinking", "thinking": "let me think..."}],
            "stop_reason": None,
        },
        "session_id": "s1",
    }),
    json.dumps({
        "type": "assistant",
        "message": {
            "id": "msg_01",
            "role": "assistant",
            "content": [{"type": "tool_use", "id": "toolu_01", "name": "Skill", "input": {"skill": "summarize"}}],
            "stop_reason": None,
        },
        "session_id": "s1",
    }),
    json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"tool_use_id": "toolu_01", "type": "tool_result", "content": "skill loaded"}],
        },
        "tool_use_result": {"type": "text"},
        "session_id": "s1",
    }),
    json.dumps({
        "type": "assistant",
        "message": {
            "id": "msg_02",
            "role": "assistant",
            "content": [{"type": "text", "text": "Here is the summary"}],
            "stop_reason": "end_turn",
        },
        "session_id": "s1",
    }),
    json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 3000,
        "num_turns": 2,
        "result": "Here is the summary",
        "stop_reason": "end_turn",
        "total_cost_usd": 0.05,
        "usage": {
            "input_tokens": 50,
            "output_tokens": 60,
            "cache_read_input_tokens": 200,
            "cache_creation_input_tokens": 100,
        },
    }),
])


class TestParseStream:
    def test_simple_text_response(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert isinstance(result, RunResult)
        assert result.cost_usd == 0.01
        assert result.duration_ms == 1000
        assert result.num_turns == 1
        assert result.stop_reason == "end_turn"
        assert result.usage["input_tokens"] == 10
        assert result.usage["output_tokens"] == 20

    def test_excludes_system_and_result_events(self):
        result = _parse_stream(SIMPLE_STREAM)
        types = [e["type"] for e in result.events]
        assert "system" not in types
        assert "result" not in types

    def test_keeps_assistant_and_user_events(self):
        result = _parse_stream(TOOL_USE_STREAM)
        types = [e["type"] for e in result.events]
        assert types == ["assistant", "user", "assistant"]

    def test_events_is_tuple(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert isinstance(result.events, tuple)

    def test_skips_blank_lines(self):
        stream_with_blanks = "\n\n" + SIMPLE_STREAM + "\n\n"
        result = _parse_stream(stream_with_blanks)
        assert result.text == "hello world"


class TestRunResultText:
    def test_simple_text(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert result.text == "hello world"

    def test_text_after_tool_use(self):
        result = _parse_stream(TOOL_USE_STREAM)
        assert result.text == "The file says hello"

    def test_text_from_multi_block(self):
        result = _parse_stream(MULTI_BLOCK_STREAM)
        assert result.text == "Here is the summary"


class TestRunResultMessages:
    def test_messages_filters_to_assistant_and_user(self):
        result = _parse_stream(TOOL_USE_STREAM)
        types = [m["type"] for m in result.messages]
        assert types == ["assistant", "user", "assistant"]

    def test_simple_has_one_message(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert len(result.messages) == 1
        assert result.messages[0]["type"] == "assistant"


class TestRunResultToolCalls:
    def test_no_tool_calls_in_simple(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert result.tool_calls == []

    def test_extracts_tool_call(self):
        result = _parse_stream(TOOL_USE_STREAM)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "Read"
        assert result.tool_calls[0]["input"] == {"file_path": "/tmp/test.txt"}

    def test_multiple_tool_calls(self):
        result = _parse_stream(MULTI_BLOCK_STREAM)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "Skill"


class TestRunResultToolResults:
    def test_no_tool_results_in_simple(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert result.tool_results == []

    def test_extracts_tool_result(self):
        result = _parse_stream(TOOL_USE_STREAM)
        assert len(result.tool_results) == 1
        assert result.tool_results[0]["tool_use_id"] == "toolu_01"
        assert result.tool_results[0]["content"] == "file contents here"
        assert result.tool_results[0]["structured"]["type"] == "text"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/support/harness/test_claude_runner.py::TestParseStream -v 2>&1 | head -20`
Expected: `ImportError` — `_parse_stream` and `RunResult` don't exist yet.

---

### Task 2: RunResult dataclass + _parse_stream — implementation

**Files:**
- Modify: `tests/support/harness/claude_runner.py`

- [ ] **Step 1: Add RunResult and _parse_stream to claude_runner.py**

Add `import dataclasses` and `import json` to the imports at the top of the file. Then add `RunResult` and `_parse_stream` after the imports, before the `ClaudeRunner` class:

```python
import dataclasses
import json


@dataclasses.dataclass(frozen=True)
class RunResult:
    """Parsed result from a stream-json Claude CLI invocation."""

    events: tuple[dict, ...]
    cost_usd: float
    duration_ms: int
    num_turns: int
    usage: dict
    stop_reason: str

    @property
    def text(self) -> str:
        """Final assistant message text."""
        for event in reversed(self.events):
            if event.get("type") != "assistant":
                continue
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    return block["text"]
        return ""

    @property
    def messages(self) -> list[dict]:
        """All assistant and user events, in order."""
        return [e for e in self.events if e.get("type") in ("assistant", "user")]

    @property
    def tool_calls(self) -> list[dict]:
        """All tool_use blocks across all assistant events, in order."""
        calls = []
        for event in self.events:
            if event.get("type") != "assistant":
                continue
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    calls.append({"name": block["name"], "input": block["input"]})
        return calls

    @property
    def tool_results(self) -> list[dict]:
        """All tool result events, in order."""
        results = []
        for event in self.events:
            if event.get("type") != "user":
                continue
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_result":
                    results.append({
                        "tool_use_id": block.get("tool_use_id"),
                        "content": block.get("content", ""),
                        "structured": event.get("tool_use_result"),
                    })
        return results


def _parse_stream(raw: str) -> RunResult:
    """Parse NDJSON stream-json output into a RunResult."""
    events = []
    metadata = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        event_type = parsed.get("type")
        if event_type in ("assistant", "user"):
            events.append(parsed)
        elif event_type == "result":
            metadata = parsed

    return RunResult(
        events=tuple(events),
        cost_usd=metadata.get("total_cost_usd", 0.0),
        duration_ms=metadata.get("duration_ms", 0),
        num_turns=metadata.get("num_turns", 0),
        usage=metadata.get("usage", {}),
        stop_reason=metadata.get("stop_reason", ""),
    )
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/support/harness/test_claude_runner.py::TestParseStream tests/support/harness/test_claude_runner.py::TestRunResultText tests/support/harness/test_claude_runner.py::TestRunResultMessages tests/support/harness/test_claude_runner.py::TestRunResultToolCalls tests/support/harness/test_claude_runner.py::TestRunResultToolResults -v`
Expected: All 16 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/support/harness/claude_runner.py tests/support/harness/test_claude_runner.py
git commit -m "Add RunResult dataclass and _parse_stream with tests"
```

---

### Task 3: Update ClaudeRunner.run() + mock tests

**Files:**
- Modify: `tests/support/harness/claude_runner.py:52-84`
- Modify: `tests/support/harness/test_claude_runner.py:75-112` (TestClaudeRunnerRun)

- [ ] **Step 1: Update the mock test to expect stream-json behavior**

Replace the entire `TestClaudeRunnerRun` class in `test_claude_runner.py` with:

```python
class TestClaudeRunnerRun:
    def test_run_calls_subprocess_with_stream_json(self):
        runner = ClaudeRunner(model="haiku", timeout=30)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = SIMPLE_STREAM

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = runner.run("test prompt")

            mock_run.assert_called_once()
            args = mock_run.call_args
            cmd = args[0][0]
            assert "claude" == cmd[0]
            assert "-p" == cmd[1]
            assert "test prompt" == cmd[2]
            assert "--model" in cmd
            assert "--output-format" in cmd
            assert "stream-json" in cmd
            assert "--verbose" in cmd
            assert "--plugin-dir" in cmd
            assert "--dangerously-skip-permissions" in cmd
            assert args[1]["timeout"] == 30
            assert args[1]["capture_output"] is True
            assert args[1]["text"] is True

    def test_run_returns_run_result(self):
        runner = ClaudeRunner(model="haiku", timeout=30)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = SIMPLE_STREAM

        with patch("subprocess.run", return_value=mock_result):
            result = runner.run("test prompt")
            assert isinstance(result, RunResult)
            assert result.text == "hello world"
            assert result.cost_usd == 0.01

    def test_run_raises_on_nonzero_exit(self):
        runner = ClaudeRunner(model="haiku", timeout=30)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "something went wrong"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="exited with code 1"):
                runner.run("bad prompt")
```

- [ ] **Step 2: Run updated mock tests to see them fail (run() still returns str)**

Run: `pytest tests/support/harness/test_claude_runner.py::TestClaudeRunnerRun -v`
Expected: `test_run_returns_run_result` FAILS (returns `str`, not `RunResult`). `test_run_calls_subprocess_with_stream_json` FAILS ("stream-json" not in cmd).

- [ ] **Step 3: Update ClaudeRunner.run() to use stream-json**

Replace the `run` method in `claude_runner.py` (lines 52-84) with:

```python
    def run(self, prompt: str) -> RunResult:
        """Run a prompt through `claude -p` and return parsed stream-json result.

        Args:
            prompt: The text prompt to send.

        Returns:
            A RunResult with the full conversation trace and metadata.
        """
        result = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--model",
                self.model,
                "--output-format",
                "stream-json",
                "--verbose",
                "--plugin-dir",
                str(self.plugin_dir),
                "--dangerously-skip-permissions",
            ],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=self.cwd,
            env=self.env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"claude -p exited with code {result.returncode}\nstderr: {result.stderr.strip()}"
            )
        return _parse_stream(result.stdout)
```

- [ ] **Step 4: Run mock tests to verify they pass**

Run: `pytest tests/support/harness/test_claude_runner.py -v`
Expected: All tests PASS (init tests + run tests + parse/result tests).

- [ ] **Step 5: Commit**

```bash
git add tests/support/harness/claude_runner.py tests/support/harness/test_claude_runner.py
git commit -m "Switch ClaudeRunner.run() to stream-json output format"
```

---

### Task 4: Update ghostwrite test assertions

**Files:**
- Modify: `tests/skills/ghostwrite/test_ghostwrite_rules.py`
- Modify: `tests/skills/ghostwrite/test_ghostwrite_mediums.py`

Fixtures `email_output`, `linkedin_output`, `slack_output`, `blog_output` now return `RunResult` instead of `str`. Every place these are used as strings needs `.text`. The `*_source` fixtures are still plain strings — no changes.

- [ ] **Step 1: Update test_ghostwrite_rules.py**

6 changes — every helper call that receives an `*_output` fixture gets `.text`:

```python
class TestGhostwriteRules:
    """General rule compliance tests. Each test uses cached output from a single CLI call."""

    def test_no_em_dashes(self, email_output):
        violations = no_em_dashes(email_output.text)
        assert violations == [], f"Em dashes found in lines: {violations}"

    def test_sentences_under_25_words(self, email_output):
        violations = long_sentences(email_output.text)
        assert violations == [], f"Sentences over 25 words: {violations}"

    def test_no_banned_words(self, email_output):
        violations = banned_words(email_output.text)
        assert violations == [], f"Banned words found: {violations}"

    def test_no_ai_tells(self, linkedin_output):
        violations = banned_words(linkedin_output.text)
        assert violations == [], f"AI tells found: {violations}"

    def test_urls_preserved(self, email_output, email_source):
        missing = urls_preserved(email_source, email_output.text)
        assert missing == [], f"URLs missing from output: {missing}"

    def test_stats_preserved(self, email_output, email_source):
        missing = stats_preserved(email_source, email_output.text)
        assert missing == [], f"Stats missing from output: {missing}"
```

- [ ] **Step 2: Update test_ghostwrite_mediums.py**

12 changes across 4 test classes. Every `*_output` used as string gets `.text`:

```python
class TestEmailMedium:
    def test_email_has_valid_signoff(self, email_output):
        assert email_signoff(email_output.text), (
            f"Email missing valid sign-off ('- Swift' or 'Happy Hacking,\\nSwift'). "
            f"Ending: ...{email_output.text[-100:]}"
        )

    def test_email_greeting_format(self, email_output):
        assert re.search(r"Hey,\s+\w+\s+--", email_output.text), (
            f"Email missing 'Hey, [Name] --' greeting. First line: {email_output.text.splitlines()[0]}"
        )

    def test_email_opens_with_point(self, runner, email_output, email_source):
        result = judge(
            source=email_source,
            output=email_output.text,
            rubric="The first sentence after the greeting contains the main point, update, or ask. Not a pleasantry or context-setting preamble.",
            runner=runner,
        )
        assert result.passed, f"Email doesn't open with the point: {result.reasoning}"


class TestLinkedinMedium:
    def test_linkedin_word_count(self, linkedin_output):
        words = len(linkedin_output.text.split())
        assert words <= 200, f"LinkedIn post is {words} words (expected under 200)"

    def test_linkedin_hashtag_count(self, linkedin_output):
        count = linkedin_hashtag_count(linkedin_output.text)
        assert 4 <= count <= 7, f"LinkedIn post has {count} hashtags (expected 4-7)"

    def test_linkedin_hooks_first(self, runner, linkedin_output, linkedin_source):
        result = judge(
            source=linkedin_source,
            output=linkedin_output.text,
            rubric="The opening line is a hook that challenges, quotes, or directly addresses the reader. It does NOT start with 'I'm excited to share' or 'I recently' or similar preamble.",
            runner=runner,
        )
        assert result.passed, f"LinkedIn doesn't hook first: {result.reasoning}"


class TestSlackMedium:
    def test_slack_under_60_words(self, slack_output):
        count = len(slack_output.text.split())
        assert count <= 60, f"Slack message is {count} words (max 60)"

    def test_slack_no_markdown_headers(self, slack_output):
        header_lines = [line for line in slack_output.text.splitlines() if re.match(r"^#+\s", line)]
        assert header_lines == [], (
            f"Slack doesn't support markdown headers: {header_lines}"
        )

    def test_slack_ask_first(self, runner, slack_output, slack_source):
        result = judge(
            source=slack_source,
            output=slack_output.text,
            rubric="The main point or ask appears in the first 1-2 sentences, not buried after context or preamble.",
            runner=runner,
        )
        assert result.passed, f"Slack doesn't put ask first: {result.reasoning}"


class TestBlogMedium:
    def test_blog_has_section_headers(self, blog_output):
        headers = [line for line in blog_output.text.splitlines() if re.match(r"^#{1,3}\s", line)]
        assert len(headers) >= 2, (
            f"Blog post should have section headers (## or ###). Found {len(headers)}"
        )
```

- [ ] **Step 3: Commit**

```bash
git add tests/skills/ghostwrite/test_ghostwrite_rules.py tests/skills/ghostwrite/test_ghostwrite_mediums.py
git commit -m "Update ghostwrite test assertions for RunResult.text"
```

---

### Task 5: Update summarize test assertions

**Files:**
- Modify: `tests/skills/summarize/test_summarize_structure.py`
- Modify: `tests/skills/summarize/test_summarize_input_types.py`

Same pattern: every `*_output` / `summarize_output` used as a string gets `.text`.

- [ ] **Step 1: Update test_summarize_structure.py**

9 changes — every helper call and direct string op on `summarize_output` gets `.text`:

```python
class TestSummarizeStructure:
    """Template structure compliance. Every summarize output must pass these."""

    def test_starts_with_h1(self, summarize_output):
        assert starts_with_h1(summarize_output.text), (
            f"Output must start with '# '. First 80 chars: {summarize_output.text[:80]}"
        )

    def test_has_all_sections(self, summarize_output):
        missing = has_all_sections(summarize_output.text)
        assert missing == [], f"Missing required sections: {missing}"

    def test_cliff_notes_max_8_bullets(self, summarize_output):
        bullets = cliff_notes_bullets(summarize_output.text)
        assert 1 <= len(bullets) <= 8, f"Cliff Notes has {len(bullets)} bullets (expected 1-8)"

    def test_share_is_1_to_2_sentences(self, summarize_output):
        share = share_text(summarize_output.text)
        assert share is not None, "Share section is missing or has no code fence"
        # Strip bare URL lines before counting sentences
        lines = [line for line in share.splitlines() if not line.strip().startswith("http")]
        prose = " ".join(lines)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", prose) if s.strip()]
        assert 1 <= len(sentences) <= 2, (
            f"Share has {len(sentences)} sentences (expected 1-2): {share}"
        )

    def test_comment_max_20_words(self, summarize_output):
        comment = comment_text(summarize_output.text)
        assert comment is not None, "Comment section is missing or has no code fence"
        count = word_count(comment)
        assert count <= 20, f"Comment is {count} words (max 20): {comment}"

    def test_no_em_dashes(self, summarize_output):
        violations = no_em_dashes(summarize_output.text)
        assert violations == [], f"Em dashes found in lines: {violations}"

    def test_no_banned_words(self, summarize_output):
        violations = banned_words(summarize_output.text)
        assert violations == [], f"Banned words found: {violations}"

    def test_no_preamble_or_postscript(self, summarize_output):
        lines = summarize_output.text.strip().splitlines()
        first_line = lines[0].strip()
        assert first_line.startswith("# "), f"Preamble detected before H1. First line: {first_line}"
        last_line = lines[-1].strip()
        postscript_phrases = [
            "let me know",
            "here's the summary",
            "hope this helps",
            "feel free to",
        ]
        for phrase in postscript_phrases:
            assert phrase not in last_line.lower(), f"Postscript detected: {last_line}"
```

- [ ] **Step 2: Update test_summarize_input_types.py**

12 changes across 3 test classes:

```python
class TestUrlInput:
    """URL input: H1 is a markdown link, Share fence ends with bare URL."""

    def test_starts_with_h1(self, url_output):
        assert starts_with_h1(url_output.text), (
            f"URL output must start with '# '. First 80 chars: {url_output.text[:80]}"
        )

    def test_has_all_sections(self, url_output):
        missing = has_all_sections(url_output.text)
        assert missing == [], f"Missing required sections: {missing}"

    def test_h1_is_markdown_link(self, url_output):
        title = h1_title(url_output.text)
        assert title is not None, "H1 title is missing"
        assert re.match(r"\[.+\]\(https?://.+\)", title), (
            f"URL input H1 should be a markdown link [Title](url). Got: {title}"
        )

    def test_share_contains_url(self, url_output, url_source):
        share = share_text(url_output.text)
        assert share is not None, "Share section is missing or has no code fence"
        assert "http" in share, (
            f"URL input Share fence should contain the source URL. Share: {share}"
        )


class TestPastedInput:
    """Pasted text input: H1 is plain text (no link), Share has no URL."""

    def test_h1_is_plain_text(self, pasted_output):
        title = h1_title(pasted_output.text)
        assert title is not None, "H1 title is missing"
        assert not re.match(r"\[.+\]\(https?://.+\)", title), (
            f"Pasted input H1 should NOT be a markdown link. Got: {title}"
        )

    def test_share_has_no_url(self, pasted_output):
        share = share_text(pasted_output.text)
        assert share is not None, "Share section is missing or has no code fence"
        assert not re.search(r"https?://\S+", share), (
            f"Pasted input Share fence should NOT contain a URL. Share: {share}"
        )


class TestFileInput:
    """File input: H1 is plain text (no link), Share has no URL."""

    def test_starts_with_h1(self, file_output):
        assert starts_with_h1(file_output.text), (
            f"File output must start with '# '. First 80 chars: {file_output.text[:80]}"
        )

    def test_has_all_sections(self, file_output):
        missing = has_all_sections(file_output.text)
        assert missing == [], f"Missing required sections: {missing}"

    def test_h1_is_plain_text(self, file_output):
        title = h1_title(file_output.text)
        assert title is not None, "H1 title is missing"
        assert not re.match(r"\[.+\]\(https?://.+\)", title), (
            f"File input H1 should NOT be a markdown link. Got: {title}"
        )

    def test_share_has_no_url(self, file_output):
        share = share_text(file_output.text)
        assert share is not None, "Share section is missing or has no code fence"
        assert not re.search(r"https?://\S+", share), (
            f"File input Share fence should NOT contain a URL. Share: {share}"
        )
```

- [ ] **Step 3: Commit**

```bash
git add tests/skills/summarize/test_summarize_structure.py tests/skills/summarize/test_summarize_input_types.py
git commit -m "Update summarize test assertions for RunResult.text"
```

---

### Task 6: Export RunResult + final verification

**Files:**
- Modify: `tests/support/harness/__init__.py`

- [ ] **Step 1: Add RunResult to the harness __init__.py export**

```python
from tests.support.harness.claude_runner import ClaudeRunner, RunResult

__all__ = ["ClaudeRunner", "RunResult"]
```

- [ ] **Step 2: Run full unit test suite (fast, mocked tests only)**

Run: `pytest tests/support/harness/test_claude_runner.py -v`
Expected: All tests PASS (init: 11, run: 3, parse: 5, text: 3, messages: 2, tool_calls: 3, tool_results: 2 = 29 tests).

- [ ] **Step 3: Commit**

```bash
git add tests/support/harness/__init__.py
git commit -m "Export RunResult from harness package"
```

- [ ] **Step 4: Run make test (full e2e with live CLI calls)**

Run: `make test`
Expected: All ~40 tests PASS. Same 7 subprocess invocations as before — no new CLI calls.
