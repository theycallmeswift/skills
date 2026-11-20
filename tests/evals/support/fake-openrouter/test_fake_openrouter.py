"""fake-openrouter serves /credits and /models, hands out scenario replies in order, mimics bad
replies (invalid JSON, empty, reset, 402), charges spend against the balance, and logs every
request to calls.log."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

FAKE = Path(__file__).parents[4] / "evals" / "support" / "fake-openrouter"
ALPHA = "alpha/vision-pro"
KEY = {"Authorization": "Bearer sk-or-fake"}
IMAGE = "data:image/png;base64,iVBORw0KGgo="


class Fake:
    """One running fake plus helpers to call it."""

    def __init__(self, tmp_path: Path, scenario: dict):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.port = probe.getsockname()[1]
        self.state = tmp_path / "state"
        scenario_file = tmp_path / "scenario.json"
        scenario_file.write_text(json.dumps(scenario))
        self.process = subprocess.Popen(
            [
                sys.executable,
                FAKE / "server.py",
                "--scenario",
                scenario_file,
                "--state",
                self.state,
                "--port",
                str(self.port),
            ]
        )
        self.base = f"http://127.0.0.1:{self.port}/api/v1"
        for _ in range(100):
            try:
                self.get("/models")
                break
            except OSError:
                time.sleep(0.05)
        (self.state / "calls.log").write_text("")

    def get(self, path: str, headers: dict | None = None) -> tuple[int, dict]:
        request = urllib.request.Request(self.base + path, headers=headers or {})
        return self.send(request)

    def complete(self, model: str = ALPHA, **body: object) -> tuple[int, dict]:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "critique this"}],
            "max_tokens": 32000,
            "reasoning": {"effort": "medium"},
            **body,
        }
        request = urllib.request.Request(
            self.base + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={**KEY, "Content-Type": "application/json"},
        )
        return self.send(request)

    @staticmethod
    def send(request: urllib.request.Request) -> tuple[int, dict]:
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def log(self) -> list[dict]:
        text = (self.state / "calls.log").read_text()
        return [json.loads(line) for line in text.splitlines()]

    def close(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=5)


@pytest.fixture
def start(tmp_path: Path):
    servers: list[Fake] = []

    def _start(scenario: dict) -> Fake:
        servers.append(Fake(tmp_path, scenario))
        return servers[-1]

    yield _start
    for server in servers:
        server.close()


def content_of(body: dict) -> str:
    return body["choices"][0]["message"]["content"]


def test_credits_report_the_scenario_balance(start):
    fake = start({"credits": {"total_credits": 12.5, "total_usage": 2.5}})
    status, body = fake.get("/credits", KEY)
    assert status == 200
    assert body == {"data": {"total_credits": 12.5, "total_usage": 2.5}}


def test_credits_require_a_key(start):
    assert start({}).get("/credits")[0] == 401


def test_models_lists_vision_models_with_pricing_strings(start):
    status, body = start({}).get("/models")
    assert status == 200
    vision = [m for m in body["data"] if "image" in m["architecture"]["input_modalities"]]
    assert len(vision) >= 4
    assert len({m["id"].split("/")[0] for m in vision}) >= 4
    for model in vision:
        assert isinstance(model["pricing"]["prompt"], str)
        assert float(model["pricing"]["completion"]) > 0
    assert any("image" not in m["architecture"]["input_modalities"] for m in body["data"])


def test_scenario_can_replace_the_catalog(start):
    models = [{"id": "solo/only", "pricing": {"prompt": "0.000001", "completion": "0.000002"}}]
    fake = start({"models": models})
    assert [m["id"] for m in fake.get("/models")[1]["data"]] == ["solo/only"]


def test_replies_are_consumed_in_order_then_default(start):
    fake = start(
        {
            "replies": {ALPHA: [{"content": {"summary": "first"}}, {"content": "second"}]},
            "default_reply": {"content": "fallback"},
        }
    )
    contents = [content_of(fake.complete()[1]) for _ in range(3)]
    assert json.loads(contents[0]) == {"summary": "first"}
    assert contents[1:] == ["second", "fallback"]


def test_queues_are_per_model(start):
    fake = start({"replies": {ALPHA: [{"content": "a"}], "beta/sight-2": [{"content": "b"}]}})
    assert content_of(fake.complete("beta/sight-2")[1]) == "b"
    assert content_of(fake.complete(ALPHA)[1]) == "a"


def test_response_has_openrouter_shape_and_usage_cost(start):
    fake = start({"replies": {ALPHA: [{"content": "hi"}]}})
    status, body = fake.complete()
    assert status == 200
    choice = body["choices"][0]
    assert choice["finish_reason"] == "stop"
    assert choice["message"]["role"] == "assistant"
    usage = body["usage"]
    assert usage["prompt_tokens"] > 0
    assert usage["completion_tokens"] > 0
    assert usage["cost"] > 0


def test_spend_moves_the_credit_balance(start):
    fake = start({"credits": {"total_credits": 10, "total_usage": 1}})
    cost = fake.complete()[1]["usage"]["cost"]
    usage = fake.get("/credits", KEY)[1]["data"]["total_usage"]
    assert usage == pytest.approx(1 + cost)


def test_fixture_files_are_served(start):
    fake = start({"replies": {ALPHA: [{"content_file": "valid-critique-a.json"}]}})
    critique = json.loads(content_of(fake.complete()[1]))
    assert critique["issues"][0]["id"] == "I1"
    assert set(critique) == {"summary", "scores", "issues", "answers"}


def test_invalid_json_reply_keeps_its_raw_text(start):
    raw = 'Findings in prose. {"summary": "cut off'
    fake = start({"replies": {ALPHA: [{"invalid_json": raw}]}})
    status, body = fake.complete()
    assert status == 200
    assert content_of(body) == raw
    with pytest.raises(ValueError):
        json.loads(content_of(body))


def test_invalid_json_fixture_has_findings_but_no_parseable_object(start):
    fake = start({"replies": {ALPHA: [{"invalid_json_file": "invalid-json-with-findings.txt"}]}})
    text = content_of(fake.complete()[1])
    assert "Finding 2" in text
    with pytest.raises(ValueError):
        json.loads(text[text.index("{") :])


def test_empty_reply_has_no_content_and_length_finish(start):
    fake = start({"replies": {ALPHA: [{"empty": True}]}})
    status, body = fake.complete()
    assert status == 200
    assert content_of(body) == ""
    assert body["choices"][0]["finish_reason"] == "length"


def test_status_reply_returns_an_openrouter_error(start):
    fake = start({"replies": {ALPHA: [{"status": 402}]}})
    status, body = fake.complete()
    assert status == 402
    assert "credits" in body["error"]["message"].lower()


def test_reset_drops_the_connection_then_recovers(start):
    fake = start({"replies": {ALPHA: [{"reset": True}]}, "default_reply": {"content": "ok"}})
    with pytest.raises(OSError):
        fake.complete()
    assert content_of(fake.complete()[1]) == "ok"


def test_unknown_model_is_a_400(start):
    status, body = start({}).complete("nobody/nothing")
    assert status == 400
    assert "nobody/nothing" in body["error"]["message"]


def test_calls_log_has_one_line_per_request(start):
    fake = start({"replies": {ALPHA: [{"content": "x"}, {"status": 402}, {"reset": True}]}})
    fake.get("/credits", KEY)
    fake.get("/models")
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "[frame]"},
                {"type": "image_url", "image_url": {"url": IMAGE}},
                {"type": "image_url", "image_url": {"url": IMAGE}},
            ],
        }
    ]
    fake.complete(messages=messages, max_tokens=1234)
    fake.complete()
    with pytest.raises(OSError):
        fake.complete()
    lines = fake.log()
    assert [(c["method"], c["path"], c["status"]) for c in lines] == [
        ("GET", "/api/v1/credits", 200),
        ("GET", "/api/v1/models", 200),
        ("POST", "/api/v1/chat/completions", 200),
        ("POST", "/api/v1/chat/completions", 402),
        ("POST", "/api/v1/chat/completions", 0),
    ]
    completion = lines[2]
    assert completion["model"] == ALPHA
    assert completion["max_tokens"] == 1234
    assert completion["reasoning"] == {"effort": "medium"}
    assert completion["n_images"] == 2
    assert completion["ts"]
    assert lines[0]["model"] is None
    assert lines[0]["n_images"] == 0


def test_bad_scenario_exits_2(tmp_path: Path):
    missing = tmp_path / "nope.json"
    result = subprocess.run(
        [sys.executable, FAKE / "server.py", "--scenario", missing, "--state", tmp_path],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "cannot read scenario" in result.stderr
