"""Tests for the job lifecycle: start, status, result, cancel, and resume."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock

import pytest
from codexrun import cli
from codexrun.result import RESULT_MAX_BYTES
from codexrun.start import INPUTS
from support.codex import pid_alive, run_cli

JOB_FILES = ("prompt.md", "events.jsonl", "stderr.log", "last.md", "meta.json")

COMMANDS = ("preflight", "start", "status", "result", "cancel")
START_FLAGS = (
    "--effort",
    "--template",
    "--model",
    "--tier",
    *(f"--{name}" for name in INPUTS),
    "--sandbox",
    "--schema",
    "--diff",
    "--base",
    "--network",
    "--resume",
    "--gate",
    "--wait",
    "--cd",
)


def unwrapped(text: str) -> str:
    """Collapse argparse's terminal-width wrapping so assertions read one flag at a time."""
    return " ".join(text.split())


def test_top_level_help_lists_every_command():
    result = run_cli("--help")

    assert (result.returncode, result.stderr) == (0, "")
    help_text = unwrapped(result.stdout)
    assert all(command in help_text for command in COMMANDS)


def test_start_help_lists_every_flag_and_its_defaults():
    result = run_cli("start", "--help")

    assert (result.returncode, result.stderr) == (0, "")
    help_text = unwrapped(result.stdout)
    assert all(flag in help_text for flag in START_FLAGS)
    assert "--sandbox {read-only,workspace-write}" in help_text
    assert "default: the resumed job's, else workspace-write" in help_text
    assert "inherited on --resume (default: the review schema)" in help_text
    assert "implement, review, or a task template file" in help_text


def test_wait_runs_codex_and_records_the_job(ws, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")

    result = ws.start("--template", "implement", "--risks", ws.risks, "--wait", effort="high")

    assert result.return_code == 0
    assert "STATUS: DONE" in result.stdout
    assert "tokens: in 100 (cached 40), out 7, reasoning 3" in result.stdout
    meta = ws.meta(result.job_id)
    assert meta["status"] == "completed" and meta["exit_code"] == 0
    assert meta["template"] == "implement"
    assert meta["thread_id"] == "thread-abc"
    assert meta["session_id"] == "sess-1"
    assert meta["usage"]["output_tokens"] == 7
    assert meta["finished_at"]

    (call,) = ws.calls()
    assert call["argv"][:5] == ["exec", "--sandbox", "workspace-write", "--cd", str(ws.repo)]
    assert "model_reasoning_effort=high" in call["argv"]
    assert Path(call["cwd"]).resolve() == ws.repo.resolve()
    assert "=== TASK TEMPLATE ===" in call["stdin"]
    assert "Make x equal 2." in call["stdin"]
    assert "R1: x must stay an int." in call["stdin"]

    job_dir = ws.jobs / result.job_id
    assert all((job_dir / name).exists() for name in JOB_FILES)
    assert not job_dir.is_relative_to(ws.repo)


def test_start_and_status_name_the_template(ws):
    started = ws.start("--template", "review", "--sandbox", "read-only", "--wait")

    status = ws.run("status")

    assert "started (review)" in started.stdout
    assert "TEMPLATE" in status.stdout
    assert "review" in status.stdout.splitlines()[-1]


def test_status_keeps_a_long_template_path_inside_its_column(ws):
    template = ws.write_input("a-very-long-house-style-template.md", "House style.\n")
    ws.start("--template", template, "--wait")

    status = ws.run("status")

    _job_id, template_cell, job_status, _created = status.stdout.splitlines()[-1].split()
    assert len(template_cell) <= cli.TEMPLATE_COLUMN
    assert job_status == "completed"


def test_background_status_reports_running_job(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "1.5")
    started = ws.start()
    ws.wait_until(lambda: ws.calls())

    status = ws.run("status")

    assert started.return_code == 0
    assert str(ws.jobs / started.job_id) in started.stdout
    assert status.return_code == 0
    assert started.job_id in status.stdout and "running" in status.stdout

    ws.wait_done(started.job_id)


def test_running_result_uses_running_exit_code(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "1.5")
    started = ws.start()
    ws.wait_until(lambda: ws.calls())

    result = ws.run("result", started.job_id)

    assert result.return_code == 4
    assert "still running" in result.stdout

    ws.wait_done(started.job_id)


def test_completed_result_prints_message_and_usage(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "0.1")
    started = ws.start()
    ws.wait_done(started.job_id)

    result = ws.run("result", "last")

    assert result.return_code == 0
    assert "completed" in result.stdout
    assert "STATUS: DONE" in result.stdout
    assert "tokens: in 100" in result.stdout


def test_result_json(ws):
    job_id = ws.start("--wait").job_id
    result = ws.run("result", job_id, "--json")

    assert result.return_code == 0
    data = json.loads(result.stdout)
    assert data["id"] == job_id
    assert data["last_message"].startswith("STATUS: DONE")
    assert data["usage"]["input_tokens"] == 100


def test_result_prints_a_short_message_unchanged(ws):
    job_id = ws.start("--wait").job_id

    result = ws.run("result", job_id)

    header, message, usage = result.stdout.splitlines()
    assert header.endswith("completed (exit 0)")
    assert message == "STATUS: DONE"
    assert usage.startswith("tokens:")


def test_result_truncates_a_long_message_and_points_at_the_file(ws):
    job_id = ws.start("--wait").job_id
    message_path = ws.jobs / job_id / "last.md"
    message_path.write_text("x" * (200 * 1024))

    result = ws.run("result", job_id)

    body = result.stdout.splitlines()[1]
    assert len(body.encode("utf-8")) <= RESULT_MAX_BYTES
    assert f"... truncated (200 KB); full message: {message_path}" in result.stdout


def test_result_truncation_never_splits_a_multibyte_character(ws):
    job_id = ws.start("--wait").job_id
    # Three bytes per character, so the cap lands inside one.
    (ws.jobs / job_id / "last.md").write_text("\u20ac" * 20_000)

    result = ws.run("result", job_id)

    lines = result.stdout.splitlines()
    body, pointer = lines[1], lines[-2]
    assert result.return_code == 0
    assert pointer.startswith("... truncated")
    assert body == "\u20ac" * len(body)


def test_result_truncation_ends_on_a_whole_line(ws):
    job_id = ws.start("--wait").job_id
    (ws.jobs / job_id / "last.md").write_text(("a" * 79 + "\n") * 500)

    result = ws.run("result", job_id)

    lines = result.stdout.splitlines()
    body, pointer = lines[1:-2], lines[-2]
    assert pointer.startswith("... truncated")
    assert body == ["a" * 79] * (RESULT_MAX_BYTES // 80)


def test_result_truncation_keeps_the_head_when_no_line_break_is_near_the_cut(ws):
    job_id = ws.start("--wait").job_id
    (ws.jobs / job_id / "last.md").write_text("header line\n" + "x" * (200 * 1024))

    result = ws.run("result", job_id)

    body = result.stdout.splitlines()[1:-2]
    assert body == ["header line", "x" * (RESULT_MAX_BYTES - len("header line\n"))]


def test_result_truncation_keeps_a_decimal_when_the_cut_would_round_away(ws):
    job_id = ws.start("--wait").job_id
    (ws.jobs / job_id / "last.md").write_text("x" * (RESULT_MAX_BYTES + 1))

    result = ws.run("result", job_id)

    assert "... truncated (16.0 KB);" in result.stdout


def test_result_points_at_no_spill_file_when_the_message_was_only_whitespace(ws):
    job_id = ws.start("--wait").job_id
    (ws.jobs / job_id / "last.md").write_text(" " * (200 * 1024))

    result = ws.run("result", job_id)

    assert "(no final message)" in result.stdout
    assert "truncated" not in result.stdout


def test_result_json_truncates_and_names_the_spill_file(ws):
    job_id = ws.start("--wait").job_id
    message_path = ws.jobs / job_id / "last.md"
    message_path.write_text("x" * (200 * 1024))

    result = ws.run("result", job_id, "--json")

    data = json.loads(result.stdout)
    assert len(data["last_message"].encode("utf-8")) <= RESULT_MAX_BYTES
    assert data["last_message_truncated"] is True
    assert data["last_message_path"] == str(message_path)


def test_result_json_omits_the_truncation_keys_for_a_short_message(ws):
    job_id = ws.start("--wait").job_id

    result = ws.run("result", job_id, "--json")

    data = json.loads(result.stdout)
    assert "last_message_truncated" not in data
    assert "last_message_path" not in data


def test_result_points_at_stderr_instead_of_quoting_it(ws):
    job_id = ws.start("--wait").job_id
    (ws.jobs / job_id / "last.md").write_text("")
    stderr_path = ws.jobs / job_id / "stderr.log"
    stderr_path.write_text("thread 'main' panicked: DISTINCTIVE-TRACE\n")

    result = ws.run("result", job_id)

    assert f"(no final message); stderr: {stderr_path}" in result.stdout
    assert "DISTINCTIVE-TRACE" not in result.stdout


def test_result_without_a_stderr_log_reports_only_the_missing_message(ws):
    job_id = ws.start("--wait").job_id
    (ws.jobs / job_id / "last.md").write_text("")
    (ws.jobs / job_id / "stderr.log").unlink()

    result = ws.run("result", job_id)

    assert "(no final message)" in result.stdout
    assert "stderr" not in result.stdout


def test_result_prefers_a_recorded_launch_error_over_the_stderr_pointer(ws):
    job_id = ws.start("--wait").job_id
    (ws.jobs / job_id / "last.md").write_text("")
    (ws.jobs / job_id / "stderr.log").write_text("noise\n")
    ws.edit_meta(job_id, error="failed to run codex: [Errno 2] No such file or directory")

    result = ws.run("result", job_id)

    assert "failed to run codex" in result.stdout
    assert "no final message" not in result.stdout


def test_failed_job(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_RC", "7")

    result = ws.start("--wait")

    assert result.return_code == 1
    meta = ws.meta(result.job_id)
    assert meta["status"] == "failed" and meta["exit_code"] == 7


def test_result_without_usage(ws):
    job_id = ws.start("--wait").job_id
    ws.edit_meta(job_id, usage=None)

    result = ws.run("result", job_id)

    assert "tokens: unavailable" in result.stdout


def test_result_for_unknown_job(ws):
    assert ws.run("result", "nope").return_code == 2


def test_cancel_kills_codex_and_keeps_its_edits(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "30")
    job_id = ws.start().job_id
    ws.wait_until(lambda: ws.calls() and ws.meta(job_id).get("pid"), timeout=10)
    edit = ws.write("new.txt", "partial edit\n")
    codex_pid = ws.calls()[0]["pid"]

    result = ws.run("cancel", job_id)

    assert result.return_code == 0 and "git status" in result.stdout
    assert ws.meta(job_id)["status"] == "cancelled"
    try:
        ws.wait_until(lambda: not pid_alive(codex_pid), timeout=5)
    except AssertionError:
        os.kill(codex_pid, signal.SIGKILL)
        raise AssertionError("codex process survived cancel") from None
    time.sleep(0.2)  # a worker that survived would overwrite the status by now
    assert ws.meta(job_id)["status"] == "cancelled"
    assert edit.read_text() == "partial edit\n"


def test_status_marks_a_job_with_a_dead_worker_failed(ws):
    job_id = ws.start("--wait").job_id
    exited = subprocess.Popen(["true"])
    exited.wait()
    ws.edit_meta(job_id, status="running", pid=exited.pid, finished_at=None)

    ws.run("status")

    assert ws.meta(job_id)["status"] == "failed"


def test_status_shows_only_the_current_sessions_jobs(ws, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    first = ws.start("--wait").job_id
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s2")
    second = ws.start("--wait").job_id

    result = ws.run("status")

    assert second in result.stdout
    assert first not in result.stdout


def test_status_all_shows_other_sessions_jobs(ws, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    first = ws.start("--wait").job_id
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s2")
    second = ws.start("--wait").job_id

    result = ws.run("status", "--all")

    assert first in result.stdout
    assert second in result.stdout


def test_status_json_orders_jobs_newest_first(ws, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    first = ws.start("--wait").job_id
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s2")
    second = ws.start("--wait").job_id

    result = ws.run("status", "--all", "--json")

    newest_first = [job["id"] for job in json.loads(result.stdout)]
    assert newest_first == [second, first]


def test_status_surfaces_corrupt_job_metadata_id(ws):
    job_id = ws.start("--wait").job_id
    (ws.jobs / job_id / "meta.json").write_text("not json")

    result = ws.run("status")

    assert result.return_code == 2
    assert job_id in result.stderr


def test_stop_worker_ignores_an_already_exited_process(monkeypatch):
    kill_process_group = Mock(side_effect=ProcessLookupError)
    monkeypatch.setattr(os, "killpg", kill_process_group)

    cli._stop_worker(123)

    kill_process_group.assert_called_once_with(123, signal.SIGTERM)


def test_stop_worker_surfaces_permission_errors(monkeypatch):
    permission_error = PermissionError("denied")
    monkeypatch.setattr(os, "killpg", Mock(side_effect=permission_error))

    with pytest.raises(PermissionError, match="denied"):
        cli._stop_worker(123)


def test_resume_continues_the_recorded_thread(ws, monkeypatch):
    monkeypatch.setenv("FAKE_THREAD_ID", "thread-first")
    first = ws.start("--wait").job_id
    ws.write("a.py", "x = 2\n")  # a dirty worktree is expected on a fix round
    fixes = ws.write_input("fixes.md", "Fix finding 1: add a test.\n")

    result = ws.start("--resume", first, "--wait", effort="medium", brief=fixes)

    assert result.return_code == 0
    call = ws.calls()[-1]
    assert call["argv"][:3] == ["exec", "resume", "thread-first"]
    assert 'sandbox_mode="workspace-write"' in call["argv"]
    assert Path(call["cwd"]).resolve() == ws.repo.resolve()
    assert "Fix finding 1" in call["stdin"]
    assert "=== TASK TEMPLATE ===" not in call["stdin"]
    assert ws.meta(result.job_id)["resumed_from"] == first


def test_resume_needs_a_recorded_thread(ws):
    first = ws.start("--wait").job_id
    ws.edit_meta(first, thread_id=None)
    calls_before = len(ws.calls())

    result = ws.start("--resume", first)

    assert result.return_code == 2 and "thread" in result.stderr
    assert len(ws.calls()) == calls_before


def test_start_prunes_old_jobs(ws):
    for index in range(55):
        old = ws.jobs / f"20000101-0000{index:02d}-job-0000"
        old.mkdir(parents=True)
        (old / "meta.json").write_text(json.dumps({"created_at": f"2000-01-01T00:00:{index:02d}"}))

    job_id = ws.start("--wait").job_id

    remaining = {job_dir.name for job_dir in ws.jobs.iterdir()}
    assert len(remaining) == 50
    assert job_id in remaining
