"""The detached worker: runs one job's `codex` process, gates its work, and records both."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import IO

from agentrun import SCRIPT
from agentrun.events import parse_events
from agentrun.state import (
    EVENTS,
    GATE_LOG,
    PROMPT,
    STDERR_LOG,
    GateResult,
    JobMeta,
    now,
    read_meta,
    record_pid,
    write_meta,
)

CODEX_LAUNCH_ERROR_EXIT_CODE = 127
SIGTERM_EXIT_CODE = 128 + int(signal.SIGTERM)
# Long enough for a real test suite, short enough that a wedged one still releases the
# orchestrator's turn. `start --wait` blocks on this, so an unbounded gate hangs the caller.
GATE_TIMEOUT_SECONDS = 900.0


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
        The Codex exit code, 127 when the process could not be launched, or 0 when the job
        was cancelled before Codex started.
    """
    record_pid(job_dir, os.getpid())

    # A cancel this early may have signalled a process group this worker had not joined yet,
    # so the status is the only word on it. Read it as late as possible before launching.
    meta = read_meta(job_dir)
    if meta.get("status") == "cancelled":
        return 0

    return_code, launch_error = _run_codex(job_dir, meta)
    thread_id, usage = parse_events((job_dir / EVENTS).read_text(errors="replace"))

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

    timeout = meta["gate_timeout"]

    with open(job_dir / GATE_LOG, "wb") as gate_log:
        try:
            gate = _spawn_gate(command, meta["worktree"], gate_log)
        except OSError as error:
            gate_log.write(f"failed to run gate: {error}\n".encode())
            return {"command": command, "status": "error", "reason": str(error)}

        with _gate_dies_with_this_worker(gate):
            try:
                exit_code = gate.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_gate(gate)
                gate_log.write(f"\ngate killed after {timeout:g}s\n".encode())
                return {"command": command, "status": "timeout", "timeout_seconds": timeout}

    return {
        "command": command,
        "status": "passed" if exit_code == 0 else "failed",
        "exit_code": exit_code,
    }


def _spawn_gate(command: str, worktree: str, gate_log: IO[bytes]) -> subprocess.Popen[bytes]:
    """Start the gate in a process group of its own, so a timeout can take the tree down."""
    return subprocess.Popen(
        command,
        shell=True,
        stdout=gate_log,
        stderr=subprocess.STDOUT,
        cwd=worktree,
        process_group=0,
    )


def _kill_gate(gate: subprocess.Popen[bytes]) -> None:
    """Kill the gate's whole group: under `shell=True` the real work is a child of the shell."""
    try:
        os.killpg(gate.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    gate.wait()


@contextmanager
def _gate_dies_with_this_worker(gate: subprocess.Popen[bytes]) -> Iterator[None]:
    """Hand a cancel on to the gate, whose own process group cancel's signal cannot reach."""

    def stop(_signal_number: int, _frame: FrameType | None) -> None:
        _kill_gate(gate)
        raise SystemExit(SIGTERM_EXIT_CODE)

    previous_handler = signal.signal(signal.SIGTERM, stop)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous_handler)


def _run_codex(job_dir: Path, meta: JobMeta) -> tuple[int, str | None]:
    """Run the recorded Codex argv while capturing its three process streams."""
    with (
        open(job_dir / PROMPT, "rb") as stdin,
        open(job_dir / EVENTS, "wb") as stdout,
        open(job_dir / STDERR_LOG, "wb") as stderr,
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
