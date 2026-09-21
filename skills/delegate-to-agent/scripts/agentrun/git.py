"""Read-only git queries: the worktree, its pending changes, and the diff to hand over."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from agentrun import UsageError


@dataclass
class DiffInfo:
    """Git diff content and the commands that reproduce it."""

    label: str
    files: list[str]
    text: str
    commands: list[str]
    untracked: list[str] = field(default_factory=list)


def git(worktree: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a Git command against a worktree."""
    return subprocess.run(
        ["git", "-C", str(worktree), *args], capture_output=True, text=True, check=check
    )


def resolve_worktree(cd: str | None) -> Path:
    """Resolve the canonical Git worktree from CLI and environment inputs."""
    start = cd or os.environ.get("PROJECT_ROOT") or os.getcwd()

    try:
        result = git(Path(start), "rev-parse", "--show-toplevel", check=False)
    except (FileNotFoundError, NotADirectoryError) as error:
        raise UsageError(f"cannot run git in {start}: {error}") from error

    if result.returncode != 0:
        raise UsageError(f"not a git repository: {start}")
    return Path(os.path.realpath(result.stdout.strip()))


def relative_inputs(worktree: Path, paths: Iterable[str | None]) -> frozenset[str]:
    """Repo-relative paths of the input files that live inside the worktree."""
    relative = set()

    for path in paths:
        if path is None:
            continue

        real = Path(os.path.realpath(path))
        if real.is_relative_to(worktree):
            relative.add(real.relative_to(worktree).as_posix())

    return frozenset(relative)


def pending_changes(worktree: Path, exclude: frozenset[str] = frozenset()) -> list[str]:
    """`git status --porcelain` entries, minus the job's own input files.

    Briefs and risk files often sit inside the worktree; they must not make it look dirty.
    """
    out = git(worktree, "status", "--porcelain", "--untracked-files=all").stdout
    return [line for line in out.splitlines() if line[3:] not in exclude]


def collect_diff(
    worktree: Path, base: str | None, exclude: frozenset[str] = frozenset()
) -> DiffInfo:
    """Collect the diff a job should inspect.

    Args:
        worktree: Repository worktree to inspect.
        base: Optional base reference for a branch diff.
        exclude: Repository-relative input files to omit from pending changes.

    Returns:
        Diff content, changed paths, label, and reproduction commands.

    Raises:
        UsageError: If the selected scope contains no changes.
    """
    listed = git(worktree, "ls-files", "--others", "--exclude-standard").stdout.split()
    untracked = [filename for filename in listed if filename not in exclude]
    revision, label, commands = _diff_target(worktree, base, exclude, untracked)
    files = git(worktree, "diff", revision, "--name-only").stdout.split()

    if not files and not untracked:
        raise UsageError(f"nothing to diff: no changes ({label})")

    text = git(worktree, "diff", revision).stdout
    return DiffInfo(label=label, files=files, text=text, commands=commands, untracked=untracked)


def _diff_target(
    worktree: Path,
    base: str | None,
    exclude: frozenset[str],
    untracked: list[str],
) -> tuple[str, str, list[str]]:
    """Choose the revision, label, and commands for the requested diff."""
    if base is None and pending_changes(worktree, exclude):
        return (
            "HEAD",
            "uncommitted changes",
            ["git diff HEAD", "git ls-files --others --exclude-standard"],
        )

    reference = base or _default_base(worktree)
    revision = _merge_base(worktree, reference)
    commands = [f"git diff {revision}", f"git diff --stat {revision}"]
    if untracked:
        commands.append("git ls-files --others --exclude-standard")

    label = f"changes since merge-base with {reference}"
    return revision, label, commands


def _default_base(worktree: Path) -> str:
    """Return the first available conventional base branch."""
    for reference in ("origin/HEAD", "main", "master"):
        if (
            git(
                worktree,
                "rev-parse",
                "--verify",
                "--quiet",
                reference,
                check=False,
            ).returncode
            == 0
        ):
            return reference

    raise UsageError("no base branch found (origin/HEAD, main, master); pass --base REF")


def _merge_base(worktree: Path, ref: str) -> str:
    """Resolve the merge base between HEAD and a reference."""
    result = git(worktree, "merge-base", "HEAD", ref, check=False)
    if result.returncode != 0:
        raise UsageError(f"cannot find merge-base of HEAD and {ref}")
    return result.stdout.strip()
