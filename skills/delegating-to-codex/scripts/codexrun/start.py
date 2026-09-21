"""`start`: validate the request, build the prompt, record the job, spawn its worker."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple, Protocol, TypedDict

from codexrun import ASSETS, UsageError
from codexrun.argv import WRITABLE_SANDBOX, build_argv, writes_to_disk
from codexrun.git import collect_diff, pending_changes, relative_inputs, resolve_worktree
from codexrun.preflight import preflight
from codexrun.prompt import build_prompt, build_resume_prompt, render_diff_section
from codexrun.state import (
    MAX_JOBS,
    PROMPT,
    JobMeta,
    find_job,
    jobs_dir,
    new_job_id,
    now,
    prune_jobs,
    read_meta,
    record_pid,
    write_meta,
)
from codexrun.worker import spawn_worker

INPUTS = ("brief", "context", "risks", "rules", "report")
BUNDLED_TEMPLATES = ("implement", "review")
RESUME_SLUG = "resume"
UNTEMPLATED_SLUG = "job"


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
    sandbox: str | None
    schema: str | None
    diff: bool
    base: str | None
    resume: str | None
    gate: str | None
    cd: str | None
    wait: bool


class RunSettings(NamedTuple):
    """The conditions a job runs under, once a resumed thread's have been inherited.

    Attributes:
        sandbox: Codex sandbox the job runs in.
        schema: JSON schema the final message must satisfy, when one applies.
        thread_id: Existing Codex thread the job continues, when it resumes one.
        escalated: Whether a resume raised a parent that could not write into one that can.
    """

    sandbox: str
    schema: Path | None
    thread_id: str | None
    escalated: bool = False


def start_job(args: StartArgs) -> tuple[Path, subprocess.Popen[bytes]]:
    """Validate, record, and spawn a Codex job."""
    worktree = resolve_worktree(args.cd)
    inputs = _read_inputs(args)
    jobs = jobs_dir(os.environ, worktree)
    run = _run_settings(args, jobs)
    preflight()

    input_paths = (getattr(args, name) for name in INPUTS)
    excluded_inputs = relative_inputs(worktree, input_paths)
    prompt = _build_prompt(args, run, worktree, inputs, excluded_inputs)
    job_dir = _create_job(jobs, args, run, worktree, prompt)

    worker = spawn_worker(job_dir)
    # The worker leads its own process group, so cancel can kill it from here on. Waiting for
    # the worker to record its own pid would leave a cancel in between with nothing to signal.
    record_pid(job_dir, worker.pid)

    return job_dir, worker


def _read_inputs(args: StartArgs) -> InputValues:
    """Read all orchestrator-provided input files.

    Args:
        args: Parsed start options naming the input files.

    Returns:
        The contents of every supplied input file.

    Raises:
        UsageError: If no brief was given, or a named file does not exist.
    """
    if not args.brief:
        raise UsageError("--brief is required")

    return {
        "brief": _input_file("brief", args.brief).read_text(encoding="utf-8"),
        "context": _read_input("context", args.context),
        "risks": _read_input("risks", args.risks),
        "rules": _read_input("rules", args.rules),
        "report": _read_input("report", args.report),
    }


def _read_input(name: str, path: str | None) -> str | None:
    """Read one optional input file."""
    if path is None:
        return None

    return _input_file(name, path).read_text(encoding="utf-8")


def _schema_file(schema: str | None) -> Path | None:
    """Resolve the optional output schema path.

    A resume replays the recorded path from whatever directory the orchestrator is in by
    then, so it is made absolute here rather than at the point it is read back.
    """
    if schema is None:
        return None

    return _input_file("schema", schema).absolute()


def _input_file(name: str, path: str) -> Path:
    """Resolve a file the caller named on the command line, or raise a user-facing error."""
    resolved = Path(path)
    if not resolved.is_file():
        raise UsageError(f"--{name} file not found: {path}")

    return resolved


def _run_settings(args: StartArgs, jobs: Path) -> RunSettings:
    """Resolve the sandbox, schema, and thread the job runs with.

    Args:
        args: Parsed start options.
        jobs: Directory holding this worktree's jobs.

    Returns:
        The conditions the job runs under.
    """
    if not args.resume:
        return RunSettings(
            sandbox=args.sandbox or WRITABLE_SANDBOX,
            schema=_schema_file(args.schema),
            thread_id=None,
        )

    return _resumed_settings(args, read_meta(find_job(jobs, args.resume)))


def _resumed_settings(args: StartArgs, parent: JobMeta) -> RunSettings:
    """Continue a thread under the conditions it started with, unless the caller overrode them.

    Args:
        args: Parsed start options; a flag the caller passed outranks the recorded value.
        parent: Metadata of the job being resumed.

    Returns:
        The conditions the resumed job runs under.

    Raises:
        UsageError: If the resumed job recorded no thread to continue.
    """
    thread_id = parent.get("thread_id")
    if not thread_id:
        raise UsageError(f"job {parent['id']} has no recorded thread_id; cannot resume")

    inherited_sandbox = _inherited_sandbox(parent)
    sandbox = args.sandbox or inherited_sandbox

    return RunSettings(
        sandbox=sandbox,
        schema=_schema_file(args.schema) if args.schema else _inherited_schema(parent),
        thread_id=thread_id,
        escalated=writes_to_disk(sandbox) and not writes_to_disk(inherited_sandbox),
    )


def _inherited_sandbox(parent: JobMeta) -> str:
    """The sandbox a resume continues under; metadata that recorded none falls back."""
    return parent.get("sandbox") or WRITABLE_SANDBOX


def _inherited_schema(parent: JobMeta) -> Path | None:
    """Return the output schema a resumed job inherits, when its parent ran with one.

    Args:
        parent: Metadata of the job being resumed.

    Returns:
        The recorded schema, or None when the parent ran without one.

    Raises:
        UsageError: If the recorded schema is gone. Review inputs live in scratch space,
            which gets cleaned up, and the caller passed no flag to blame for it.
    """
    recorded = parent.get("schema")
    if not recorded:
        return None

    schema = Path(recorded)
    if not schema.is_file():
        raise UsageError(
            f"inherited schema file is missing: {recorded}; pass --schema to name another"
        )

    return schema


def _build_prompt(
    args: StartArgs,
    run: RunSettings,
    worktree: Path,
    inputs: InputValues,
    excluded_inputs: frozenset[str],
) -> str:
    """Build a fresh or resumed prompt after the Git checks the sandbox calls for."""
    if args.resume:
        # A fix round is exempt because it runs against the delegate's own uncommitted edits.
        # A parent that could not write produced none, so whatever is pending belongs to the
        # user and an escalation to a writable sandbox has to answer for it.
        if run.escalated:
            _require_clean(worktree, excluded_inputs)

        return _resume_prompt(args, inputs)

    if writes_to_disk(run.sandbox):
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


def _resume_prompt(args: StartArgs, inputs: InputValues) -> str:
    """Build a resumed prompt and report the flags that no longer apply.

    Args:
        args: Parsed start options, read for the flags a resume cannot honour.
        inputs: Contents of the orchestrator's input files.

    Returns:
        The compact follow-up prompt for the resumed thread.
    """
    ignored_inputs = [
        f"--{name}" for name in ("context", "risks", "rules", "report") if inputs[name] is not None
    ]
    ignored_flags = [
        flag
        for flag, given in (
            ("--template", args.template),
            ("--diff", args.diff),
            ("--base", args.base),
        )
        if given
    ]

    if ignored_inputs or ignored_flags:
        names = ", ".join(ignored_inputs + ignored_flags)
        print(
            f"note: {names} ignored on --resume; the thread continues where it left off",
            file=sys.stderr,
        )

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
        bundled = ", ".join(BUNDLED_TEMPLATES)
        raise UsageError(f"--template is neither a file nor one of {bundled}: {name}")

    return Path(name).read_text(encoding="utf-8")


def template_label(args: StartArgs) -> str:
    """Name a job by what it runs: a resumed thread, its template, or a plain job."""
    if args.resume:
        return RESUME_SLUG

    return args.template or UNTEMPLATED_SLUG


def template_slug(args: StartArgs) -> str:
    """Reduce a job's label to a filename-safe slug for its identifier."""
    return Path(template_label(args)).stem


def _create_job(
    jobs: Path,
    args: StartArgs,
    run: RunSettings,
    worktree: Path,
    prompt: str,
) -> Path:
    """Create the job directory, prompt, argv, and initial metadata."""
    jobs.mkdir(parents=True, exist_ok=True)
    prune_jobs(jobs, keep=MAX_JOBS - 1)

    job_id = new_job_id(template_slug(args))
    job_dir = jobs / job_id
    job_dir.mkdir()

    argv = build_argv(
        worktree=worktree,
        job_dir=job_dir,
        effort=args.effort,
        sandbox=run.sandbox,
        model=args.model,
        tier=args.tier,
        network=args.network,
        thread_id=run.thread_id,
        schema=run.schema,
    )
    (job_dir / PROMPT).write_text(prompt, encoding="utf-8")

    meta = _initial_meta(job_id, args, run, worktree, argv)
    write_meta(job_dir, meta)
    return job_dir


def _initial_meta(
    job_id: str,
    args: StartArgs,
    run: RunSettings,
    worktree: Path,
    argv: list[str],
) -> JobMeta:
    """Build the initial metadata for a running job."""
    return {
        "id": job_id,
        "template": template_label(args),
        "sandbox": run.sandbox,
        "schema": str(run.schema) if run.schema else None,
        "worktree": str(worktree),
        "argv": argv,
        "pid": None,
        "status": "running",
        "exit_code": None,
        "thread_id": run.thread_id,
        "usage": None,
        "session_id": os.environ.get("CLAUDE_CODE_SESSION_ID"),
        "resumed_from": args.resume,
        "gate_command": args.gate,
        "created_at": now(),
        "finished_at": None,
    }
