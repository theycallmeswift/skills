"""Contract between agent_run argv and the real Codex CLI.

Runs in the normal suite: it needs no credentials and no internet, only the `codex` binary and a
loopback port. A missing binary fails rather than skips, so the contract cannot silently rot.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from support.codex_contract import (
    RESUMED_USAGE,
    SCHEMA,
    USAGE,
    Stub,
    config,
    git,
    job_dir,
    meta,
    serve_stub,
    start,
)


@dataclass
class ContractWorkspace:
    """Repository, isolated Codex configuration, and active API stub for a contract test."""

    repo: Path
    inputs: Path
    state: Path
    codex_home: Path
    env: dict[str, str]
    stub: Stub
    port: int


@pytest.fixture
def contract_workspace(tmp_path: Path) -> Iterator[ContractWorkspace]:
    """Build a clean repository and local Responses API stub."""
    if not shutil.which("codex"):
        pytest.fail("`codex` is not on PATH; install the Codex CLI (see docs/development.md)")

    repo = tmp_path / "repo"
    inputs = tmp_path / "inputs"
    state = tmp_path / "state"
    codex_home = tmp_path / "codex-home"
    repo.mkdir()
    inputs.mkdir()
    codex_home.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "commit", "-q", "--allow-empty", "-m", "init")

    with serve_stub(repo) as (stub, port):
        (codex_home / "config.toml").write_text(config(port))
        (codex_home / "auth.json").write_text('{"OPENAI_API_KEY":"sk-dummy-not-real"}\n')
        env: dict[str, str] = dict(os.environ)
        env.update(
            {
                "CLAUDE_PLUGIN_DATA": str(state),
                "CODEX_HOME": str(codex_home),
                "STUB_API_KEY": "stub-key",
            }
        )
        env.pop("CODEX_THREAD_ID", None)

        yield ContractWorkspace(repo, inputs, state, codex_home, env, stub, port)


def test_stub_sends_events_in_order_with_total_usage(tmp_path):
    stub = Stub(tmp_path)

    payload = stub.reply({})

    events = [
        json.loads(line.removeprefix("data: "))
        for line in payload.decode().splitlines()
        if line.startswith("data: ")
    ]
    assert [event["type"] for event in events] == [
        "response.created",
        "response.output_item.done",
        "response.completed",
    ]
    usage = events[-1]["response"]["usage"]
    assert usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"]


def test_real_cli_accepts_workspace_write_argv(contract_workspace):
    brief = contract_workspace.inputs / "implement.md"
    brief.write_text("Create hello.txt containing exactly: hi\n")

    result, job_id = start(
        contract_workspace.env,
        contract_workspace.repo,
        brief,
        "--tier",
        "flex",
        "--network",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (contract_workspace.repo / "hello.txt").read_text() == "hi\n"
    assert meta(contract_workspace.state, job_id)["usage"] == USAGE


def test_real_cli_resume_reuses_the_thread(contract_workspace):
    initial_brief = contract_workspace.inputs / "implement.md"
    initial_brief.write_text("Create hello.txt containing exactly: hi\n")
    initial_result, initial_id = start(
        contract_workspace.env,
        contract_workspace.repo,
        initial_brief,
    )
    assert initial_result.returncode == 0, initial_result.stdout + initial_result.stderr
    initial_meta = meta(contract_workspace.state, initial_id)
    resume_brief = contract_workspace.inputs / "resume.md"
    resume_brief.write_text("Also create bye.txt containing exactly: bye\n")

    result, resumed_id = start(
        contract_workspace.env,
        contract_workspace.repo,
        resume_brief,
        "--resume",
        initial_id,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    resumed_meta = meta(contract_workspace.state, resumed_id)
    assert resumed_meta["thread_id"] == initial_meta["thread_id"]
    assert resumed_meta["usage"] == RESUMED_USAGE


def test_real_cli_read_only_run_sends_the_schema(contract_workspace):
    (contract_workspace.repo / "hello.txt").write_text("hi\n")
    brief = contract_workspace.inputs / "review.md"
    brief.write_text("Review the new file.\n")

    result, job_id = start(
        contract_workspace.env,
        contract_workspace.repo,
        brief,
        "--template",
        "review",
        "--sandbox",
        "read-only",
        "--schema",
        "--diff",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert meta(contract_workspace.state, job_id)["usage"] == USAGE
    review_request = next(
        request
        for request in contract_workspace.stub.requests
        if request.get("text", {}).get("format", {}).get("type") == "json_schema"
    )
    assert review_request["text"]["format"]["schema"] == json.loads(SCHEMA.read_text())


def test_real_cli_strict_config_rejects_an_unknown_key(contract_workspace):
    config_path = contract_workspace.codex_home / "config.toml"
    config_path.write_text(
        config(
            contract_workspace.port,
            "definitely_not_a_real_codex_key = true",
        )
    )
    (contract_workspace.repo / "hello.txt").write_text("hi\n")
    brief = contract_workspace.inputs / "review.md"
    brief.write_text("Review the new file.\n")

    result, job_id = start(
        contract_workspace.env,
        contract_workspace.repo,
        brief,
        "--sandbox",
        "read-only",
    )

    assert result.returncode != 0
    assert meta(contract_workspace.state, job_id)["status"] == "failed"
    stderr = (job_dir(contract_workspace.state, job_id) / "stderr.log").read_text()
    assert "definitely_not_a_real_codex_key" in stderr
