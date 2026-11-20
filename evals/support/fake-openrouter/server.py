#!/usr/bin/env python3
"""A fake OpenRouter HTTP API for evals of scripts that call OpenRouter.

Usage:
    server.py --scenario FILE --state DIR [--port 8787] [--host 127.0.0.1]
        [--forward-agent https://openrouter.ai/api]

Serves `GET /api/v1/credits`, `GET /api/v1/models` and `POST /api/v1/chat/completions`. A
scenario JSON decides the balance, the model catalog and, per model, the replies handed out
in order across requests. Every request is appended to `<state>/calls.log` as one JSON line.

With --forward-agent, requests under `/agent/v1/messages` (the Anthropic Messages API an eval
agent runs on) are relayed to that base URL through $HTTPS_PROXY, streaming the reply, and
logged to `<state>/agent.log` instead. Nothing else is ever forwarded, so a script in the guest
reaches real completions only through the agent's own messages endpoint.
See README.md for the scenario format. Standard library only: it runs in the eval guest.

Exit codes: 0 stopped by signal, 2 bad usage or unreadable scenario.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import ssl
import sys
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
API = "/api/v1"
AGENT_PREFIX = "/agent"
AGENT_MESSAGES = f"{AGENT_PREFIX}/v1/messages"
AGENT_TIMEOUT_SECONDS = 900
# Hop-by-hop or recomputed headers that must not be copied across the relay.
SKIPPED_HEADERS = {
    "host",
    "connection",
    "keep-alive",
    "content-length",
    "transfer-encoding",
    "accept-encoding",
    "proxy-connection",
}
FAKE_KEY = "sk-or-fake"
EMPTY_COMPLETION_TOKENS = 32000
STATUS_MESSAGES = {
    400: "Bad request",
    401: "No auth credentials found",
    402: "Insufficient credits. Add more using https://openrouter.ai/settings/credits",
    404: "No endpoints found",
    429: "Rate limit exceeded",
    500: "Internal server error",
    502: "Provider returned error",
    503: "Service unavailable",
}


class Scenario:
    """The scripted behaviour: balance, catalog and per-model reply queues."""

    def __init__(self, data: dict, base_dir: Path):
        """Load credits, catalog and reply queues from scenario data; base_dir finds fixtures."""
        self.base_dir = base_dir
        credits = data.get("credits", {})
        self.total_credits = float(credits.get("total_credits", 100.0))
        self.total_usage = float(credits.get("total_usage", 0.0))
        models = data.get("models")
        if models is None:
            models = json.loads((HERE / "fixtures" / "models.json").read_text())["data"]
        self.models = models
        self.replies = {slug: list(queue) for slug, queue in data.get("replies", {}).items()}
        self.default_reply = data.get("default_reply", {"content_file": "valid-critique-a.json"})
        self.spent = 0.0
        self.lock = threading.Lock()

    def model(self, slug: str) -> dict | None:
        """The catalog entry for slug, or None when the model is unknown."""
        return next((entry for entry in self.models if entry["id"] == slug), None)

    def next_reply(self, slug: str) -> dict:
        """Pop the model's next scripted reply, or the default once its queue is empty."""
        with self.lock:
            queue = self.replies.get(slug, [])
            return queue.pop(0) if queue else self.default_reply

    def credits(self) -> dict:
        """The /credits payload: total credits and usage including spend charged so far."""
        with self.lock:
            usage = round(self.total_usage + self.spent, 8)
        return {"data": {"total_credits": self.total_credits, "total_usage": usage}}

    def charge(self, cost: float) -> None:
        """Add one completion's cost to the running spend."""
        with self.lock:
            self.spent += cost

    def read_fixture(self, name: str) -> str:
        """Read a fixture named relative to the scenario file, then to fixtures/."""
        for base in (self.base_dir, HERE / "fixtures"):
            path = base / name
            if path.is_file():
                return path.read_text()
        raise FileNotFoundError(name)


def render_content(reply: dict, scenario: Scenario) -> str | None:
    """The reply's message content, or None when it carries none (`empty`)."""
    if "content_file" in reply:
        return scenario.read_fixture(reply["content_file"]).rstrip("\n")
    if "content" in reply:
        content = reply["content"]
        return content if isinstance(content, str) else json.dumps(content)
    if "invalid_json_file" in reply:
        return scenario.read_fixture(reply["invalid_json_file"]).rstrip("\n")
    if "invalid_json" in reply:
        return str(reply["invalid_json"])
    return None


def count_images(messages: list) -> int:
    """Count image_url parts across all chat messages."""
    total = 0
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, list):
            total += sum(1 for part in content if part.get("type") == "image_url")
    return total


def prompt_chars(messages: list) -> int:
    """Count characters of text content across all chat messages."""
    total = 0
    for message in messages:
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            texts = (part.get("text", "") for part in content if part.get("type") == "text")
            total += sum(len(text) for text in texts)
    return total


class Handler(BaseHTTPRequestHandler):
    """Serves the fake API routes from the class-level scenario and call log."""

    scenario: Scenario
    log_path: Path
    log_lock = threading.Lock()
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        """Silence the default per-request stderr logging; calls.log is the record."""

    def record(self, status: int, body: dict | None = None, reply: str | None = None) -> None:
        """Append one line to calls.log. `status` 0 means the socket was reset unanswered."""
        body = body or {}
        raw_messages = body.get("messages")
        messages = raw_messages if isinstance(raw_messages, list) else []
        line = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "method": self.command,
            "path": self.path,
            "model": body.get("model"),
            "max_tokens": body.get("max_tokens"),
            "reasoning": body.get("reasoning"),
            "n_images": count_images(messages),
            "status": status,
            "reply": reply,
        }
        with self.log_lock, self.log_path.open("a") as log:
            log.write(json.dumps(line) + "\n")

    def send_json(self, status: int, payload: dict) -> None:
        """Write a JSON response with the given status."""
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_error_json(self, status: int, message: str | None = None) -> None:
        """Write an OpenRouter-shaped error body, with a stock message when none is given."""
        text = message or STATUS_MESSAGES.get(status, "Error")
        self.send_json(status, {"error": {"code": status, "message": text, "metadata": None}})

    def authorized(self) -> bool:
        """Whether the request carries a non-empty Bearer token."""
        return self.headers.get("Authorization", "").startswith("Bearer ") and (
            len(self.headers["Authorization"]) > len("Bearer ")
        )

    forward_base: str | None = None

    def relay_agent(self, body: bytes) -> None:
        """Relay an agent Messages API request upstream and stream the reply back unchanged."""
        path = self.path.split("?")[0]
        if not self.forward_base or not path.startswith(AGENT_MESSAGES):
            self.log_agent(404, 0)
            return self.send_error_json(404, f"No agent route for {path}")
        target = urlsplit(self.forward_base)
        upstream_path = target.path.rstrip("/") + self.path[len(AGENT_PREFIX) :]
        headers = {
            name: value
            for name, value in self.headers.items()
            if name.lower() not in SKIPPED_HEADERS
        }
        headers["Host"] = target.netloc
        headers["Content-Length"] = str(len(body))
        connection = upstream_connection(target.hostname or "", target.port or 443)
        try:
            connection.request(self.command, upstream_path, body=body, headers=headers)
            response = connection.getresponse()
            self.send_response(response.status)
            for name, value in response.getheaders():
                if name.lower() not in SKIPPED_HEADERS:
                    self.send_header(name, value)
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            sent = 0
            while chunk := response.read1(65536):
                self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                self.wfile.flush()
                sent += len(chunk)
            self.wfile.write(b"0\r\n\r\n")
            self.log_agent(response.status, sent)
        finally:
            connection.close()

    def log_agent(self, status: int, size: int) -> None:
        """Append one relayed (or refused) agent request to agent.log, never to calls.log."""
        line = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "method": self.command,
            "path": self.path,
            "status": status,
            "bytes": size,
        }
        with self.log_lock, (self.log_path.parent / "agent.log").open("a") as log:
            log.write(json.dumps(line) + "\n")

    def do_GET(self) -> None:
        """Serve the model catalog and the credits balance."""
        path = self.path.split("?")[0]
        if path.startswith(AGENT_PREFIX):
            return self.relay_agent(b"")
        if path == f"{API}/models":
            self.record(200)
            self.send_json(200, {"data": self.scenario.models})
        elif path == f"{API}/credits":
            if not self.authorized():
                self.record(401)
                return self.send_error_json(401)
            self.record(200)
            self.send_json(200, self.scenario.credits())
        else:
            self.record(404)
            self.send_error_json(404, f"No route for {path}")

    def do_POST(self) -> None:
        """Validate a chat-completions request and answer it from the scenario."""
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if self.path.startswith(AGENT_PREFIX):
            return self.relay_agent(raw)
        if self.path.split("?")[0] != f"{API}/chat/completions":
            self.record(404)
            return self.send_error_json(404, f"No route for {self.path}")
        try:
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError
        except ValueError:
            self.record(400)
            return self.send_error_json(400, "Invalid JSON body")
        if not self.authorized():
            self.record(401, body)
            return self.send_error_json(401)
        slug = str(body.get("model"))
        model = self.scenario.model(slug)
        if model is None:
            self.record(400, body)
            return self.send_error_json(400, f"{slug} is not a valid model ID")
        reply = self.scenario.next_reply(slug)
        self.respond(reply, body, model)

    def respond(self, reply: dict, body: dict, model: dict) -> None:
        """Play one scripted reply: reset, error status, delay, or a billed completion."""
        if reply.get("reset"):
            self.record(0, body, "reset")
            self.close_connection = True
            self.connection.close()
            return
        if "status" in reply:
            self.record(int(reply["status"]), body, f"status {reply['status']}")
            return self.send_error_json(int(reply["status"]), reply.get("message"))
        if reply.get("delay"):
            time.sleep(float(reply["delay"]))
        messages = body["messages"] if isinstance(body.get("messages"), list) else []
        if reply.get("empty"):
            content, kind = "", "empty"
            finish = "length"
            completion_tokens = int(reply.get("completion_tokens", EMPTY_COMPLETION_TOKENS))
        else:
            rendered = render_content(reply, self.scenario)
            content = rendered if rendered is not None else ""
            raw = "invalid_json" in reply or "invalid_json_file" in reply
            kind = "invalid_json" if raw else "content"
            finish = reply.get("finish_reason", "stop")
            completion_tokens = int(reply.get("completion_tokens", len(content) // 4 + 1))
        prompt_tokens = int(
            reply.get("prompt_tokens", prompt_chars(messages) // 4 + 800 * count_images(messages))
        )
        pricing = model.get("pricing", {})
        cost = reply.get("cost")
        if cost is None:
            cost = prompt_tokens * float(pricing.get("prompt", 0)) + completion_tokens * float(
                pricing.get("completion", 0)
            )
        cost = round(float(cost), 8)
        self.scenario.charge(cost)
        self.record(200, body, kind)
        self.send_json(
            200,
            {
                "id": f"gen-fake-{int(time.time() * 1000)}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model["id"],
                "provider": "FakeProvider",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": finish,
                        "native_finish_reason": finish,
                        "message": {"role": "assistant", "content": content, "refusal": None},
                    }
                ],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                    "cost": cost,
                },
            },
        )


def upstream_connection(host: str, port: int) -> http.client.HTTPSConnection:
    """An HTTPS connection to host, tunnelled through $HTTPS_PROXY when one is set.

    The proxy resolves the host itself, so the guest's /etc/hosts block on openrouter.ai
    doesn't stop the relay; certificates verify against the default trust (SSL_CERT_FILE).
    """
    context = ssl.create_default_context()
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not proxy:
        return http.client.HTTPSConnection(
            host, port, timeout=AGENT_TIMEOUT_SECONDS, context=context
        )
    parts = urlsplit(proxy)
    connection = http.client.HTTPSConnection(
        parts.hostname or "", parts.port or 80, timeout=AGENT_TIMEOUT_SECONDS, context=context
    )
    connection.set_tunnel(host, port)
    return connection


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: load the scenario and serve until interrupted; returns the exit code."""
    parser = argparse.ArgumentParser(description="Fake OpenRouter API for evals.")
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--forward-agent", default=None, metavar="BASE_URL")
    args = parser.parse_args(argv)
    try:
        scenario = Scenario(json.loads(args.scenario.read_text()), args.scenario.resolve().parent)
    except (OSError, ValueError) as error:
        print(f"cannot read scenario {args.scenario}: {error}", file=sys.stderr)
        return 2
    args.state.mkdir(parents=True, exist_ok=True)
    Handler.scenario = scenario
    Handler.log_path = args.state / "calls.log"
    Handler.log_path.touch()
    Handler.forward_base = args.forward_agent
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
