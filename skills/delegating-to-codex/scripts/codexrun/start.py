"""`start`: validate the request, build the prompt, record the job, spawn its worker."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Protocol, cast

from codexrun import ASSETS, UsageError
from codexrun.argv import build_argv
from codexrun.git import collect_diff, pending_changes, relative_inputs, resolve_worktree
from codexrun.preflight import preflight
from codexrun.prompt import build_prompt, build_resume_prompt, render_diff_section
from codexrun.state import (
    MAX_JOBS,
    JobMeta,
    find_job,
    jobs_dir,
    new_job_id,
    now,
    prune_jobs,
    read_meta,
    write_meta,
)
from codexrun.worker import spawn_worker

INPUTS = ("brief", "context", "risks", "rules", "report")
InputValues = dict[str, str | None]


class StartArgs(Protocol):
    """Arguments consumed while starting a Codex job."""

    mode: str
    effort: str
    model: str | None
    tier: str | None
    network: bool
    brief: str | None
    context: str | None
    risks: str | None
    rules: str | None
    report: str | None
    base: str | None
    resume: str | None
    cd: str | None
    wait: bool


def start_job(args: StartArgs) -> tuple[Path, subprocess.Popen[bytes]]:
    """Validate, record, and spawn a Codex job."""
    _check_flags(args)

    worktree = resolve_worktree(args.cd)
    inputs = _read_inputs(args)
    preflight()

    input_paths = (getattr(args, name) for name in INPUTS)
    excluded_inputs = relative_inputs(worktree, input_paths)
    jobs = jobs_dir(os.environ, worktree)
    thread_id = _resume_thread(jobs, args.resume) if args.resume else None
    prompt = _build_prompt(args, worktree, inputs, excluded_inputs)
    job_dir = _create_job(jobs, args, worktree, thread_id, prompt)

    return job_dir, spawn_worker(job_dir)


def _check_flags(args: StartArgs) -> None:
    """Reject invalid mode-specific start options."""
    if args.mode == "review" and args.network:
        raise UsageError("--network is only valid for implement")

    if args.mode == "review" and args.resume:
        raise UsageError("--resume is only valid for implement")

    if not args.brief:
        raise UsageError(f"--brief is required for {args.mode}")

    if args.mode == "implement" and args.report:
        print("note: --report is only used by review; ignoring it", file=sys.stderr)


def _read_inputs(args: StartArgs) -> InputValues:
    """Read all orchestrator-provided input files."""
    return {name: _read_input(name, getattr(args, name)) for name in INPUTS}


def _read_input(name: str, path: str | None) -> str | None:
    """Read one optional input file or raise a user-facing error."""
    if path is None:
        return None

    if not Path(path).is_file():
        raise UsageError(f"--{name} file not found: {path}")

    return Path(path).read_text(encoding="utf-8")


def _resume_thread(jobs: Path, job_id: str) -> str:
    """Return the recorded thread ID for a resumable job."""
    thread_id = read_meta(find_job(jobs, job_id)).get("thread_id")
    if not thread_id:
        raise UsageError(f"job {job_id} has no recorded thread_id; cannot resume")

    return thread_id


def _build_prompt(
    args: StartArgs,
    worktree: Path,
    inputs: InputValues,
    excluded_inputs: frozenset[str],
) -> str:
    """Build a fresh or resumed prompt after mode-specific Git checks."""
    if args.resume:
        return _resume_prompt(inputs)

    if args.mode == "implement":
        _require_clean(worktree, excluded_inputs)
        return build_prompt("implement", template=_template("implement"), **inputs)

    diff_info = collect_diff(worktree, args.base, excluded_inputs)
    diff = render_diff_section(diff_info)
    return build_prompt("review", template=_template("review"), diff=diff, **inputs)


def _resume_prompt(inputs: InputValues) -> str:
    """Build a resumed prompt and report inputs that no longer apply."""
    ignored_flags = [
        f"--{name}" for name in ("context", "risks", "rules") if inputs[name] is not None
    ]
    if ignored_flags:
        names = ", ".join(ignored_flags)
        print(f"note: {names} ignored on --resume (the thread has them)", file=sys.stderr)

    return build_resume_prompt(cast(str, inputs["brief"]))


def _require_clean(worktree: Path, exclude: frozenset[str]) -> None:
    """Codex's edits must be reviewable on their own, so implement starts from a clean tree."""
    pending = pending_changes(worktree, exclude)
    if not pending:
        return

    listing = ", ".join(line[3:] for line in pending[:5])
    raise UsageError(
        f"worktree has uncommitted changes ({listing}); commit them first so Codex's "
        "edits are reviewable on their own (or pass --resume for a fix round)"
    )


def _template(mode: str) -> str:
    """Read the bundled task template for a mode."""
    return (ASSETS / f"{mode}-prompt.md").read_text(encoding="utf-8")


def _create_job(
    jobs: Path,
    args: StartArgs,
    worktree: Path,
    thread_id: str | None,
    prompt: str,
) -> Path:
    """Create the job directory, prompt, argv, and initial metadata."""
    jobs.mkdir(parents=True, exist_ok=True)
    prune_jobs(jobs, keep=MAX_JOBS - 1)

    job_id = new_job_id(args.mode)
    job_dir = jobs / job_id
    job_dir.mkdir()

    argv = build_argv(
        args.mode,
        worktree=worktree,
        job_dir=job_dir,
        effort=args.effort,
        model=args.model,
        tier=args.tier,
        network=args.network,
        thread_id=thread_id,
    )
    (job_dir / "prompt.md").write_text(prompt, encoding="utf-8")

    meta = _initial_meta(job_id, args, worktree, argv, thread_id)
    write_meta(job_dir, meta)
    return job_dir


def _initial_meta(
    job_id: str,
    args: StartArgs,
    worktree: Path,
    argv: list[str],
    thread_id: str | None,
) -> JobMeta:
    """Build the initial metadata for a running job."""
    return {
        "id": job_id,
        "mode": args.mode,
        "worktree": str(worktree),
        "argv": argv,
        "pid": None,
        "status": "running",
        "exit_code": None,
        "thread_id": thread_id,
        "usage": None,
        "session_id": os.environ.get("CLAUDE_CODE_SESSION_ID"),
        "resumed_from": args.resume,
        "created_at": now(),
        "finished_at": None,
    }
