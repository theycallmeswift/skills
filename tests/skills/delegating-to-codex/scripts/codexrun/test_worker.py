"""Tests for worker process execution and launch failures."""

from __future__ import annotations

from unittest.mock import Mock

from codexrun import worker
from codexrun.state import now, read_meta, write_meta
from support.codex import job_meta


def test_worker_records_a_process_launch_error(tmp_path, monkeypatch):
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (job_dir / "prompt.md").write_text("Do the task.\n")
    write_meta(job_dir, job_meta(worktree=str(tmp_path), argv=["missing-codex"]))
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
    write_meta(
        job_dir,
        job_meta(
            id="launch-error",
            worktree=str(ws.repo),
            argv=["missing-codex"],
            status="failed",
            exit_code=worker.CODEX_LAUNCH_ERROR_EXIT_CODE,
            finished_at=now(),
            error="failed to run codex: binary vanished",
        ),
    )

    result = ws.run("result", "launch-error")

    assert result.return_code == 1
    assert "failed to run codex: binary vanished" in result.stdout
