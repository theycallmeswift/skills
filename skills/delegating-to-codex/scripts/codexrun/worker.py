"""The detached worker: runs one job's `codex` process and records how it ended."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from codexrun import SCRIPT
from codexrun.events import parse_events
from codexrun.state import JobMeta, now, read_meta, write_meta

CODEX_LAUNCH_ERROR_EXIT_CODE = 127


def spawn_worker(job_dir: Path) -> subprocess.Popen[bytes]:
    """Start the worker in its own session so it outlives the caller and cancel can kill it."""
    return subprocess.Popen(
        [sys.executable, str(SCRIPT), "_worker", str(job_dir)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def run_worker(job_dir: Path) -> int:
    """Run Codex for a recorded job and persist its final state.

    Args:
        job_dir: Job directory containing metadata and the rendered prompt.

    Returns:
        The Codex exit code, or 127 when the process could not be launched.
    """
    meta = read_meta(job_dir)
    meta["pid"] = os.getpid()
    write_meta(job_dir, meta)

    return_code, launch_error = _run_codex(job_dir, meta)
    thread_id, usage = parse_events((job_dir / "events.jsonl").read_text(errors="replace"))

    meta = read_meta(job_dir)
    if meta.get("status") == "cancelled":
        return return_code

    meta.update(
        status="completed" if return_code == 0 else "failed",
        exit_code=return_code,
        thread_id=thread_id or meta.get("thread_id"),
        usage=usage,
        finished_at=now(),
    )
    if launch_error:
        meta["error"] = launch_error
    write_meta(job_dir, meta)
    return return_code


def _run_codex(job_dir: Path, meta: JobMeta) -> tuple[int, str | None]:
    """Run the recorded Codex argv while capturing its three process streams."""
    with (
        open(job_dir / "prompt.md", "rb") as stdin,
        open(job_dir / "events.jsonl", "wb") as stdout,
        open(job_dir / "stderr.log", "wb") as stderr,
    ):
        try:
            return (
                subprocess.call(
                    meta["argv"],
                    stdin=stdin,
                    stdout=stdout,
                    stderr=stderr,
                    cwd=meta["worktree"],
                ),
                None,
            )
        except OSError as error:
            message = f"failed to run codex: {error}"
            stderr.write(f"{message}\n".encode())
            return CODEX_LAUNCH_ERROR_EXIT_CODE, message
