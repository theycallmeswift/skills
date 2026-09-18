#!/usr/bin/env python3
"""
Delegate implementation and review tasks to `codex exec` as background jobs.

Builds every `codex exec` call, keeps job state outside the repo, and reports the
final message plus token usage. Codex only edits the worktree; the caller commits.

Usage:
    codex_run.py preflight
    codex_run.py start {implement|review} --effort EFFORT [--model M] [--tier T] [--network]
        [--brief F] [--context F] [--risks F] [--rules F] [--report F] [--base REF]
        [--resume JOB_ID] [--cd DIR] [--wait]
    codex_run.py status [--all] [--json]
    codex_run.py result [JOB_ID|last] [--json]
    codex_run.py cancel JOB_ID

Exit codes: 0 ok; 1 job failed or cancelled; 2 usage or input error; 3 preflight failed;
4 job still running.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

SCRIPT = Path(__file__).resolve()
ASSETS = SCRIPT.parent.parent / "assets"
EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")
MAX_JOBS = 50
INLINE_MAX_FILES = 2
INLINE_MAX_BYTES = 256 * 1024
USAGE_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")
# A job whose worker never recorded a pid after this long is treated as dead.
PID_GRACE_SECONDS = 60


class UsageError(Exception):
    """Bad invocation or input; exit 2."""


class PreflightError(Exception):
    """Environment can't run Codex; exit 3."""


# ---------------------------------------------------------------------------
# state


def state_root(env) -> Path:
    """Persistent state root: the most specific harness-provided dir wins."""
    if env.get("CLAUDE_PLUGIN_DATA"):
        return Path(env["CLAUDE_PLUGIN_DATA"])
    if env.get("HERMES_HOME"):
        return Path(env["HERMES_HOME"]) / "mechaswift"
    if env.get("XDG_STATE_HOME"):
        return Path(env["XDG_STATE_HOME"]) / "mechaswift"
    home = Path(env["HOME"]) if env.get("HOME") else Path.home()
    return home / ".local" / "state" / "mechaswift"


def jobs_dir(env, worktree: Path) -> Path:
    real = os.path.realpath(worktree)
    digest = hashlib.sha256(real.encode()).hexdigest()[:16]
    return state_root(env) / "codex-jobs" / f"{os.path.basename(real)}-{digest}"


def new_job_id(mode: str) -> str:
    return f"{datetime.now():%Y%m%d-%H%M%S}-{mode}-{secrets.token_hex(2)}"


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def read_meta(job_dir: Path) -> dict:
    return json.loads((job_dir / "meta.json").read_text(encoding="utf-8"))


def write_meta(job_dir: Path, meta: dict) -> None:
    tmp = job_dir / f".meta.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, job_dir / "meta.json")


def _sort_key(job_dir: Path) -> tuple[str, str]:
    try:
        created = read_meta(job_dir).get("created_at") or ""
    except (OSError, ValueError):
        created = ""
    return (created, job_dir.name)


def list_jobs(jobs: Path) -> list[Path]:
    """Job dirs, newest first."""
    if not jobs.is_dir():
        return []
    dirs = [p for p in jobs.iterdir() if p.is_dir()]
    return sorted(dirs, key=_sort_key, reverse=True)


def prune_jobs(jobs: Path, keep: int = MAX_JOBS) -> None:
    for old in list_jobs(jobs)[keep:]:
        shutil.rmtree(old, ignore_errors=True)


# ---------------------------------------------------------------------------
# argv and prompt


def build_argv(
    mode: str,
    *,
    worktree: Path,
    job_dir: Path,
    effort: str,
    model: str | None = None,
    tier: str | None = None,
    network: bool = False,
    thread_id: str | None = None,
    schema: Path | None = None,
) -> list[str]:
    """The exact `codex` argv for a job. Task settings explicit; user config inherited."""
    if mode == "review" and (network or thread_id):
        raise ValueError("review runs read-only and fresh: no network, no resume")
    if mode not in ("implement", "review"):
        raise ValueError(f"unknown mode: {mode}")

    task = ["-c", f"model_reasoning_effort={effort}"]
    if tier:
        task += ["-c", f"service_tier={tier}"]
    if model:
        task += ["-m", model]
    net = ["-c", "sandbox_workspace_write.network_access=true"] if network else []
    tail = ["-o", str(job_dir / "last.md"), "-"]

    if thread_id:
        head = ["codex", "exec", "resume", thread_id, "--json", "--strict-config"]
        return [*head, "-c", 'sandbox_mode="workspace-write"', *task, *net, *tail]
    if mode == "implement":
        head = ["codex", "exec", "--sandbox", "workspace-write", "--cd", str(worktree)]
        return [*head, "--json", "--strict-config", *task, *net, *tail]
    schema = schema or ASSETS / "review-output.schema.json"
    head = ["codex", "exec", "--sandbox", "read-only", "--ephemeral", "--cd", str(worktree)]
    return [*head, "--json", "--strict-config", *task, "--output-schema", str(schema), *tail]


def _section(name: str, text: str) -> str:
    return f"=== {name} ===\n{text.strip()}\n"


def build_prompt(
    mode: str,
    *,
    template: str,
    brief: str,
    rules: str | None = None,
    context: str | None = None,
    report: str | None = None,
    risks: str | None = None,
    diff: str | None = None,
) -> str:
    parts = [("TASK TEMPLATE", template), ("RULES", rules), ("BRIEF", brief)]
    parts.append(("CONTEXT", context))
    if mode == "review":
        parts.append(("IMPLEMENTER REPORT", report))
    parts.append(("NAMED RISKS", risks))
    if mode == "review":
        parts.append(("DIFF", diff))
    return "\n".join(_section(name, text) for name, text in parts if text is not None)


def build_resume_prompt(brief: str) -> str:
    header = (
        "Follow-up from the orchestrator on the task above. Apply the fixes below under the "
        "same rules: leave changes in the working tree (no git add/commit/stash/checkout), "
        "and end with the same STATUS final message.\n"
    )
    return header + "\n" + _section("BRIEF", brief)


# ---------------------------------------------------------------------------
# review diff


@dataclass
class DiffInfo:
    label: str
    files: list[str]
    text: str
    commands: list[str]
    untracked: list[str] = field(default_factory=list)


def render_diff_section(info: DiffInfo) -> str:
    all_files = info.files + [f"{f} (untracked)" for f in info.untracked]
    listing = "\n".join(f"- {f}" for f in all_files)
    size = len(info.text.encode())
    commands = "\n".join(f"  {c}" for c in info.commands)
    if len(all_files) <= INLINE_MAX_FILES and size <= INLINE_MAX_BYTES:
        out = f"Scope: {info.label}\nChanged files:\n{listing}\n\n"
        if info.untracked:
            out += "Untracked files are new and not in the diff; read them directly.\n\n"
        return out + f"Diff (from `{info.commands[0]}`):\n{info.text}"
    return (
        f"Scope: {info.label}\n"
        f"The diff is too large to inline ({len(all_files)} files, {size // 1024} KB). "
        f"Inspect it yourself with read-only git:\n{commands}\n"
        "Read untracked files directly.\n\n"
        f"Changed files:\n{listing}\n"
    )


def _git(worktree: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(worktree), *args], capture_output=True, text=True, check=check
    )


def _default_base(worktree: Path) -> str:
    for ref in ("origin/HEAD", "main", "master"):
        if _git(worktree, "rev-parse", "--verify", "--quiet", ref, check=False).returncode == 0:
            return ref
    raise UsageError("no base branch found (origin/HEAD, main, master); pass --base REF")


def pending_changes(worktree: Path, exclude: frozenset[str] = frozenset()) -> list[str]:
    """`git status --porcelain` entries, minus the job's own input files.

    Briefs and risk files often sit inside the worktree; they must not make it look dirty.
    """
    out = _git(worktree, "status", "--porcelain", "--untracked-files=all").stdout
    return [line for line in out.splitlines() if line[3:] not in exclude]


def relative_inputs(worktree: Path, paths) -> frozenset[str]:
    """Repo-relative paths of the input files that live inside the worktree."""
    rel = set()
    for path in paths:
        if path is None:
            continue
        real = Path(os.path.realpath(path))
        if real.is_relative_to(worktree):
            rel.add(real.relative_to(worktree).as_posix())
    return frozenset(rel)


def collect_diff(
    worktree: Path, base: str | None, exclude: frozenset[str] = frozenset()
) -> DiffInfo:
    untracked = [
        f
        for f in _git(worktree, "ls-files", "--others", "--exclude-standard").stdout.split()
        if f not in exclude
    ]
    dirty = bool(pending_changes(worktree, exclude))
    if base is None and dirty:
        rev, label = "HEAD", "uncommitted changes"
        commands = ["git diff HEAD", "git ls-files --others --exclude-standard"]
    else:
        ref = base or _default_base(worktree)
        mb = _git(worktree, "merge-base", "HEAD", ref, check=False)
        if mb.returncode != 0:
            raise UsageError(f"cannot find merge-base of HEAD and {ref}")
        rev, label = mb.stdout.strip(), f"changes since merge-base with {ref}"
        commands = [f"git diff {rev}", f"git diff --stat {rev}"]
        if untracked:
            commands.append("git ls-files --others --exclude-standard")
    files = _git(worktree, "diff", rev, "--name-only").stdout.split()
    text = _git(worktree, "diff", rev).stdout
    if not files and not untracked:
        raise UsageError(f"nothing to review: no changes ({label})")
    return DiffInfo(label=label, files=files, text=text, commands=commands, untracked=untracked)


# ---------------------------------------------------------------------------
# events


def parse_events(text: str) -> tuple[str | None, dict | None]:
    """(thread_id, usage of the last turn.completed) from a JSONL stream; tolerates junk."""
    thread_id, usage = None, None
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "thread.started" and event.get("thread_id"):
            thread_id = event["thread_id"]
        elif event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = {k: event["usage"].get(k, 0) for k in USAGE_KEYS}
    return thread_id, usage


def format_usage(usage: dict | None) -> str:
    if not usage:
        return "tokens: unavailable"
    return (
        f"tokens: in {usage.get('input_tokens', 0)} "
        f"(cached {usage.get('cached_input_tokens', 0)}), "
        f"out {usage.get('output_tokens', 0)}, "
        f"reasoning {usage.get('reasoning_output_tokens', 0)}"
    )


# ---------------------------------------------------------------------------
# environment


def resolve_worktree(cd: str | None) -> Path:
    start = cd or os.environ.get("PROJECT_ROOT") or os.getcwd()
    try:
        res = _git(Path(start), "rev-parse", "--show-toplevel", check=False)
    except (FileNotFoundError, NotADirectoryError) as e:
        raise UsageError(f"cannot run git in {start}: {e}") from e
    if res.returncode != 0:
        raise UsageError(f"not a git repository: {start}")
    return Path(os.path.realpath(res.stdout.strip()))


def preflight() -> None:
    if os.environ.get("CODEX_THREAD_ID"):
        raise PreflightError("already running inside Codex; do the work directly")
    if not shutil.which("codex"):
        raise PreflightError("`codex` not found on PATH; install the Codex CLI first")
    try:
        res = subprocess.run(["codex", "login", "status"], capture_output=True, timeout=60)
    except subprocess.TimeoutExpired as e:
        raise PreflightError("`codex login status` timed out; check the Codex CLI") from e
    if res.returncode != 0:
        raise PreflightError("Codex is not logged in; run `codex login`")


def _read_input(flag: str, path: str | None) -> str | None:
    if path is None:
        return None
    p = Path(path)
    if not p.is_file():
        raise UsageError(f"{flag} file not found: {path}")
    return p.read_text(encoding="utf-8")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _age_seconds(meta: dict) -> float:
    try:
        return time.time() - datetime.fromisoformat(meta["created_at"]).timestamp()
    except (KeyError, TypeError, ValueError):
        return float("inf")


def refresh(job_dir: Path) -> dict:
    """Load meta, marking a running job failed if its worker is gone."""
    meta = read_meta(job_dir)
    if meta.get("status") != "running":
        return meta
    pid = meta.get("pid")
    dead = not _pid_alive(pid) if pid else _age_seconds(meta) > PID_GRACE_SECONDS
    if dead:
        # The worker may have finished between the read and the check.
        meta = read_meta(job_dir)
        if meta.get("status") == "running":
            meta.update(status="failed", finished_at=_now())
            write_meta(job_dir, meta)
    return meta


def find_job(jobs: Path, job_id: str) -> Path:
    if job_id == "last":
        found = list_jobs(jobs)
        if not found:
            raise UsageError("no jobs for this worktree")
        return found[0]
    job_dir = jobs / job_id
    if not (job_dir / "meta.json").is_file():
        raise UsageError(f"no such job for this worktree: {job_id}")
    return job_dir


# ---------------------------------------------------------------------------
# commands


def cmd_preflight(args) -> int:
    preflight()
    print("preflight: ok")
    return 0


def cmd_start(args) -> int:
    mode = args.mode
    if mode == "review" and args.network:
        raise UsageError("--network is only valid for implement")
    if mode == "review" and args.resume:
        raise UsageError("--resume is only valid for implement")
    if not args.brief:
        raise UsageError(f"--brief is required for {mode}")
    if mode == "implement" and args.report:
        print("note: --report is only used by review; ignoring it", file=sys.stderr)

    worktree = resolve_worktree(args.cd)
    inputs = {
        name: _read_input(f"--{name}", getattr(args, name))
        for name in ("brief", "context", "risks", "rules", "report")
    }
    preflight()
    exclude = relative_inputs(
        worktree, (getattr(args, n) for n in ("brief", "context", "risks", "rules", "report"))
    )

    jobs = jobs_dir(os.environ, worktree)
    thread_id = None
    if args.resume:
        prior = read_meta(find_job(jobs, args.resume))
        thread_id = prior.get("thread_id")
        if not thread_id:
            raise UsageError(f"job {args.resume} has no recorded thread_id; cannot resume")
        ignored = [n for n in ("context", "risks", "rules") if inputs[n] is not None]
        if ignored:
            names = ", ".join(f"--{n}" for n in ignored)
            print(f"note: {names} ignored on --resume (the thread has them)", file=sys.stderr)
        prompt = build_resume_prompt(inputs["brief"])
    elif mode == "implement":
        pending = pending_changes(worktree, exclude)
        if pending:
            listing = ", ".join(line[3:] for line in pending[:5])
            raise UsageError(
                f"worktree has uncommitted changes ({listing}); commit them first so Codex's "
                "edits are reviewable on their own (or pass --resume for a fix round)"
            )
        template = (ASSETS / "implement-prompt.md").read_text(encoding="utf-8")
        prompt = build_prompt(
            mode,
            template=template,
            brief=inputs["brief"],
            rules=inputs["rules"],
            context=inputs["context"],
            risks=inputs["risks"],
        )
    else:
        template = (ASSETS / "review-prompt.md").read_text(encoding="utf-8")
        diff = render_diff_section(collect_diff(worktree, args.base, exclude))
        prompt = build_prompt(
            mode,
            template=template,
            brief=inputs["brief"],
            rules=inputs["rules"],
            context=inputs["context"],
            report=inputs["report"],
            risks=inputs["risks"],
            diff=diff,
        )

    jobs.mkdir(parents=True, exist_ok=True)
    prune_jobs(jobs, keep=MAX_JOBS - 1)
    job_id = new_job_id(mode)
    job_dir = jobs / job_id
    job_dir.mkdir()
    argv = build_argv(
        mode,
        worktree=worktree,
        job_dir=job_dir,
        effort=args.effort,
        model=args.model,
        tier=args.tier,
        network=args.network,
        thread_id=thread_id,
    )
    (job_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    write_meta(
        job_dir,
        {
            "id": job_id,
            "mode": mode,
            "worktree": str(worktree),
            "argv": argv,
            "pid": None,
            "status": "running",
            "exit_code": None,
            "thread_id": thread_id,
            "usage": None,
            "session_id": os.environ.get("CLAUDE_CODE_SESSION_ID"),
            "resumed_from": args.resume,
            "created_at": _now(),
            "finished_at": None,
        },
    )
    worker = subprocess.Popen(
        [sys.executable, str(SCRIPT), "_worker", str(job_dir)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    print(f"job {job_id} started ({mode})")
    print(f"dir {job_dir}")
    if not args.wait:
        return 0
    worker.wait()
    print()
    return show_result(job_dir, as_json=False)


def run_worker(job_dir: Path) -> int:
    meta = read_meta(job_dir)
    meta["pid"] = os.getpid()
    write_meta(job_dir, meta)
    with (
        open(job_dir / "prompt.md", "rb") as stdin,
        open(job_dir / "events.jsonl", "wb") as stdout,
        open(job_dir / "stderr.log", "wb") as stderr,
    ):
        try:
            rc = subprocess.call(
                meta["argv"], stdin=stdin, stdout=stdout, stderr=stderr, cwd=meta["worktree"]
            )
        except OSError as e:
            stderr.write(f"failed to run codex: {e}\n".encode())
            rc = 127
    thread_id, usage = parse_events((job_dir / "events.jsonl").read_text(errors="replace"))
    meta = read_meta(job_dir)
    if meta.get("status") == "cancelled":
        return rc
    meta.update(
        status="completed" if rc == 0 else "failed",
        exit_code=rc,
        thread_id=thread_id or meta.get("thread_id"),
        usage=usage,
        finished_at=_now(),
    )
    write_meta(job_dir, meta)
    return rc


def show_result(job_dir: Path, as_json: bool) -> int:
    meta = refresh(job_dir)
    last_path = job_dir / "last.md"
    last = last_path.read_text(encoding="utf-8") if last_path.is_file() else ""
    if as_json:
        print(json.dumps({**meta, "last_message": last}, indent=2))
    elif meta["status"] == "running":
        print(f"job {meta['id']} still running")
    else:
        code = meta.get("exit_code")
        suffix = f" (exit {code})" if code is not None else ""
        print(f"job {meta['id']}: {meta['status']}{suffix}")
        if last.strip():
            print(last.rstrip())
        else:
            err = job_dir / "stderr.log"
            tail = err.read_text(errors="replace").splitlines()[-20:] if err.is_file() else []
            print("(no final message)" + ("; stderr tail:\n" + "\n".join(tail) if tail else ""))
        print(format_usage(meta.get("usage")))
    return {"running": 4, "completed": 0}.get(meta["status"], 1)


def cmd_status(args) -> int:
    jobs = jobs_dir(os.environ, resolve_worktree(args.cd))
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    rows = []
    for job_dir in list_jobs(jobs):
        try:
            meta = refresh(job_dir)
        except (OSError, ValueError):
            continue
        if session and not args.all and meta.get("session_id") != session:
            continue
        rows.append(meta)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print("no jobs")
        return 0
    print(f"{'ID':<34} {'MODE':<10} {'STATUS':<10} CREATED")
    for m in rows:
        print(f"{m['id']:<34} {m['mode']:<10} {m['status']:<10} {m.get('created_at', '')}")
    return 0


def cmd_result(args) -> int:
    jobs = jobs_dir(os.environ, resolve_worktree(args.cd))
    return show_result(find_job(jobs, args.job_id), as_json=args.json)


def cmd_cancel(args) -> int:
    jobs = jobs_dir(os.environ, resolve_worktree(args.cd))
    job_dir = find_job(jobs, args.job_id)
    meta = refresh(job_dir)
    if meta["status"] != "running":
        print(f"job {meta['id']} is already {meta['status']}")
        return 0
    meta.update(status="cancelled", finished_at=_now())
    write_meta(job_dir, meta)
    if meta.get("pid"):
        try:
            os.killpg(meta["pid"], signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    print(f"job {meta['id']} cancelled")
    print("Any edits Codex made are left in the worktree; inspect them with `git status`.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Delegate tasks to codex exec as jobs.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", help="check codex is installed and logged in")

    start = sub.add_parser("start", help="start an implement or review job")
    start.add_argument("mode", choices=("implement", "review"))
    start.add_argument("--effort", required=True, choices=EFFORTS)
    start.add_argument("--model")
    start.add_argument("--tier", help="service_tier")
    start.add_argument("--network", action="store_true", help="allow network (implement)")
    for name in ("brief", "context", "risks", "rules", "report"):
        start.add_argument(f"--{name}", metavar="FILE")
    start.add_argument("--base", help="review: diff against merge-base with REF")
    start.add_argument("--resume", metavar="JOB_ID", help="implement: continue that job's thread")
    start.add_argument("--wait", action="store_true", help="run in the foreground")

    status = sub.add_parser("status", help="list jobs for this worktree")
    status.add_argument("--all", action="store_true", help="include other sessions' jobs")
    status.add_argument("--json", action="store_true")

    result = sub.add_parser("result", help="show a job's final message and usage")
    result.add_argument("job_id", nargs="?", default="last")
    result.add_argument("--json", action="store_true")

    cancel = sub.add_parser("cancel", help="stop a running job")
    cancel.add_argument("job_id")

    for p in (start, status, result, cancel):
        p.add_argument("--cd", metavar="DIR", help="worktree (default: $PROJECT_ROOT or cwd)")

    worker = sub.add_parser("_worker")
    worker.add_argument("job_dir")
    return parser


COMMANDS = {
    "preflight": cmd_preflight,
    "start": cmd_start,
    "status": cmd_status,
    "result": cmd_result,
    "cancel": cmd_cancel,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "_worker":
        return run_worker(Path(args.job_dir))
    try:
        return COMMANDS[args.command](args)
    except UsageError as e:
        print(f"codex_run: {e}", file=sys.stderr)
        return 2
    except PreflightError as e:
        print(f"codex_run: preflight failed: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
