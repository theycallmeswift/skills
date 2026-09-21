"""Tests for the post-run gate: a check on the delegate's work that the delegate never runs."""

from __future__ import annotations

from unittest.mock import Mock

from codexrun import worker
from codexrun.state import read_meta, write_meta
from support.codex import job_meta


def test_a_passing_gate_is_recorded_and_summarized_in_one_line(ws):
    job_id = ws.start("--gate", "true").job_id
    ws.wait_done(job_id)

    result = ws.run("result", job_id)

    assert result.return_code == 0
    assert "gate: passed - true" in result.stdout
    assert ws.meta(job_id)["gate"] == {"command": "true", "status": "passed", "exit_code": 0}


def test_a_failing_gate_exits_five_without_touching_the_delegates_own_status(ws):
    job_id = ws.start("--gate", "exit 3").job_id
    ws.wait_done(job_id)

    result = ws.run("result", job_id)

    assert result.return_code == 5
    log_path = ws.jobs / job_id / "gate.log"
    assert f"gate: failed (exit 3) - exit 3; output: {log_path}" in result.stdout
    assert result.stdout.isascii()  # a terminal on an ascii locale still gets the bad news
    meta = ws.meta(job_id)
    assert meta["gate"] == {"command": "exit 3", "status": "failed", "exit_code": 3}
    assert meta["status"] == "completed"
    assert meta["exit_code"] == 0


def test_gate_output_goes_to_the_log_and_never_to_the_result(ws):
    noise = ws.write_input("noise.txt", "tests-are-noisy\n")
    job_id = ws.start("--gate", f"cat {noise} >&2").job_id
    ws.wait_done(job_id)

    result = ws.run("result", job_id)

    assert "tests-are-noisy" in (ws.jobs / job_id / "gate.log").read_text()
    assert "tests-are-noisy" not in result.stdout


def test_a_failed_delegate_skips_the_gate_without_running_the_command(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_RC", "7")

    result = ws.start("--gate", "touch gate-ran.txt", "--wait")

    assert result.return_code == 1
    assert not (ws.repo / "gate-ran.txt").exists()
    assert ws.meta(result.job_id)["gate"] == {"command": "touch gate-ran.txt", "status": "skipped"}
    assert "gate: skipped (job failed) - touch gate-ran.txt" in result.stdout


def test_a_worker_that_finds_its_job_cancelled_runs_no_gate(tmp_path, monkeypatch):
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "prompt.md").write_text("Do the task.\n")
    # Cancel reaches a worker that has not recorded a pid yet, so nothing kills it:
    # the worker has to notice the status itself.
    write_meta(
        job_dir,
        job_meta(worktree=str(tmp_path), status="cancelled", gate_command="touch gate-ran.txt"),
    )
    codex_exits_clean = Mock(return_value=0)
    monkeypatch.setattr(worker.subprocess, "call", codex_exits_clean)

    worker.run_worker(job_dir)

    assert codex_exits_clean.call_count == 1  # codex ran; the gate never did
    recorded = read_meta(job_dir)
    assert recorded["status"] == "cancelled"
    assert "gate" not in recorded
    assert not (tmp_path / "gate-ran.txt").exists()


def test_a_job_without_a_gate_records_and_prints_none(ws):
    result = ws.start("--wait")

    assert result.return_code == 0
    assert "gate:" not in result.stdout
    meta = ws.meta(result.job_id)
    assert "gate" not in meta
    assert meta["gate_command"] is None


def test_wait_reports_the_gate_alongside_the_delegates_result(ws):
    result = ws.start("--gate", "true", "--wait")

    assert result.return_code == 0
    assert "STATUS: DONE" in result.stdout
    assert "gate: passed - true" in result.stdout


def test_an_errored_gate_exits_five_and_names_the_reason(ws):
    job_id = ws.start("--wait").job_id
    ws.edit_meta(job_id, gate={"command": "make test", "status": "error", "reason": "no shell"})

    result = ws.run("result", job_id)

    assert result.return_code == 5
    assert "gate: error (no shell) - make test" in result.stdout
    assert "gate.log" not in result.stdout


def test_an_unlaunchable_gate_is_recorded_as_an_error(tmp_path, monkeypatch):
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "prompt.md").write_text("Do the task.\n")
    write_meta(
        job_dir,
        job_meta(worktree=str(tmp_path), argv=["fake-codex"], gate_command="make test"),
    )
    codex_succeeds_then_the_gate_cannot_start = Mock(side_effect=[0, OSError("no shell")])
    monkeypatch.setattr(worker.subprocess, "call", codex_succeeds_then_the_gate_cannot_start)

    worker.run_worker(job_dir)

    recorded = read_meta(job_dir)
    assert recorded["gate"] == {"command": "make test", "status": "error", "reason": "no shell"}
    assert recorded["status"] == "completed"
    assert "no shell" in (job_dir / "gate.log").read_text()
