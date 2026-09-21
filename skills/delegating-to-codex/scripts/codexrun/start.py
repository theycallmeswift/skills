"""`start`: validate the request, build the prompt, record the job, spawn its worker."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Protocol, TypedDict

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
BUNDLED_TEMPLATES = ("implement", "review")


class InputValues(TypedDict):
    """Contents read from the five supported orchestrator input files."""

    brief: str
    context: str | None
    risks: str | None
    rules: str | None
    report: str | None


class StartArgs(Protocol):
    """Arguments consumed while starting a Codex job."""

    effort: str
    template: str | None
    model: str | None
    tier: str | None
    network: bool
    brief: str | None
    context: str | None
    risks: str | None
    rules: str | None
    report: str | None
    sandbox: str
    schema: str | None
    diff: bool
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
    """Reject a start request that cannot produce a prompt."""
    if not args.brief:
        raise UsageError("--brief is required")


def _read_inputs(args: StartArgs) -> InputValues:
    """Read all orchestrator-provided input files."""
    brief = _read_input("brief", args.brief)
    if brief is None:
        raise UsageError("--brief is required")

    return {
        "brief": brief,
        "context": _read_input("context", args.context),
        "risks": _read_input("risks", args.risks),
        "rules": _read_input("rules", args.rules),
        "report": _read_input("report", args.report),
    }


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
    """Build a fresh or resumed prompt after the Git checks the sandbox calls for."""
    if args.resume:
        return _resume_prompt(inputs)

    if args.sandbox == "workspace-write":
        _require_clean(worktree, excluded_inputs)

    diff = _diff_section(args, worktree, excluded_inputs)
    return build_prompt(template=_template(args.template), diff=diff, **inputs)


def _diff_section(
    args: StartArgs,
    worktree: Path,
    excluded_inputs: frozenset[str],
) -> str | None:
    """Render the diff the job should read, when one was asked for."""
    if not (args.diff or args.base):
        return None

    return render_diff_section(collect_diff(worktree, args.base, excluded_inputs))


def _resume_prompt(inputs: InputValues) -> str:
    """Build a resumed prompt and report inputs that no longer apply."""
    ignored_flags = [
        f"--{name}" for name in ("context", "risks", "rules", "report") if inputs[name] is not None
    ]
    if ignored_flags:
        names = ", ".join(ignored_flags)
        print(f"note: {names} ignored on --resume (the thread has them)", file=sys.stderr)

    return build_resume_prompt(inputs["brief"])


def _require_clean(worktree: Path, exclude: frozenset[str]) -> None:
    """Codex's edits must be reviewable on their own, so a writing job starts from a clean tree."""
    pending = pending_changes(worktree, exclude)
    if not pending:
        return

    listing = ", ".join(line[3:] for line in pending[:5])
    raise UsageError(
        f"worktree has uncommitted changes ({listing}); commit them first so Codex's "
        "edits are reviewable on their own (or pass --resume for a fix round)"
    )


def _template(name: str | None) -> str | None:
    """Read the requested task template.

    Args:
        name: A bundled template name, a path to a template file, or None.

    Returns:
        The template text, or None when the job runs without one.

    Raises:
        UsageError: If the template path is not a file.
    """
    if name is None:
        return None

    if name in BUNDLED_TEMPLATES:
        return (ASSETS / f"{name}-prompt.md").read_text(encoding="utf-8")

    if not Path(name).is_file():
        raise UsageError(f"--template file not found: {name}")

    return Path(name).read_text(encoding="utf-8")


def template_slug(template: str | None) -> str:
    """Name a job after the template it runs; an untemplated job is just a job."""
    return template or "job"


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

    # A template may be a path, so the job id carries only its stem.
    job_id = new_job_id(Path(template_slug(args.template)).stem)
    job_dir = jobs / job_id
    job_dir.mkdir()

    argv = build_argv(
        worktree=worktree,
        job_dir=job_dir,
        effort=args.effort,
        sandbox=args.sandbox,
        model=args.model,
        tier=args.tier,
        network=args.network,
        thread_id=thread_id,
        schema=Path(args.schema) if args.schema else None,
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
        "template": template_slug(args.template),
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
