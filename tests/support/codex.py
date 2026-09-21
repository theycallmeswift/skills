"""Workspaces and process helpers for codex wrapper tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias, TypedDict, cast

import pytest
from codexrun import SCRIPT
from codexrun.cli import main
from codexrun.git import DiffInfo, resolve_worktree
from codexrun.state import GateResult, JobMeta, Usage, jobs_dir, now

GIT = [
    "git",
    "-c",
    "user.name=t",
    "-c",
    "user.email=t@example.com",
    "-c",
    "commit.gpgsign=false",
]
HOST_ENV = (
    "CODEX_THREAD_ID",
    "CLAUDE_CODE_SESSION_ID",
    "HERMES_HOME",
    "XDG_STATE_HOME",
    "PROJECT_ROOT",
)
JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
JobMetaValue: TypeAlias = str | int | list[str] | Usage | GateResult | None


class CodexCall(TypedDict):
    """One invocation recorded by the fake Codex executable."""

    argv: list[str]
    stdin: str
    cwd: str
    pid: int


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run the wrapper CLI in a subprocess."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@dataclass
class Run:
    """Captured result of an in-process CLI invocation."""

    return_code: int
    stdout: str
    stderr: str

    @property
    def job_id(self) -> str:
        """Extract the started job identifier from stdout."""
        for line in self.stdout.splitlines():
            if line.startswith("job "):
                return line.split()[1]
        raise AssertionError(f"no job id in: {self.stdout!r}")


class Workspace:
    """Git repository, fake Codex process, and captured CLI state for unit tests."""

    def __init__(self, root: Path, capsys: pytest.CaptureFixture[str]):
        """Initialize paths and common input files below a temporary root."""
        self.root = root
        self.repo = root / "repo"
        self.inputs = root / "inputs"
        self.log = root / "codex.log"
        self._capsys = capsys
        self.brief = self.write_input("brief.md", "Make x equal 2.\n")
        self.risks = self.write_input("risks.md", "R1: x must stay an int.\n")

    def git(self, *args: str) -> str:
        """Run Git in the workspace repository and return stdout."""
        command = [*GIT, "-C", str(self.repo), *args]
        return subprocess.run(command, check=True, capture_output=True, text=True).stdout

    def head(self) -> str:
        """Return the repository's current commit identifier."""
        return self.git("rev-parse", "HEAD").strip()

    def write(self, name: str, text: str) -> Path:
        """Write a file relative to the repository."""
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def write_input(self, name: str, text: str) -> str:
        """Write an orchestrator input file and return its path as text."""
        self.inputs.mkdir(exist_ok=True)
        path = self.inputs / name
        path.write_text(text)
        return str(path)

    def run(self, *argv: str) -> Run:
        """Invoke the CLI in-process and capture its streams."""
        return_code = main(list(argv))
        captured = self._capsys.readouterr()
        return Run(return_code, captured.out, captured.err)

    def start(
        self,
        *extra: str,
        effort: str = "low",
        brief: str | None = None,
    ) -> Run:
        """Invoke the start command with the common brief and effort defaults."""
        return self.run(
            "start",
            "--effort",
            effort,
            "--brief",
            brief or self.brief,
            *extra,
        )

    def calls(self) -> list[CodexCall]:
        """Read calls recorded by the fake Codex executable."""
        if not self.log.exists():
            return []
        return [cast(CodexCall, json.loads(line)) for line in self.log.read_text().splitlines()]

    @property
    def jobs(self) -> Path:
        """Return this workspace's persistent jobs directory."""
        return jobs_dir(os.environ, resolve_worktree(str(self.repo)))

    def meta(self, job_id: str) -> JobMeta:
        """Read metadata for a recorded job."""
        return cast(JobMeta, json.loads((self.jobs / job_id / "meta.json").read_text()))

    def edit_meta(self, job_id: str, **changes: JobMetaValue) -> None:
        """Apply selected metadata changes directly for a test setup."""
        updated_meta = cast(JobMeta, {**self.meta(job_id), **changes})
        (self.jobs / job_id / "meta.json").write_text(json.dumps(updated_meta))

    def wait_until(self, condition: Callable[[], bool], timeout: float = 15) -> None:
        """Poll a condition until it succeeds or the timeout expires."""
        deadline = time.time() + timeout
        while not condition():
            if time.time() > deadline:
                raise AssertionError("timed out waiting")
            time.sleep(0.05)

    def wait_done(self, job_id: str) -> JobMeta:
        """Wait for a job to leave the running state and return its metadata."""
        self.wait_until(lambda: self.meta(job_id)["status"] != "running")
        return self.meta(job_id)


class Repo:
    """Subprocess-oriented repository used by real CLI contract tests."""

    def __init__(self, root: Path):
        """Initialize repository, input, and isolated state paths."""
        self.path = root / "repo"
        self.inputs = root / "inputs"
        self.env: dict[str, str] = dict(os.environ)
        self.env["CLAUDE_PLUGIN_DATA"] = str(root / "state")
        self.env.pop("CODEX_THREAD_ID", None)

    def git(self, *args: str) -> str:
        """Run Git in the repository and return stdout."""
        command = [*GIT, "-C", str(self.path), *args]
        return subprocess.run(command, check=True, capture_output=True, text=True).stdout

    def input(self, name: str, text: str) -> str:
        """Write an input file and return its path as text."""
        self.inputs.mkdir(exist_ok=True)
        path = self.inputs / name
        path.write_text(text)
        return str(path)

    def codex_run(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run the wrapper CLI and require a successful exit."""
        command: list[str] = [sys.executable, str(SCRIPT), *args, "--cd", str(self.path)]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=self.env,
            timeout=600,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    def start(self, brief: str, *extra: str) -> str:
        """Run a foreground job and return its identifier."""
        result = self.codex_run(
            "start",
            "--effort",
            "low",
            "--brief",
            brief,
            *extra,
            "--wait",
        )
        return next(
            line.split()[1] for line in result.stdout.splitlines() if line.startswith("job ")
        )


def job_meta(**overrides: JobMetaValue) -> JobMeta:
    """Build job metadata, leaving the call site only the fields its test turns on."""
    defaults: JobMeta = {
        "id": "job",
        "template": "implement",
        "worktree": ".",
        "argv": ["codex"],
        "pid": None,
        "status": "running",
        "exit_code": None,
        "thread_id": None,
        "usage": None,
        "session_id": None,
        "resumed_from": None,
        "gate_command": None,
        "created_at": now(),
        "finished_at": None,
    }
    return cast(JobMeta, {**defaults, **overrides})


def jsonl(*events: JsonObject) -> str:
    """Encode event objects as a JSONL stream."""
    return "\n".join(json.dumps(event) for event in events)


def headings(prompt: str) -> list[str]:
    """Extract section headings from a rendered prompt."""
    return [line.strip("= ") for line in prompt.splitlines() if line.startswith("=== ")]


def diff_info(files: list[str], text: str) -> DiffInfo:
    """Build concise diff metadata for prompt tests."""
    return DiffInfo(label="scope", files=files, text=text, commands=["git diff abc123"])


def make_jobs(root: Path, count: int) -> None:
    """Create timestamped job fixtures beneath a state directory."""
    for index in range(count):
        job = root / f"job{index:02d}"
        job.mkdir()
        created_at = f"2026-01-01T00:00:{index:02d}"
        (job / "meta.json").write_text(json.dumps({"created_at": created_at}))


def commit_on_feature_branch(workspace: Workspace, files: dict[str, str]) -> str:
    """Commit files on a new feature branch and return the prior commit."""
    base = workspace.head()
    workspace.git("checkout", "-q", "-b", "feature")

    for name, text in files.items():
        workspace.write(name, text)

    workspace.git("add", ".")
    workspace.git("commit", "-q", "-m", "feature")
    return base


def pid_alive(pid: int) -> bool:
    """Return whether a process identifier still exists."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
