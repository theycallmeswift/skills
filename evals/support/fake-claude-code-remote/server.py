"""Stdio MCP server replaying the claude-code-remote Routine tools from cassette.json.

Usage: server.py <routines.json> <call-log>

cassette.json is recorded from the live server (see README.md). <routines.json> is a list
of partial Routines; each is laid over the recorded Routine so every live field is present.
`list_triggers` returns every Routine still held; `delete_trigger` removes one and echoes it.
Each `tools/call` appends one JSON line, tool and arguments, to <call-log>.
Standard library only: the eval guest has just the distribution's python3.
"""

import json
import sys
from pathlib import Path

CASSETTE = json.loads((Path(__file__).parent / "cassette.json").read_text(encoding="utf-8"))


def overlay(base: dict, changes: dict) -> dict:
    """`base` with `changes` merged in, recursing into nested objects."""
    merged = dict(base)
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            value = overlay(base[key], value)
        merged[key] = value
    return merged


def text(result: object, is_error: bool = False) -> dict:
    """A tool result carrying `result` as one text block, compact JSON like the live server."""
    body = result if isinstance(result, str) else json.dumps(result, separators=(",", ":"))
    return {"content": [{"type": "text", "text": body}], "isError": is_error}


def call_tool(routines: list[dict], name: object, arguments: dict) -> dict:
    """Answer one tool call from the held Routines, deleting from them in place."""
    if name == "list_triggers":
        return text(overlay(CASSETTE["list_triggers"], {"data": routines}))
    if name == "delete_trigger":
        held = [each for each in routines if each["id"] == arguments.get("trigger_id")]
        if not held:
            return text("Routine not found", is_error=True)
        routines.remove(held[0])
        return text({"trigger": held[0]})
    return text(f"unknown tool {name}", is_error=True)


def answer(message: dict, routines: list[dict], call_log: Path) -> dict | None:
    """The JSON-RPC response to one message, or None for a notification."""
    if "id" not in message:
        return None

    method = message.get("method")
    params = message.get("params") or {}
    if method == "initialize":
        result: dict = {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "fake-claude-code-remote", "version": "0.0.0"},
        }
    elif method == "tools/list":
        result = {"tools": CASSETTE["tools"]}
    elif method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        with call_log.open("a", encoding="utf-8") as log:
            log.write(json.dumps({"tool": name, "arguments": arguments}) + "\n")
        result = call_tool(routines, name, arguments)
    elif method == "ping":
        result = {}
    else:
        error = {"code": -32601, "message": f"unsupported method {method}"}
        return {"jsonrpc": "2.0", "id": message["id"], "error": error}

    return {"jsonrpc": "2.0", "id": message["id"], "result": result}


def main() -> int:
    """Serve newline-delimited JSON-RPC on stdin and stdout until stdin closes."""
    if len(sys.argv) != 3:
        print("usage: server.py <routines.json> <call-log>", file=sys.stderr)
        return 2

    scenario = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    routines = [overlay(CASSETTE["routine"], each) for each in scenario]
    call_log = Path(sys.argv[2])
    call_log.parent.mkdir(parents=True, exist_ok=True)
    for line in sys.stdin:
        if not line.strip():
            continue
        response = answer(json.loads(line), routines, call_log)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
