"""Stub Responses API server and process helpers for the Codex CLI contract test."""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TypeAlias, TypedDict, cast

from codexrun.state import JobMeta, Usage

JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
LogArgument: TypeAlias = str | int | float


class ResponseFormat(TypedDict, total=False):
    """Response format fields inspected by the contract stub."""

    type: str
    schema: JsonObject


class TextOptions(TypedDict, total=False):
    """Text options inspected by the contract stub."""

    format: ResponseFormat


class RequestBody(TypedDict, total=False):
    """Subset of a Responses API request inspected by the contract stub."""

    text: TextOptions


USAGE: Usage = {
    "input_tokens": 11,
    "cached_input_tokens": 2,
    "output_tokens": 7,
    "reasoning_output_tokens": 3,
}
RESUMED_USAGE: Usage = {
    "input_tokens": 22,
    "cached_input_tokens": 4,
    "output_tokens": 14,
    "reasoning_output_tokens": 6,
}


class Stub:
    """Stateful Responses API stub that records requests and applies canned edits."""

    def __init__(self, worktree: Path):
        """Initialize the stub against the repository it may edit."""
        self.worktree = worktree
        self.requests: list[RequestBody] = []

    def reply(self, body: RequestBody) -> bytes:
        """Record one request and return its server-sent event payload."""
        index = len(self.requests)
        self.requests.append(body)
        self._apply_requested_edit(index)

        output = self._output_for(body)
        events = self._events(index, output)
        return "".join(
            f"event: {event['type']}\ndata: {json.dumps(event)}\n\n" for event in events
        ).encode()

    def _apply_requested_edit(self, index: int) -> None:
        """Apply the deterministic edit associated with a request index."""
        if index == 0:
            (self.worktree / "hello.txt").write_text("hi\n")
        elif index == 1:
            (self.worktree / "bye.txt").write_text("bye\n")

    def _output_for(self, body: RequestBody) -> str:
        """Return plain or schema-shaped assistant output for a request."""
        response_format = body.get("text", {}).get("format", {})
        if response_format.get("type") != "json_schema":
            return "STATUS: DONE\n"

        return json.dumps(
            {
                "verdict": "approve",
                "summary": "Looks good.",
                "findings": [],
                "next_steps": [],
            }
        )

    def _events(self, index: int, output: str) -> list[JsonObject]:
        """Build the Responses API events for one completed request."""
        response_id = f"resp-{index}"
        item = {
            "type": "message",
            "role": "assistant",
            "id": f"msg-{index}",
            "content": [{"type": "output_text", "text": output}],
        }
        usage = {
            "input_tokens": USAGE["input_tokens"],
            "input_tokens_details": {"cached_tokens": USAGE["cached_input_tokens"]},
            "output_tokens": USAGE["output_tokens"],
            "output_tokens_details": {"reasoning_tokens": USAGE["reasoning_output_tokens"]},
            "total_tokens": USAGE["input_tokens"] + USAGE["output_tokens"],
        }
        return [
            {"type": "response.created", "response": {"id": response_id}},
            {"type": "response.output_item.done", "item": item},
            {
                "type": "response.completed",
                "response": {"id": response_id, "usage": usage},
            },
        ]


def handler_for(stub: Stub) -> type[BaseHTTPRequestHandler]:
    """Build an HTTP handler class bound to a specific stub instance."""

    class Handler(BaseHTTPRequestHandler):
        """Serve the minimal endpoints exercised by the real Codex CLI."""

        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            """Serve the model-list probe used by the contract fixture."""
            if self.path != "/v1/models":
                self.send_error(404)
                return

            self._send_json({"models": []})

        def do_POST(self) -> None:
            """Serve one Responses API request as an event stream."""
            if self.path != "/v1/responses":
                self.send_error(404)
                return

            length = int(self.headers["Content-Length"])
            request = cast(RequestBody, json.loads(self.rfile.read(length)))
            payload = stub.reply(request)
            self._send_payload(payload, "text/event-stream")

        def _send_json(self, body: JsonObject) -> None:
            """Send a JSON response with an exact content length."""
            self._send_payload(json.dumps(body).encode(), "application/json")

        def _send_payload(self, payload: bytes, content_type: str) -> None:
            """Send a successful response with the provided payload."""
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format_string: str, *arguments: LogArgument) -> None:
            """Suppress the base handler's stderr access log."""
            pass

    return Handler


@contextmanager
def serve_stub(worktree: Path) -> Iterator[tuple[Stub, int]]:
    """Serve the Responses API stub on an ephemeral loopback port."""
    stub = Stub(worktree)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(stub))
    thread = threading.Thread(target=server.serve_forever)
    thread.start()

    try:
        yield stub, cast(int, server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "skills/delegating-to-codex/scripts/codex_run.py"
SCHEMA = ROOT / "skills/delegating-to-codex/assets/review-output.schema.json"


def git(repo: Path, *args: str) -> str:
    """Run Git with deterministic test identity configuration."""
    command = [
        "git",
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.com",
        "-C",
        str(repo),
        *args,
    ]
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def run(env: dict[str, str], repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the wrapper CLI against a contract-test repository."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--cd", str(repo)],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


def start(
    env: dict[str, str],
    repo: Path,
    mode: str,
    brief: Path,
    *args: str,
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Run a foreground job and return its process result and identifier."""
    result = run(
        env,
        repo,
        "start",
        mode,
        "--effort",
        "low",
        "--model",
        "stub-model",
        "--brief",
        str(brief),
        *args,
        "--wait",
    )
    job_id = next(
        (line.split()[1] for line in result.stdout.splitlines() if line.startswith("job ")),
        "",
    )
    return result, job_id


def job_dir(state: Path, job_id: str) -> Path:
    """Find the unique state directory for a contract-test job."""
    matches = list((state / "codex-jobs").glob(f"*/{job_id}/meta.json"))
    assert len(matches) == 1
    return matches[0].parent


def meta(state: Path, job_id: str) -> JobMeta:
    """Read metadata for a contract-test job."""
    return cast(JobMeta, json.loads((job_dir(state, job_id) / "meta.json").read_text()))


def config(port: int, *extra: str) -> str:
    """Build a Codex configuration that targets the local stub."""
    lines = [
        'model_provider = "stub"',
        *extra,
        "",
        "[model_providers.stub]",
        'name = "Stub"',
        f'base_url = "http://127.0.0.1:{port}/v1"',
        'env_key = "STUB_API_KEY"',
        'wire_api = "responses"',
        "request_max_retries = 0",
    ]
    return "\n".join(lines) + "\n"
