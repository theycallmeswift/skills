"""The detached worker: runs one job's `codex` process and records how it ended."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from codexrun import SCRIPT
from codexrun.events import parse_events
from codexrun.state import GateResult, JobMeta, now, read_meta, write_meta

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

    gate = _run_gate(job_dir, meta, return_code)

    meta.update(
        status="completed" if return_code == 0 else "failed",
        exit_code=return_code,
        thread_id=thread_id or meta.get("thread_id"),
        usage=usage,
        finished_at=now(),
    )
    if gate:
        meta["gate"] = gate
    if launch_error:
        meta["error"] = launch_error
    write_meta(job_dir, meta)
    return return_code


def _run_gate(job_dir: Path, meta: JobMeta, codex_return_code: int) -> GateResult | None:
    """Check the delegate's work with a command the delegate itself never ran.

    Args:
        job_dir: Job directory the gate's combined output is written to.
        meta: Job metadata naming the gate command and the worktree to run it in.
        codex_return_code: How the delegate's own process exited.

    Returns:
        What the gate did, or None when the job asked for no gate.
    """
    command = meta.get("gate_command")
    if not command:
        return None

    # A delegate that failed made no claim worth checking, and a gate passing over
    # unchanged code would read like success.
    if codex_return_code != 0:
        return {"command": command, "status": "skipped"}

    with open(job_dir / "gate.log", "wb") as gate_log:
        try:
            exit_code = subprocess.call(
                command,
                shell=True,
                stdout=gate_log,
                stderr=subprocess.STDOUT,
                cwd=meta["worktree"],
            )
        except OSError as error:
            gate_log.write(f"failed to run gate: {error}\n".encode())
            return {"command": command, "status": "error"}

    return {
        "command": command,
        "status": "passed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
    }


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
