# Migrate ClaudeRunner to stream-json

**Date:** 2026-04-11
**Status:** Draft

## Goal

Switch ClaudeRunner from `--output-format text` to `--output-format stream-json --verbose` so every test run captures the full conversation trace — tool calls, cost, duration, token usage — not just the final text. This unlocks process verification tests (e.g. "did summarize dispatch a ghostwrite subagent?") without adding CLI calls.

## Non-Goals

- Writing process verification tests for summarize (separate spec).
- Changing the test fixtures or conftest files (they already return `runner.run()`; the return type changes but the call sites don't).
- Real-time streaming or early termination (we parse the full stream after the subprocess exits, same as today).
- Changing how the skill-creator scripts work (external dependency, untouched).

## Approach

Replace the `subprocess.run` call in `ClaudeRunner.run()` to use `--output-format stream-json --verbose`. Parse the NDJSON stdout into a `RunResult` dataclass that stores all raw events and exposes `.text`, `.messages`, `.tool_calls`, `.tool_results` as computed properties. Update all existing test assertions from bare string operations to `.text` access. No extra CLI calls, no new fixtures, no new dependencies.

## Components

- `tests/support/harness/claude_runner.py` — add `RunResult` dataclass, change `run()` to parse stream-json and return `RunResult`
- `tests/support/harness/__init__.py` — export `RunResult`
- `tests/support/harness/test_claude_runner.py` — update subprocess mock to produce stream-json output, add `RunResult` parsing tests
- `tests/skills/ghostwrite/test_ghostwrite_rules.py` — `.text` on all string assertions
- `tests/skills/ghostwrite/test_ghostwrite_mediums.py` — `.text` on all string assertions
- `tests/skills/summarize/test_summarize_structure.py` — `.text` on all string assertions
- `tests/skills/summarize/test_summarize_input_types.py` — `.text` on all string assertions

## Data / Interfaces

### RunResult dataclass

```python
@dataclasses.dataclass(frozen=True)
class RunResult:
    events: tuple[dict, ...]     # All stream events in order (raw NDJSON, parsed)
    cost_usd: float              # total_cost_usd from result event
    duration_ms: int             # duration_ms from result event
    num_turns: int               # num_turns from result event
    usage: dict                  # {input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens}
    stop_reason: str             # "end_turn", "max_tokens", etc.

    @property
    def text(self) -> str:
        """Final assistant message text. Replaces what --output-format text returned."""
        for event in reversed(self.events):
            if event.get("type") != "assistant":
                continue
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    return block["text"]
        return ""

    @property
    def messages(self) -> list[dict]:
        """All assistant and user (tool result) events, in order."""
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
        """All tool result events (type: user with tool_result content), in order."""
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
```

Uses `tuple` for `events` since the dataclass is frozen. Properties are computed on access — fine for test assertions, no caching needed.

### Event types and shapes (confirmed via live testing)

The stream produces 5 event types. We store `assistant` and `user` events. We extract metadata from `result`. We ignore `system` and `rate_limit_event`.

**`assistant` events** — one per content block, not per message. A single API message with `[thinking, tool_use]` emits two NDJSON lines sharing the same `message.id`:

```json
{
  "type": "assistant",
  "message": {
    "model": "claude-haiku-4-5-20251001",
    "id": "msg_01HZ7TU8R14oz69f7BZ7GJW5",
    "type": "message",
    "role": "assistant",
    "content": [
      {
        "type": "tool_use",
        "id": "toolu_01JYToBm47G3JHqYGNazAK6U",
        "name": "Read",
        "input": { "file_path": "/tmp/test.txt" }
      }
    ],
    "stop_reason": null
  },
  "parent_tool_use_id": null,
  "session_id": "..."
}
```

Content block types: `thinking`, `text`, `tool_use`. Each appears in its own `assistant` event.

**`user` events** — tool results. There is no dedicated `tool_result` event type; results arrive as `type: "user"`:

```json
{
  "type": "user",
  "message": {
    "role": "user",
    "content": [
      {
        "tool_use_id": "toolu_01JYToBm47G3JHqYGNazAK6U",
        "type": "tool_result",
        "content": "1\thello world\n"
      }
    ]
  },
  "tool_use_result": {
    "type": "text",
    "file": {
      "filePath": "/tmp/test.txt",
      "content": "hello world\n",
      "numLines": 2
    }
  },
  "session_id": "..."
}
```

`tool_use_result` is a top-level field with structured data (cleaner than the raw `content` string sent to the model).

**`result` event** — always the last line:

```json
{
  "type": "result",
  "subtype": "success",
  "is_error": false,
  "duration_ms": 4426,
  "num_turns": 1,
  "result": "the final text",
  "stop_reason": "end_turn",
  "total_cost_usd": 0.017,
  "usage": {
    "input_tokens": 10,
    "output_tokens": 383,
    "cache_read_input_tokens": 18450,
    "cache_creation_input_tokens": 10751
  }
}
```

### Event sequence for a multi-turn conversation

```
system/init
assistant(thinking)              # turn 1: model decides to call tool
assistant(tool_use: Skill)       # same message.id as thinking above
user(tool_result)                # skill content loaded
assistant(thinking)              # turn 2
assistant(tool_use: scrape)      # fetch content
user(tool_result)                # scraped page
assistant(thinking)              # turn 3
assistant(tool_use: Agent)       # dispatch ghostwrite subagent
user(tool_result)                # ghostwritten text
assistant(thinking)              # turn 4
assistant(text)                  # final response template
result                           # metadata
```

When the model calls multiple tools in the same turn, you get interleaved `assistant(tool_use)` / `user(tool_result)` pairs under the same `message.id`.

### ClaudeRunner.run() changes

Before:
```python
def run(self, prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", self.model,
         "--output-format", "text", "--plugin-dir", str(self.plugin_dir),
         "--dangerously-skip-permissions"],
        capture_output=True, text=True, timeout=self.timeout,
        cwd=self.cwd, env=self.env,
    )
    if result.returncode != 0:
        raise RuntimeError(...)
    return result.stdout.strip()
```

After:
```python
def run(self, prompt: str) -> RunResult:
    result = subprocess.run(
        ["claude", "-p", prompt, "--model", self.model,
         "--output-format", "stream-json", "--verbose",
         "--plugin-dir", str(self.plugin_dir),
         "--dangerously-skip-permissions"],
        capture_output=True, text=True, timeout=self.timeout,
        cwd=self.cwd, env=self.env,
    )
    if result.returncode != 0:
        raise RuntimeError(...)
    return _parse_stream(result.stdout)
```

`_parse_stream(raw: str) -> RunResult` is a module-level function that splits on newlines, parses each JSON line, collects tool_calls from `assistant` events, and extracts metadata from the `result` event.

### Test assertion changes

Every test that currently treats the output as a bare string adds `.text`. Examples:

```python
# Before
def test_no_em_dashes(self, email_output):
    violations = no_em_dashes(email_output)

# After
def test_no_em_dashes(self, email_output):
    violations = no_em_dashes(email_output.text)
```

```python
# Before (parametrized)
def test_starts_with_h1(self, summarize_output):
    assert starts_with_h1(summarize_output)

# After
def test_starts_with_h1(self, summarize_output):
    assert starts_with_h1(summarize_output.text)
```

The `judge()` helper takes `source` and `output` as strings — callers pass `.text`:
```python
# Before
result = judge(source=email_source, output=email_output, ...)

# After
result = judge(source=email_source, output=email_output.text, ...)
```

### Files changed and assertion count

| File | String assertions to update |
|---|---|
| `test_ghostwrite_rules.py` | 6 (all pass source/output strings to helpers) |
| `test_ghostwrite_mediums.py` | 10 (mix of direct string ops and helper/judge calls) |
| `test_summarize_structure.py` | 8 (all pass output to helpers) |
| `test_summarize_input_types.py` | 8 (all pass output to helpers or do direct string checks) |
| **Total** | **~32 assertions** |

## Testing

- **Unit tests for `_parse_stream`**: Feed it synthetic NDJSON with known `assistant`, `user`, `system`, and `result` events. Verify `RunResult.events` contains only `assistant` and `user` events in order, and that metadata fields are extracted from the `result` event. These are fast, no CLI calls.
- **Unit tests for `RunResult` properties**: Verify `.text` returns last assistant text block, `.messages` filters to assistant+user events, `.tool_calls` flattens all tool_use blocks in order, `.tool_results` collects all user/tool_result events with structured data.
- **Existing `TestClaudeRunnerRun` mock tests**: Update the mock to return stream-json stdout instead of plain text. Verify `run()` returns a `RunResult` with correct `.text`.
- **Existing skill tests**: Run `make test` end-to-end. All 30+ tests should pass with no behavior change (they just read `.text` now).
- **No new CLI calls** added by this refactor. Same 7 session-scoped fixtures, same 7 subprocess invocations.

## Open Questions

None.
