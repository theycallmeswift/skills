"""Synthetic stream-json NDJSON for unit tests."""

import json

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
