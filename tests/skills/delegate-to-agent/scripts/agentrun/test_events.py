"""Tests for reading thread IDs and token usage from Codex's JSONL event stream."""

from __future__ import annotations

import pytest
from agentrun.events import format_usage, parse_events
from agentrun.state import Usage
from support.codex import JsonObject, jsonl

USAGE: Usage = {
    "input_tokens": 10,
    "cached_input_tokens": 4,
    "output_tokens": 2,
    "reasoning_output_tokens": 1,
}


def test_thread_id_and_last_turn_usage():
    completed_turn: JsonObject = {
        "type": "turn.completed",
        "usage": {
            "input_tokens": 10,
            "cached_input_tokens": 4,
            "output_tokens": 2,
            "reasoning_output_tokens": 1,
        },
    }
    stream = jsonl(
        {"type": "thread.started", "thread_id": "T9"},
        {"type": "turn.completed", "usage": {"input_tokens": 1}},
        completed_turn,
    )

    assert parse_events(stream) == ("T9", USAGE)


@pytest.mark.parametrize(
    "stream, expected",
    [
        (
            jsonl({"type": "thread.started", "thread_id": "T"}) + '\n{"type": "turn.comp',
            ("T", None),
        ),
        ("", (None, None)),
        ("not json\n[1,2]\n", (None, None)),
    ],
    ids=["truncated", "empty", "junk"],
)
def test_tolerates_broken_streams(stream, expected):
    assert parse_events(stream) == expected


def test_format_usage_with_counts():
    assert format_usage(USAGE) == "tokens: in 10 (cached 4), out 2, reasoning 1"


def test_format_usage_without_counts():
    assert format_usage(None) == "tokens: unavailable"
