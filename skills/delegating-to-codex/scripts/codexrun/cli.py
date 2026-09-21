"""Command line: parse arguments, dispatch a command, map errors to exit codes."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from pathlib import Path
from typing import Protocol, cast

from codexrun import ASSETS, PreflightError, UsageError
from codexrun.argv import EFFORTS, SANDBOXES, WRITABLE_SANDBOX
from codexrun.git import resolve_worktree
from codexrun.preflight import preflight
from codexrun.result import show_result
from codexrun.start import BUNDLED_TEMPLATES, INPUTS, StartArgs, start_job, template_label
from codexrun.state import JobMeta, find_job, jobs_dir, list_jobs, now, refresh, write_meta
from codexrun.worker import run_worker

REVIEW_SCHEMA = ASSETS / "review-output.schema.json"
TEMPLATE_COLUMN = 10


class ParsedArgs(Protocol):
    """Command discriminator present on every parsed namespace."""

    command: str


class WorktreeArgs(Protocol):
    """Arguments shared by commands scoped to a worktree."""

    cd: str | None


class StatusArgs(WorktreeArgs, Protocol):
    """Arguments consumed by the status command."""

    all: bool
    json: bool


class ResultArgs(WorktreeArgs, Protocol):
    """Arguments consumed by the result command."""

    job_id: str
    json: bool


class CancelArgs(WorktreeArgs, Protocol):
    """Arguments consumed by the cancel command."""

    job_id: str


class WorkerArgs(ParsedArgs, Protocol):
    """Arguments consumed by the internal worker command."""

    job_dir: str


def cmd_preflight(_args: ParsedArgs) -> int:
    """Check the Codex environment and print confirmation."""
    preflight()
    print("preflight: ok")
    return 0


def cmd_start(args: StartArgs) -> int:
    """Start a job and optionally wait for its result."""
    job_dir, worker = start_job(args)
    print(f"job {job_dir.name} started ({template_label(args)})")
    print(f"dir {job_dir}")

    if not args.wait:
        return 0

    worker.wait()
    print()
    return show_result(job_dir, as_json=False)


def cmd_status(args: StatusArgs) -> int:
    """Print visible jobs for the selected worktree."""
    rows = _visible_jobs(_jobs(args), show_all=args.all)

    if args.json:
        print(json.dumps(rows, indent=2))
    elif not rows:
        print("no jobs")
    else:
        _print_status_table(rows)

    return 0


def _print_status_table(rows: list[JobMeta]) -> None:
    """Print job metadata as a compact terminal table."""
    print(f"{'ID':<34} {'TEMPLATE':<{TEMPLATE_COLUMN}} {'STATUS':<10} CREATED")
    for meta in rows:
        template = _template_cell(meta["template"])
        print(
            f"{meta['id']:<34} {template:<{TEMPLATE_COLUMN}} "
            f"{meta['status']:<10} {meta['created_at']}"
        )


def _template_cell(template: str) -> str:
    """Fit a template name into its column so a file path cannot break the table."""
    name = Path(template).stem
    if len(name) <= TEMPLATE_COLUMN:
        return name

    return name[: TEMPLATE_COLUMN - 1] + "~"


def cmd_result(args: ResultArgs) -> int:
    """Print one job's result."""
    return show_result(find_job(_jobs(args), args.job_id), as_json=args.json)


def cmd_cancel(args: CancelArgs) -> int:
    """Cancel a running job while preserving its worktree edits."""
    job_dir = find_job(_jobs(args), args.job_id)
    meta = refresh(job_dir)

    if meta["status"] != "running":
        print(f"job {meta['id']} is already {meta['status']}")
        return 0

    meta.update(status="cancelled", finished_at=now())
    write_meta(job_dir, meta)
    _stop_worker(meta.get("pid"))

    print(f"job {meta['id']} cancelled")
    print("Any edits Codex made are left in the worktree; inspect them with `git status`.")
    return 0


def _stop_worker(pid: int | None) -> None:
    """Terminate a worker process group if it still exists."""
    if not pid:
        return

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def _jobs(args: WorktreeArgs) -> Path:
    """Resolve the job directory for a parsed command namespace."""
    return jobs_dir(os.environ, resolve_worktree(args.cd))


def _visible_jobs(jobs: Path, show_all: bool) -> list[JobMeta]:
    """Refreshed metas, limited to this session's jobs unless show_all."""
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    rows: list[JobMeta] = []

    for job_dir in list_jobs(jobs):
        try:
            meta = refresh(job_dir)
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise UsageError(f"cannot read job metadata for {job_dir.name}: {error}") from error

        if show_all or not session or meta.get("session_id") == session:
            rows.append(meta)

    return rows


def build_parser() -> argparse.ArgumentParser:
    """Build the complete command-line parser."""
    parser = argparse.ArgumentParser(description="Delegate tasks to codex exec as jobs.")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("preflight", help="check codex is installed and logged in")
    start = _add_start_parser(commands)
    status = _add_status_parser(commands)
    result = _add_result_parser(commands)
    cancel = _add_cancel_parser(commands)

    for command in (start, status, result, cancel):
        command.add_argument("--cd", metavar="DIR", help="worktree (default: $PROJECT_ROOT or cwd)")

    worker = commands.add_parser("_worker")
    worker.add_argument("job_dir")
    return parser


def _add_start_parser(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    """Add and return the start subcommand parser."""
    start = commands.add_parser("start", help="start a codex job")
    start.add_argument("--effort", required=True, choices=EFFORTS)
    start.add_argument(
        "--template", help=f"{', '.join(BUNDLED_TEMPLATES)}, or a task template file"
    )
    start.add_argument("--model")
    start.add_argument("--tier", help="service_tier")

    for name in INPUTS:
        start.add_argument(f"--{name}", metavar="FILE")

    start.add_argument(
        "--sandbox",
        choices=SANDBOXES,
        default=WRITABLE_SANDBOX,
        help=f"sandbox Codex runs in (default: {WRITABLE_SANDBOX})",
    )
    start.add_argument(
        "--schema",
        nargs="?",
        const=str(REVIEW_SCHEMA),
        metavar="FILE",
        help="require JSON output (default: the review schema)",
    )
    start.add_argument("--diff", action="store_true", help="attach the worktree diff to the prompt")
    start.add_argument(
        "--base", metavar="REF", help="diff against merge-base with REF (implies --diff)"
    )
    start.add_argument("--network", action="store_true", help="allow network access")
    start.add_argument("--resume", metavar="JOB_ID", help="continue that job's thread")
    start.add_argument(
        "--gate", metavar="CMD", help="shell command run after the job, in the worktree"
    )
    start.add_argument("--wait", action="store_true", help="run in the foreground")
    return start


def _add_status_parser(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    """Add and return the status subcommand parser."""
    status = commands.add_parser("status", help="list jobs for this worktree")
    status.add_argument("--all", action="store_true", help="include other sessions' jobs")
    status.add_argument("--json", action="store_true")
    return status


def _add_result_parser(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    """Add and return the result subcommand parser."""
    result = commands.add_parser("result", help="show a job's final message and usage")
    result.add_argument("job_id", nargs="?", default="last")
    result.add_argument("--json", action="store_true")
    return result


def _add_cancel_parser(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
) -> argparse.ArgumentParser:
    """Add and return the cancel subcommand parser."""
    cancel = commands.add_parser("cancel", help="stop a running job")
    cancel.add_argument("job_id")
    return cancel


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, dispatch one command, and map expected errors to exit codes."""
    namespace = build_parser().parse_args(argv)
    args = cast(ParsedArgs, namespace)

    if args.command == "_worker":
        worker_args = cast(WorkerArgs, namespace)
        return run_worker(Path(worker_args.job_dir))

    try:
        if args.command == "preflight":
            return cmd_preflight(args)
        if args.command == "start":
            return cmd_start(cast(StartArgs, namespace))
        if args.command == "status":
            return cmd_status(cast(StatusArgs, namespace))
        if args.command == "result":
            return cmd_result(cast(ResultArgs, namespace))
        if args.command == "cancel":
            return cmd_cancel(cast(CancelArgs, namespace))
        raise AssertionError(f"unhandled command: {args.command}")
    except UsageError as error:
        print(f"codex_run: {error}", file=sys.stderr)
        return 2
    except PreflightError as error:
        print(f"codex_run: preflight failed: {error}", file=sys.stderr)
        return 3
