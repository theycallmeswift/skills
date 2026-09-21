"""Read Codex's `--json` event stream: thread id and token usage."""

from __future__ import annotations

import json
from typing import cast

from agentrun.state import Usage

USAGE_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
)


def parse_events(text: str) -> tuple[str | None, Usage | None]:
    """Read the thread ID and last completed turn's usage from a JSONL stream."""
    thread_id, usage = None, None

    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue

        if not isinstance(event, dict):
            continue

        event_type = event.get("type")
        if event_type == "thread.started" and event.get("thread_id"):
            thread_id = event["thread_id"]
        elif event_type == "turn.completed" and isinstance(event.get("usage"), dict):
            turn_usage = event["usage"]
            usage = cast(Usage, {key: turn_usage.get(key, 0) for key in USAGE_KEYS})

    return thread_id, usage


def format_usage(usage: Usage | None) -> str:
    """Format token usage for terminal output."""
    if not usage:
        return "tokens: unavailable"

    return (
        f"tokens: in {usage.get('input_tokens', 0)} "
        f"(cached {usage.get('cached_input_tokens', 0)}), "
        f"out {usage.get('output_tokens', 0)}, "
        f"reasoning {usage.get('reasoning_output_tokens', 0)}"
    )
