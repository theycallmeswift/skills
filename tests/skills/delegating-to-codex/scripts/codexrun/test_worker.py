"""Tests for worker process execution and launch failures."""

from __future__ import annotations

from unittest.mock import Mock

from codexrun import worker
from codexrun.state import JobMeta, now, read_meta, write_meta


def test_worker_records_a_process_launch_error(tmp_path, monkeypatch):
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "prompt.md").write_text("Do the task.\n")
    meta: JobMeta = {
        "id": "job",
        "template": "implement",
        "worktree": str(tmp_path),
        "argv": ["missing-codex"],
        "pid": None,
        "status": "running",
        "exit_code": None,
        "thread_id": None,
        "usage": None,
        "session_id": None,
        "resumed_from": None,
        "created_at": now(),
        "finished_at": None,
    }
    write_meta(job_dir, meta)
    monkeypatch.setattr(worker.subprocess, "call", Mock(side_effect=OSError("binary vanished")))

    return_code = worker.run_worker(job_dir)

    recorded = read_meta(job_dir)
    assert return_code == worker.CODEX_LAUNCH_ERROR_EXIT_CODE
    assert recorded["status"] == "failed"
    assert recorded["exit_code"] == worker.CODEX_LAUNCH_ERROR_EXIT_CODE
    assert recorded["error"] == "failed to run codex: binary vanished"


def test_result_prints_a_recorded_worker_error(ws):
    job_dir = ws.jobs / "launch-error"
    job_dir.mkdir(parents=True)
    meta: JobMeta = {
        "id": "launch-error",
        "template": "implement",
        "worktree": str(ws.repo),
        "argv": ["missing-codex"],
        "pid": None,
        "status": "failed",
        "exit_code": worker.CODEX_LAUNCH_ERROR_EXIT_CODE,
        "thread_id": None,
        "usage": None,
        "session_id": None,
        "resumed_from": None,
        "created_at": now(),
        "finished_at": now(),
        "error": "failed to run codex: binary vanished",
    }
    write_meta(job_dir, meta)

    result = ws.run("result", "launch-error")

    assert result.return_code == 1
    assert "failed to run codex: binary vanished" in result.stdout
