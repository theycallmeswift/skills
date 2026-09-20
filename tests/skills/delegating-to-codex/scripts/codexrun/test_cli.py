"""Tests for the implement job lifecycle: start, status, result, cancel, and resume."""

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
from support.codex import pid_alive, run_cli

JOB_FILES = ("prompt.md", "events.jsonl", "stderr.log", "last.md", "meta.json")

TOP_LEVEL_HELP = """usage: codex_run.py [-h] {preflight,start,status,result,cancel,_worker} ...

Delegate tasks to codex exec as jobs.

positional arguments:
  {preflight,start,status,result,cancel,_worker}
    preflight           check codex is installed and logged in
    start               start an implement or review job
    status              list jobs for this worktree
    result              show a job's final message and usage
    cancel              stop a running job

options:
  -h, --help            show this help message and exit
"""

START_HELP = """usage: codex_run.py start [-h] --effort {none,minimal,low,medium,high,xhigh}
                          [--model MODEL] [--tier TIER] [--network]
                          [--brief FILE] [--context FILE] [--risks FILE]
                          [--rules FILE] [--report FILE] [--base BASE]
                          [--resume JOB_ID] [--wait] [--cd DIR]
                          {implement,review}

positional arguments:
  {implement,review}

options:
  -h, --help            show this help message and exit
  --effort {none,minimal,low,medium,high,xhigh}
  --model MODEL
  --tier TIER           service_tier
  --network             allow network (implement)
  --brief FILE
  --context FILE
  --risks FILE
  --rules FILE
  --report FILE
  --base BASE           review: diff against merge-base with REF
  --resume JOB_ID       implement: continue that job's thread
  --wait                run in the foreground
  --cd DIR              worktree (default: $PROJECT_ROOT or cwd)
"""


def test_help_text_is_unchanged():
    top_level = run_cli("--help")
    start = run_cli("start", "--help")

    assert (top_level.returncode, top_level.stdout, top_level.stderr) == (0, TOP_LEVEL_HELP, "")
    assert (start.returncode, start.stdout, start.stderr) == (0, START_HELP, "")


def test_implement_wait_runs_codex_and_records_the_job(ws, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1")

    result = ws.start("implement", "--risks", ws.risks, "--wait", effort="high")

    assert result.return_code == 0
    assert "STATUS: DONE" in result.stdout
    assert "tokens: in 100 (cached 40), out 7, reasoning 3" in result.stdout
    meta = ws.meta(result.job_id)
    assert meta["status"] == "completed" and meta["exit_code"] == 0
    assert meta["mode"] == "implement"
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


def test_background_status_reports_running_job(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "1.5")
    started = ws.start("implement")
    ws.wait_until(lambda: ws.calls())

    status = ws.run("status")

    assert started.return_code == 0
    assert str(ws.jobs / started.job_id) in started.stdout
    assert status.return_code == 0
    assert started.job_id in status.stdout and "running" in status.stdout

    ws.wait_done(started.job_id)


def test_running_result_uses_running_exit_code(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "1.5")
    started = ws.start("implement")
    ws.wait_until(lambda: ws.calls())

    result = ws.run("result", started.job_id)

    assert result.return_code == 4
    assert "still running" in result.stdout

    ws.wait_done(started.job_id)


def test_completed_result_prints_message_and_usage(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "0.1")
    started = ws.start("implement")
    ws.wait_done(started.job_id)

    result = ws.run("result", "last")

    assert result.return_code == 0
    assert "completed" in result.stdout
    assert "STATUS: DONE" in result.stdout
    assert "tokens: in 100" in result.stdout


def test_result_json(ws):
    job_id = ws.start("implement", "--wait").job_id
    result = ws.run("result", job_id, "--json")

    assert result.return_code == 0
    data = json.loads(result.stdout)
    assert data["id"] == job_id
    assert data["last_message"].startswith("STATUS: DONE")
    assert data["usage"]["input_tokens"] == 100


def test_failed_job(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_RC", "7")

    result = ws.start("implement", "--wait")

    assert result.return_code == 1
    meta = ws.meta(result.job_id)
    assert meta["status"] == "failed" and meta["exit_code"] == 7


def test_result_without_usage(ws):
    job_id = ws.start("implement", "--wait").job_id
    ws.edit_meta(job_id, usage=None)

    result = ws.run("result", job_id)

    assert "tokens: unavailable" in result.stdout


def test_result_for_unknown_job(ws):
    assert ws.run("result", "nope").return_code == 2


def test_cancel_kills_codex_and_keeps_its_edits(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_SLEEP", "30")
    job_id = ws.start("implement").job_id
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
    job_id = ws.start("implement", "--wait").job_id
    exited = subprocess.Popen(["true"])
    exited.wait()
    ws.edit_meta(job_id, status="running", pid=exited.pid, finished_at=None)

    ws.run("status")

    assert ws.meta(job_id)["status"] == "failed"


def test_status_shows_only_the_current_sessions_jobs(ws, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    first = ws.start("implement", "--wait").job_id
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s2")
    second = ws.start("implement", "--wait").job_id

    result = ws.run("status")

    assert second in result.stdout
    assert first not in result.stdout


def test_status_all_shows_other_sessions_jobs(ws, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    first = ws.start("implement", "--wait").job_id
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s2")
    second = ws.start("implement", "--wait").job_id

    result = ws.run("status", "--all")

    assert first in result.stdout
    assert second in result.stdout


def test_status_json_orders_jobs_newest_first(ws, monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s1")
    first = ws.start("implement", "--wait").job_id
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "s2")
    second = ws.start("implement", "--wait").job_id

    result = ws.run("status", "--all", "--json")

    newest_first = [job["id"] for job in json.loads(result.stdout)]
    assert newest_first == [second, first]


def test_status_surfaces_corrupt_job_metadata_id(ws):
    job_id = ws.start("implement", "--wait").job_id
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
    first = ws.start("implement", "--wait").job_id
    ws.write("a.py", "x = 2\n")  # a dirty worktree is expected on a fix round
    fixes = ws.write_input("fixes.md", "Fix finding 1: add a test.\n")

    result = ws.start("implement", "--resume", first, "--wait", effort="medium", brief=fixes)

    assert result.return_code == 0
    call = ws.calls()[-1]
    assert call["argv"][:3] == ["exec", "resume", "thread-first"]
    assert 'sandbox_mode="workspace-write"' in call["argv"]
    assert Path(call["cwd"]).resolve() == ws.repo.resolve()
    assert "Fix finding 1" in call["stdin"]
    assert "=== TASK TEMPLATE ===" not in call["stdin"]
    assert ws.meta(result.job_id)["resumed_from"] == first


def test_resume_needs_a_recorded_thread(ws):
    first = ws.start("implement", "--wait").job_id
    ws.edit_meta(first, thread_id=None)
    calls_before = len(ws.calls())

    result = ws.start("implement", "--resume", first)

    assert result.return_code == 2 and "thread" in result.stderr
    assert len(ws.calls()) == calls_before


def test_start_prunes_old_jobs(ws):
    for index in range(55):
        old = ws.jobs / f"20000101-0000{index:02d}-implement-0000"
        old.mkdir(parents=True)
        (old / "meta.json").write_text(json.dumps({"created_at": f"2000-01-01T00:00:{index:02d}"}))

    job_id = ws.start("implement", "--wait").job_id

    remaining = {job_dir.name for job_dir in ws.jobs.iterdir()}
    assert len(remaining) == 50
    assert job_id in remaining
