#!/usr/bin/env python3
"""Stand-in for the `codex` CLI that logs calls and emits canned JSON events.

Env knobs: FAKE_CODEX_LOG (required; one JSON line per call: argv, stdin, cwd, pid),
FAKE_CODEX_LOGIN_RC, FAKE_CODEX_RC, FAKE_CODEX_SLEEP (seconds), FAKE_THREAD_ID.
"""

from __future__ import annotations

import json
import os
import sys
import time

USAGE = {
    "input_tokens": 100,
    "cached_input_tokens": 40,
    "output_tokens": 7,
    "reasoning_output_tokens": 3,
}


def emit(event: dict[str, str | dict[str, int]]) -> None:
    """Write one fake Codex event as JSONL."""
    print(json.dumps(event), flush=True)


def main(args: list[str]) -> int:
    """Handle login checks or execute one canned Codex turn."""
    if args[:2] == ["login", "status"]:
        return_code = int(os.environ.get("FAKE_CODEX_LOGIN_RC", "0"))
        print("Logged in" if return_code == 0 else "Not logged in", file=sys.stderr)
        return return_code

    call = {"argv": args, "stdin": sys.stdin.read(), "cwd": os.getcwd(), "pid": os.getpid()}
    with open(os.environ["FAKE_CODEX_LOG"], "a") as log:
        log.write(json.dumps(call) + "\n")

    emit({"type": "thread.started", "thread_id": os.environ.get("FAKE_THREAD_ID", "thread-abc")})
    time.sleep(float(os.environ.get("FAKE_CODEX_SLEEP", "0")))
    with open(args[args.index("-o") + 1], "w") as output_file:
        output_file.write("STATUS: DONE\n")
    emit({"type": "turn.completed", "usage": USAGE})
    return int(os.environ.get("FAKE_CODEX_RC", "0"))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
