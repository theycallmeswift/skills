"""Tests for run_critique.py against an in-process threaded HTTP fake of the OpenRouter API.

Covers: cost gate (exit 3, no completion call), --estimate-only, request wire format
(max_tokens, content order), records for success / bad JSON / empty reply / 402 / dropped
connection / 5xx, 408 and 429 retry, spend reservation under parallel workers, incremental
record writes, cost summed across attempts, JSON extraction, --only / --force reruns,
run_stats.json, exit codes and usage errors.
"""

from __future__ import annotations

import http.client
import json
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import run_critique

GOOD_REPLY = {"summary": "fine", "scores": [], "issues": [], "answers": []}
PRICES = {"vendor-a/vision": ("0.000001", "0.000002"), "vendor-b/eye": ("0.000001", "0.000002")}


@dataclass
class Reply:
    """One scripted HTTP reply; drop=True closes the socket without answering."""

    status: int = 200
    body: dict | None = None
    drop: bool = False


def completion(text: str, cost: float = 0.01) -> Reply:
    """Build a successful chat-completions reply carrying text."""
    return Reply(
        body={
            "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
            "usage": {"cost": cost, "prompt_tokens": 100, "completion_tokens": 50},
        }
    )


class FakeOpenRouter:
    """Threaded fake serving /credits, /models and /chat/completions on localhost."""

    def __init__(self, credits: float = 100.0, prices: dict | None = None) -> None:
        """Start serving; script completion replies by assigning `on_completion`."""
        self.credits = credits
        self.prices = PRICES if prices is None else prices
        self.models_payload: list[dict] | None = None
        self.completions: list[dict] = []
        self.paths: list[str] = []
        self.on_completion = lambda body: completion(json.dumps(GOOD_REPLY))
        self._lock = threading.Lock()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            """Routes requests to the fake's state."""

            def log_message(self, format, *args):
                """Silence request logging."""

            def do_GET(self):
                """Serve credits and model pricing."""
                fake.paths.append(self.path)
                if self.path == "/v1/credits":
                    payload = {"data": {"total_credits": fake.credits, "total_usage": 0}}
                else:
                    listed = fake.models_payload or [
                        {"id": slug, "pricing": {"prompt": prompt, "completion": output}}
                        for slug, (prompt, output) in fake.prices.items()
                    ]
                    payload = {"data": listed}
                self.send_json(200, payload)

            def do_POST(self):
                """Record the completion request and play the scripted reply."""
                length = int(self.headers["Content-Length"])
                body = json.loads(self.rfile.read(length))
                with fake._lock:
                    fake.paths.append(self.path)
                    fake.completions.append(body)
                reply = fake.on_completion(body)
                if reply.drop:
                    self.connection.close()
                    return
                self.send_json(reply.status, reply.body or {})

            def send_json(self, status, payload):
                """Write a JSON response."""
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def completion_models(self) -> list[str]:
        """Model slugs of every completion request received, in arrival order."""
        return [body["model"] for body in self.completions]

    def close(self) -> None:
        """Stop the server."""
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture(autouse=True)
def no_retry_pause(monkeypatch):
    """Make the pause between attempts instant."""
    monkeypatch.setattr(run_critique, "RETRY_DELAY_SECONDS", 0)


@pytest.fixture
def fake():
    """A fake OpenRouter, shut down after the test."""
    server = FakeOpenRouter()
    yield server
    server.close()


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    """Give every test an API key and a clean base-url environment."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)


@pytest.fixture
def workspace(tmp_path):
    """A rubric, a one-image package with a token file, and an output directory path."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "home.png").write_bytes(b"\x89PNG fake image bytes")
    (package / "manifest.json").write_text(
        json.dumps(
            [{"file": "home.png", "frame": "Home", "theme": "light", "description": "landing"}]
        )
    )
    (package / "tokens.json").write_text('{"color": "#fff"}')
    (package / "notes.md").write_text("brand notes")
    rubric = tmp_path / "rubric.md"
    rubric.write_text("Critique this design.")
    return {"rubric": str(rubric), "package": str(package), "out": tmp_path / "out"}


def run(workspace, fake, *extra, models="vendor-a/vision,vendor-b/eye", runs="2", cap="5"):
    """Invoke run_critique.main against the fake."""
    return run_critique.main(
        [
            workspace["rubric"],
            workspace["package"],
            str(workspace["out"]),
            "--models",
            models,
            "--runs",
            runs,
            "--cap",
            cap,
            "--base-url",
            fake.url,
            *extra,
        ]
    )


def read_record(workspace, name):
    """Load one record file by name."""
    return json.loads((workspace["out"] / "records" / name).read_text())


def test_happy_path_writes_a_record_per_pair_and_stats(workspace, fake, capsys):
    exit_code = run(workspace, fake)

    records = sorted(path.name for path in (workspace["out"] / "records").iterdir())
    stats = json.loads((workspace["out"] / "run_stats.json").read_text())
    assert exit_code == 0
    assert records == [
        "vendor-a__vision__run1.json",
        "vendor-a__vision__run2.json",
        "vendor-b__eye__run1.json",
        "vendor-b__eye__run2.json",
    ]
    assert stats["runs"] == 4
    assert stats["parsed_runs"] == 4
    assert stats["failed"] == []
    assert "parsed 4/4 runs" in capsys.readouterr().out


def test_record_has_the_contract_fields(workspace, fake):
    run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    assert set(record) == {
        "model",
        "run",
        "ok",
        "error",
        "status",
        "raw_text",
        "parsed",
        "cost_usd",
        "prompt_tokens",
        "completion_tokens",
        "seconds",
        "finish_reason",
    }
    assert record["ok"] is True
    assert record["parsed"] == GOOD_REPLY
    assert record["cost_usd"] == 0.01
    assert record["finish_reason"] == "stop"


def test_every_request_asks_for_at_least_32000_max_tokens(workspace, fake):
    run(workspace, fake)

    assert len(fake.completions) == 4
    assert all(body["max_tokens"] >= 32000 for body in fake.completions)
    assert all(body["usage"] == {"include": True} for body in fake.completions)
    assert all(body["reasoning"] == {"effort": "medium"} for body in fake.completions)


def test_message_orders_rubric_then_images_then_text_files(workspace, fake):
    run(workspace, fake, runs="1", models="vendor-a/vision")

    parts = fake.completions[0]["messages"][0]["content"]
    assert parts[0] == {"type": "text", "text": "Critique this design."}
    assert parts[1] == {"type": "text", "text": "[Home] (light): landing"}
    assert parts[2]["type"] == "image_url"
    assert parts[2]["image_url"]["url"].startswith("data:image/png;base64,")
    assert [part["text"] for part in parts[3:]] == [
        "[notes.md]\nbrand notes",
        '[tokens.json]\n{"color": "#fff"}',
    ]


def test_cost_gate_over_cap_exits_3_without_any_completion_call(workspace, fake, capsys):
    exit_code = run(workspace, fake, cap="0.001")

    assert exit_code == 3
    assert fake.completions == []
    assert not (workspace["out"] / "records").exists()
    assert "exceeds cap" in capsys.readouterr().out


def test_cost_gate_over_balance_exits_3_without_any_completion_call(workspace, capsys):
    broke = FakeOpenRouter(credits=0.01)
    try:
        exit_code = run(workspace, broke, cap="50")
    finally:
        broke.close()

    assert exit_code == 3
    assert broke.completions == []
    assert "exceeds balance" in capsys.readouterr().out


def test_estimate_only_prints_and_makes_no_completion_call(workspace, fake, capsys):
    exit_code = run(workspace, fake, "--estimate-only")

    output = capsys.readouterr().out
    assert exit_code == 0
    assert fake.completions == []
    assert "models vendor-a/vision, vendor-b/eye" in output
    assert "estimate $0.22  cap $5.00  balance $100.00" in output


def test_estimate_scales_with_runs_and_model_prices(workspace, fake, capsys):
    run(workspace, fake, "--estimate-only", runs="1", models="vendor-a/vision")

    assert "estimate $0.06" in capsys.readouterr().out


def test_unknown_model_slug_exits_2_listing_it(workspace, fake, capsys):
    exit_code = run(workspace, fake, models="vendor-a/vision,ghost/model")

    assert exit_code == 2
    assert "ghost/model" in capsys.readouterr().err
    assert fake.completions == []


def test_missing_api_key_exits_2(workspace, fake, monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY")

    exit_code = run(workspace, fake)

    assert exit_code == 2
    assert "OPENROUTER_API_KEY" in capsys.readouterr().err


def test_base_url_falls_back_to_environment(workspace, fake, monkeypatch):
    monkeypatch.setenv("OPENROUTER_BASE_URL", fake.url)

    exit_code = run_critique.main(
        [
            workspace["rubric"],
            workspace["package"],
            str(workspace["out"]),
            "--models",
            "vendor-a/vision",
            "--runs",
            "1",
            "--cap",
            "5",
        ]
    )

    assert exit_code == 0
    assert fake.completion_models() == ["vendor-a/vision"]


def test_models_can_come_from_a_file_with_comments(workspace, fake, tmp_path):
    models_file = tmp_path / "models.txt"
    models_file.write_text("# vision shortlist\nvendor-a/vision\n\nvendor-b/eye  # second\n")

    exit_code = run(workspace, fake, models=str(models_file), runs="1")

    assert exit_code == 0
    assert sorted(fake.completion_models()) == ["vendor-a/vision", "vendor-b/eye"]


def test_fenced_json_with_leading_prose_is_parsed_and_raw_text_kept(workspace, fake):
    text = 'Here is my critique:\n```json\n{"summary": "ok", "issues": []}\n```\nThanks!'
    fake.on_completion = lambda body: completion(text)

    run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    assert record["parsed"] == {"summary": "ok", "issues": []}
    assert record["raw_text"] == text


def test_invalid_json_keeps_raw_text_with_null_parsed_and_exits_1(workspace, fake, capsys):
    fake.on_completion = lambda body: completion("I think the design is lovely {oops")

    exit_code = run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    stats = json.loads((workspace["out"] / "run_stats.json").read_text())
    assert exit_code == 1
    assert record["parsed"] is None
    assert record["raw_text"] == "I think the design is lovely {oops"
    assert record["ok"] is True
    assert stats["unparsed"] == ["vendor-a/vision#1"]
    assert stats["failed"] == []


def test_empty_reply_is_retried_once_then_recorded(workspace, fake):
    fake.on_completion = lambda body: completion("")

    exit_code = run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    assert exit_code == 1
    assert len(fake.completions) == 2
    assert record["ok"] is False
    assert record["error"] == "empty reply"
    assert record["parsed"] is None


def test_empty_reply_that_recovers_on_retry_succeeds(workspace, fake):
    replies = [completion(""), completion(json.dumps(GOOD_REPLY))]
    fake.on_completion = lambda body: replies.pop(0)

    exit_code = run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    assert exit_code == 0
    assert len(fake.completions) == 2
    assert record["parsed"] == GOOD_REPLY


def test_402_is_recorded_not_crashed_and_not_retried(workspace, fake):
    fake.on_completion = lambda body: Reply(status=402, body={"error": {"message": "no credits"}})

    exit_code = run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    assert exit_code == 1
    assert len(fake.completions) == 1
    assert record["ok"] is False
    assert record["status"] == 402
    assert record["error"] == "insufficient credits (402)"
    assert record["parsed"] is None


def test_connection_reset_is_recorded_after_one_retry(workspace, fake):
    fake.on_completion = lambda body: Reply(drop=True)

    exit_code = run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    assert exit_code == 1
    assert len(fake.completions) == 2
    assert record["ok"] is False
    assert record["status"] is None
    assert record["error"]


def test_5xx_is_retried_once_and_can_recover(workspace, fake):
    replies = [Reply(status=503, body={"error": "busy"}), completion(json.dumps(GOOD_REPLY))]
    fake.on_completion = lambda body: replies.pop(0)

    exit_code = run(workspace, fake, runs="1", models="vendor-a/vision")

    assert exit_code == 0
    assert len(fake.completions) == 2


def test_400_is_recorded_without_retry(workspace, fake):
    fake.on_completion = lambda body: Reply(status=400, body={"error": "bad image"})

    run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    assert len(fake.completions) == 1
    assert record["status"] == 400
    assert record["error"].startswith("HTTP 400")


def test_only_reruns_just_the_named_pair_and_overwrites_its_record(workspace, fake):
    fake.on_completion = lambda body: Reply(status=402, body={})
    run(workspace, fake, runs="2")
    fake.completions.clear()
    fake.on_completion = lambda body: completion(json.dumps(GOOD_REPLY))

    exit_code = run(workspace, fake, "--only", "vendor-b/eye#2", runs="2")

    rerun = read_record(workspace, "vendor-b__eye__run2.json")
    untouched = read_record(workspace, "vendor-a__vision__run1.json")
    stats = json.loads((workspace["out"] / "run_stats.json").read_text())
    assert exit_code == 1
    assert fake.completion_models() == ["vendor-b/eye"]
    assert rerun["ok"] is True
    assert untouched["ok"] is False
    assert sorted(stats["failed"]) == [
        "vendor-a/vision#1",
        "vendor-a/vision#2",
        "vendor-b/eye#1",
    ]


def test_only_rejects_pairs_outside_the_plan(workspace, fake, capsys):
    exit_code = run(workspace, fake, "--only", "vendor-a/vision#9", runs="2")

    assert exit_code == 2
    assert fake.completions == []
    assert "--only" in capsys.readouterr().err


def test_spend_cap_stops_launching_new_calls(workspace, fake):
    fake.on_completion = lambda body: completion(json.dumps(GOOD_REPLY), cost=10.0)

    exit_code = run(workspace, fake, "--workers", "1", runs="2", cap="5")

    skipped = [
        read_record(workspace, name)
        for name in ("vendor-a__vision__run2.json", "vendor-b__eye__run1.json")
    ]
    assert exit_code == 1
    assert len(fake.completions) == 1
    assert all(record["error"] == "skipped: spend cap reached" for record in skipped)


def test_missing_manifest_exits_2(workspace, fake, capsys):
    Path(workspace["package"], "manifest.json").unlink()

    exit_code = run(workspace, fake)

    assert exit_code == 2
    assert "manifest.json" in capsys.readouterr().err
    assert fake.completions == []


def read_stats(workspace):
    """Load run_stats.json."""
    return json.loads((workspace["out"] / "run_stats.json").read_text())


def test_estimate_only_over_cap_exits_3_without_any_completion_call(workspace, fake, capsys):
    exit_code = run(workspace, fake, "--estimate-only", cap="0.001")

    assert exit_code == 3
    assert fake.completions == []
    assert "exceeds cap" in capsys.readouterr().out


def test_estimate_only_over_balance_exits_3(workspace, capsys):
    broke = FakeOpenRouter(credits=0.01)
    try:
        exit_code = run(workspace, broke, "--estimate-only", cap="50")
    finally:
        broke.close()

    assert exit_code == 3
    assert broke.completions == []


def test_spend_reserves_estimates_before_dispatch():
    spend = run_critique.Spend(limit=1.0)

    assert spend.reserve(0.6)
    assert not spend.reserve(0.6)
    spend.settle(0.6, 0.1)
    assert spend.reserve(0.85)
    assert not spend.reserve(0.1)


def test_parallel_reservations_never_exceed_the_limit():
    spend = run_critique.Spend(limit=3.0)
    granted = []

    def worker():
        granted.append(spend.reserve(1.0))

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(granted) == 3


def test_default_workers_do_not_retry_past_the_cap(workspace, fake):
    first_attempts = threading.Barrier(4)
    calls = []

    def reply(body):
        calls.append(body["model"])
        if len(calls) <= 4:
            first_attempts.wait(10)  # every pair reserves before any cost lands
        return completion("", cost=10.0)

    fake.on_completion = reply

    exit_code = run(workspace, fake, runs="2", cap="5")

    assert exit_code == 1
    assert len(fake.completions) == 4
    records = [
        read_record(workspace, path.name) for path in (workspace["out"] / "records").iterdir()
    ]
    assert all(record["error"] == "empty reply" for record in records)
    assert all(record["cost_usd"] == 10.0 for record in records)


def test_each_record_is_written_when_its_pair_finishes(workspace, fake):
    release = threading.Event()

    def reply(body):
        if body["model"] == "vendor-b/eye":
            release.wait(10)
        return completion(json.dumps(GOOD_REPLY))

    fake.on_completion = reply
    thread = threading.Thread(target=run, args=(workspace, fake), kwargs={"runs": "1"})
    thread.start()
    fast = workspace["out"] / "records" / "vendor-a__vision__run1.json"
    deadline = time.monotonic() + 10
    while not fast.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    finished_early = fast.exists()
    release.set()
    thread.join()

    assert finished_early
    assert (workspace["out"] / "records" / "vendor-b__eye__run1.json").exists()


def test_truncated_body_becomes_an_error_record_and_the_batch_continues(
    workspace, fake, monkeypatch
):
    real = run_critique.request_json

    def flaky(url, api_key, body=None, timeout=60):
        if body and body["model"] == "vendor-a/vision":
            raise http.client.IncompleteRead(b"par")
        return real(url, api_key, body, timeout)

    monkeypatch.setattr(run_critique, "request_json", flaky)

    exit_code = run(workspace, fake, runs="1")

    broken = read_record(workspace, "vendor-a__vision__run1.json")
    fine = read_record(workspace, "vendor-b__eye__run1.json")
    assert exit_code == 1
    assert broken["ok"] is False
    assert "IncompleteRead" in broken["error"]
    assert fine["ok"] is True


def test_request_json_returns_http_exceptions_as_errors(monkeypatch):
    def broken(*args, **kwargs):
        raise http.client.BadStatusLine("garbage")

    monkeypatch.setattr(run_critique.urllib.request, "urlopen", broken)

    result = run_critique.request_json("http://127.0.0.1:1/x", "key")

    assert result.status is None
    assert result.error and "BadStatusLine" in result.error


def test_unexpected_exception_in_a_pair_becomes_an_error_record(workspace, fake, monkeypatch):
    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(run_critique, "attempt_with_retry", explode)

    exit_code = run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    assert exit_code == 1
    assert record["error"] == "RuntimeError: boom"


def test_cost_is_summed_across_retry_attempts(workspace, fake):
    replies = [completion("", cost=0.25), completion(json.dumps(GOOD_REPLY), cost=0.5)]
    fake.on_completion = lambda body: replies.pop(0)

    run(workspace, fake, runs="1", models="vendor-a/vision")

    record = read_record(workspace, "vendor-a__vision__run1.json")
    assert record["cost_usd"] == 0.75
    assert read_stats(workspace)["total_cost_usd"] == 0.75


@pytest.mark.parametrize("status", [408, 429])
def test_408_and_429_are_retried_after_a_pause(workspace, fake, monkeypatch, status):
    pauses = []
    monkeypatch.setattr(run_critique, "pause", pauses.append)
    replies = [
        Reply(status=status, body={"error": "slow down"}),
        completion(json.dumps(GOOD_REPLY)),
    ]
    fake.on_completion = lambda body: replies.pop(0)

    exit_code = run(workspace, fake, runs="1", models="vendor-a/vision")

    assert exit_code == 0
    assert len(fake.completions) == 2
    assert pauses == [run_critique.RETRY_DELAY_SECONDS]


def test_retries_only_once(workspace, fake):
    fake.on_completion = lambda body: Reply(status=429, body={"error": "slow"})

    run(workspace, fake, runs="1", models="vendor-a/vision")

    assert len(fake.completions) == 2
    assert read_record(workspace, "vendor-a__vision__run1.json")["status"] == 429


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('Per {schema} here: {"issues": []}', {"issues": []}),
        ('<think>use {x} and {"issues": [9]}</think>{"issues": [1]}', {"issues": [1]}),
        ('<think>use {x}</think>{"a": 1}', None),
        ('{} then {"issues": [1]}', {"issues": [1]}),
        ('{"a": 1} {"b": 2}', None),
        ('{"issues": [{"criterion": "Contrast", "score": 2}', None),
        (
            '```json\n{"issues": [2], "nested": {"issues": 3}}\n```',
            {"issues": [2], "nested": {"issues": 3}},
        ),
        ("no braces", None),
        ("{broken", None),
        ("[1, 2]", None),
    ],
)
def test_extract_json_finds_the_critique_object(text, expected):
    assert run_critique.extract_json(text) == expected


def test_existing_records_are_refused_without_only_or_force(workspace, fake, capsys):
    run(workspace, fake, runs="1")
    before = len(fake.completions)

    exit_code = run(workspace, fake, runs="1")

    assert exit_code == 2
    assert len(fake.completions) == before
    assert "--force" in capsys.readouterr().err


def test_force_overwrites_existing_records(workspace, fake):
    run(workspace, fake, runs="1")
    fake.completions.clear()

    exit_code = run(workspace, fake, "--force", runs="1")

    assert exit_code == 0
    assert len(fake.completions) == 2


def test_stale_records_for_dropped_models_stay_out_of_the_summary(workspace, fake):
    run(workspace, fake, runs="1")

    exit_code = run(workspace, fake, "--force", runs="1", models="vendor-a/vision")

    stats = read_stats(workspace)
    assert exit_code == 0
    assert stats["runs"] == 1
    assert stats["total_cost_usd"] == 0.01


def test_summary_covers_unrerun_pairs_from_earlier_records(workspace, fake):
    run(workspace, fake, runs="1")
    fake.completions.clear()

    run(workspace, fake, "--only", "vendor-b/eye#1", runs="1")

    assert fake.completion_models() == ["vendor-b/eye"]
    assert read_stats(workspace)["runs"] == 2


def test_failure_hint_names_failed_pairs_only_when_something_failed(workspace, fake, capsys):
    run(workspace, fake, runs="1", models="vendor-a/vision")
    assert "--only" not in capsys.readouterr().out

    fake.on_completion = lambda body: Reply(status=402, body={})
    run(workspace, fake, "--force", runs="1", models="vendor-a/vision")
    out = capsys.readouterr().out
    assert "rerun failures with --only vendor-a/vision#1" in out
    assert "a#1" not in out


def test_estimate_grows_with_text_size_and_images(workspace, fake, capsys):
    run(workspace, fake, "--estimate-only", runs="1", models="vendor-a/vision")
    base = capsys.readouterr().out
    Path(workspace["package"], "tokens.json").write_text("x" * 800_000)

    run(workspace, fake, "--estimate-only", runs="1", models="vendor-a/vision")

    assert "estimate $0.06" in base
    assert "estimate $0.22" in capsys.readouterr().out


def test_estimate_prompt_tokens_floors_at_40k_and_counts_images():
    small = [{"type": "text", "text": "hi"}]
    images = [{"type": "image_url", "image_url": {"url": "data:x"}}] * 30
    long_text = [{"type": "text", "text": "y" * 400_000}]

    assert run_critique.estimate_prompt_tokens(small) == 40000
    assert run_critique.estimate_prompt_tokens(small + images) == 30 * 1600
    assert run_critique.estimate_prompt_tokens(images) == 48000
    assert run_critique.estimate_prompt_tokens(long_text) == 100000


@pytest.mark.parametrize("pricing", [None, {"prompt": "-1", "completion": "-1"}, {"prompt": None}])
def test_null_or_negative_pricing_is_a_usage_error_naming_the_model(
    workspace, fake, capsys, pricing
):
    fake.models_payload = [{"id": "vendor-a/vision", "pricing": pricing}]

    exit_code = run(workspace, fake, runs="1", models="vendor-a/vision")

    assert exit_code == 2
    assert "vendor-a/vision" in capsys.readouterr().err
    assert fake.completions == []
