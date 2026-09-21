"""Job state kept outside the repo: one dir per job holding meta.json and the run's files."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import time
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast

from codexrun import UsageError

MAX_JOBS = 50
# A job whose worker never recorded a pid after this long is treated as dead.
PID_GRACE_SECONDS = 60
# The files that make up one job directory.
META = "meta.json"
PROMPT = "prompt.md"
EVENTS = "events.jsonl"
STDERR_LOG = "stderr.log"
LAST_MESSAGE = "last.md"
GATE_LOG = "gate.log"


class Usage(TypedDict):
    """Token counts reported by a completed Codex turn."""

    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int


GateStatus = Literal["passed", "failed", "skipped", "error"]


class GateResult(TypedDict):
    """Outcome of the post-run check the worker ran on the delegate's work.

    Attributes:
        command: The shell command the gate ran.
        status: How the gate ended.
        exit_code: The command's exit code, absent when it never ran.
        reason: Why the gate could not start, present only on an error.
    """

    command: str
    status: GateStatus
    exit_code: NotRequired[int]
    reason: NotRequired[str]


class JobMeta(TypedDict):
    """Persistent metadata for one delegated Codex job."""

    id: str
    template: str
    sandbox: str
    schema: str | None
    worktree: str
    argv: list[str]
    pid: int | None
    status: str
    exit_code: int | None
    thread_id: str | None
    usage: Usage | None
    session_id: str | None
    resumed_from: str | None
    gate_command: str | None
    created_at: str
    finished_at: str | None
    gate: NotRequired[GateResult]
    error: NotRequired[str]


def state_root(env: Mapping[str, str]) -> Path:
    """Resolve the persistent state root.

    Args:
        env: Environment variables used to select a harness-specific state directory.

    Returns:
        The most specific configured state directory.
    """
    if env.get("CLAUDE_PLUGIN_DATA"):
        return Path(env["CLAUDE_PLUGIN_DATA"])

    if env.get("HERMES_HOME"):
        return Path(env["HERMES_HOME"]) / "mechaswift"

    if env.get("XDG_STATE_HOME"):
        return Path(env["XDG_STATE_HOME"]) / "mechaswift"

    home = Path(env["HOME"]) if env.get("HOME") else Path.home()
    return home / ".local" / "state" / "mechaswift"


def jobs_dir(env: Mapping[str, str], worktree: Path) -> Path:
    """Resolve the job directory for a worktree.

    Args:
        env: Environment variables used to resolve the state root.
        worktree: Canonical or user-provided worktree path.

    Returns:
        A stable, worktree-specific directory below the state root.
    """
    real = os.path.realpath(worktree)
    digest = hashlib.sha256(real.encode()).hexdigest()[:16]
    return state_root(env) / "codex-jobs" / f"{os.path.basename(real)}-{digest}"


def new_job_id(slug: str) -> str:
    """Create a timestamped, collision-resistant job identifier."""
    return f"{datetime.now():%Y%m%d-%H%M%S}-{slug}-{secrets.token_hex(2)}"


def now() -> str:
    """Return the current local time as an ISO 8601 string."""
    return datetime.now().astimezone().isoformat()


def read_meta(job_dir: Path) -> JobMeta:
    """Read a job's metadata from disk."""
    decoded = json.loads((job_dir / META).read_text(encoding="utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError(f"job metadata is not an object: {job_dir.name}")
    return cast(JobMeta, decoded)


def write_meta(job_dir: Path, meta: JobMeta) -> None:
    """Validate and atomically write a job's metadata."""
    _created_at(meta)

    # Write-then-rename so a concurrent reader never sees a half-written file.
    temporary_path = job_dir / f".meta.{os.getpid()}.tmp"
    temporary_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary_path, job_dir / META)


def list_jobs(jobs: Path) -> list[Path]:
    """Return job directories ordered newest first."""
    if not jobs.is_dir():
        return []

    job_directories = [job_dir for job_dir in jobs.iterdir() if job_dir.is_dir()]
    return sorted(job_directories, key=_created_then_name, reverse=True)


def _created_then_name(job_dir: Path) -> tuple[str, str]:
    """Return the stable sort key for a job directory."""
    try:
        return (_created_at(read_meta(job_dir)), job_dir.name)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise UsageError(f"cannot read job metadata for {job_dir.name}: {error}") from error


def prune_jobs(jobs: Path, keep: int = MAX_JOBS) -> None:
    """Delete all but the newest requested number of job directories."""
    for old_job_dir in list_jobs(jobs)[keep:]:
        shutil.rmtree(old_job_dir, ignore_errors=True)


def find_job(jobs: Path, job_id: str) -> Path:
    """Find a job directory by identifier.

    Args:
        jobs: Directory containing the worktree's jobs.
        job_id: Exact job identifier or ``last`` for the newest job.

    Returns:
        The matching job directory.

    Raises:
        UsageError: If the requested job does not exist.
    """
    if job_id == "last":
        found = list_jobs(jobs)
        if not found:
            raise UsageError("no jobs for this worktree")
        return found[0]

    job_dir = jobs / job_id
    if not (job_dir / META).is_file():
        raise UsageError(f"no such job for this worktree: {job_id}")

    return job_dir


def refresh(job_dir: Path) -> JobMeta:
    """Load meta, marking a running job failed if its worker is gone."""
    meta = read_meta(job_dir)
    if meta.get("status") != "running" or _worker_alive(meta):
        return meta

    # The worker may have finished between the first read and the process check.
    meta = read_meta(job_dir)
    if meta.get("status") == "running":
        meta.update(status="failed", finished_at=now())
        write_meta(job_dir, meta)

    return meta


def _worker_alive(meta: JobMeta) -> bool:
    """Return whether a running job still has a viable worker."""
    pid = meta.get("pid")
    if pid:
        return _pid_alive(pid)

    return _age_seconds(meta) <= PID_GRACE_SECONDS


def _pid_alive(pid: int) -> bool:
    """Return whether the process exists or cannot be inspected."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True

    return True


def _age_seconds(meta: JobMeta) -> float:
    """Return seconds elapsed since the job metadata was created."""
    return time.time() - datetime.fromisoformat(_created_at(meta)).timestamp()


def _created_at(meta: JobMeta) -> str:
    """Validate and return a job's creation timestamp."""
    created_at = meta["created_at"]
    if not isinstance(created_at, str):
        raise TypeError("job metadata created_at must be a string")
    datetime.fromisoformat(created_at)
    return created_at
