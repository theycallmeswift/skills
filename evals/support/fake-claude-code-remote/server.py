"""Stdio MCP server faking the claude-code-remote Routine tools.

Usage: server.py <routines.json> <call-log>

<routines.json> is a list of Routines exactly as `list_triggers` shows them.
`list_triggers` returns every Routine still held; `delete_trigger` removes one and
echoes it. Each `tools/call` appends one JSON line, tool and arguments, to <call-log>.
Standard library only: the eval guest has just the distribution's python3.
"""

import json
import sys
from pathlib import Path

# Copied from the live server in a cloud session, keeping only the inputs the fake reads.
# delete_trigger's warning is verbatim: it is what makes a bare agent refuse the delete.
TOOLS = [
    {
        "name": "list_triggers",
        "description": (
            "List Routines (scheduled triggers) owned by this account. Use it to find trigger "
            "IDs (trig_...) for update_trigger and delete_trigger. Each entry has the Routine's "
            "id, name, cron_expression, run_once_at, enabled state, ended_reason, next_run_at, "
            "created_at, persistent_session_id, and last_run. last_run is the most recent "
            "recorded run {status, fired_at, finished_at, session_id}. It is absent when no run "
            "was recorded (e.g. never fired). For a Routine that wakes an existing session, "
            "last_run records that the wake was delivered (SUCCEEDED) or failed to deliver, not "
            "how the turn went."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "When set, only Routines whose enabled state matches. "
                    "Omit for both.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum Routines to return (default 20, max 100).",
                },
            },
        },
    },
    {
        "name": "delete_trigger",
        "description": (
            "Delete a Routine (scheduled trigger). The Routine must belong to the calling "
            "session's account — deleting another account's Routine fails with not-found. "
            "Use this to undo a create_trigger call or to clean up Routines whose work is done. "
            "Deleting a Routine also deletes every session it started, so a session the Routine "
            "started cannot delete it. From such a session, stop the Routine with update_trigger "
            "(enabled=false) instead. A bad cron or wrong prompt does not need deletion — "
            "update_trigger fixes those in place, keeping the Routine's run history. On success, "
            "the result usually echoes the deleted Routine's last state (including its name) in "
            "the response's trigger field — callers without stored-data read access get a "
            "plain-text confirmation instead. Either way the Routine no longer exists once this "
            "returns."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "trigger_id": {
                    "type": "string",
                    "description": "The Routine's trigger ID to delete (starts with 'trig_'). "
                    "Returned by create_trigger in the response's trigger.id field, or by "
                    "list_triggers.",
                }
            },
            "required": ["trigger_id"],
        },
    },
]


def call_tool(routines: list[dict], name: object, arguments: dict) -> dict:
    """Answer one tool call from the held Routines, deleting from them in place."""
    if name == "list_triggers":
        result: object = {"data": routines, "has_more": False}
    elif name == "delete_trigger":
        trigger_id = arguments.get("trigger_id")
        held = [each for each in routines if each["id"] == trigger_id]
        if not held:
            return {"isError": True, "content": [{"type": "text", "text": "Routine not found"}]}
        routines.remove(held[0])
        result = {"trigger": held[0]}
    else:
        return {"isError": True, "content": [{"type": "text", "text": f"unknown tool {name}"}]}

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


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
        result = {"tools": TOOLS}
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

    routines = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
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
