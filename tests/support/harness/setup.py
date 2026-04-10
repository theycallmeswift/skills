import shutil
from collections.abc import Callable
from pathlib import Path

SKILL_PREAMBLE = "Before responding, read and follow skills/{name}/SKILL.md.\n\n"


def skill_setup(skill: str, project_root: Path) -> Callable[[Path], None]:
    """Write a preamble that ensures the agent activates the named skill.

    The plugin is already loaded via ClaudeAgentOptions (see runner.py),
    so the agent has access to all skills. The preamble ensures the
    specific skill is used regardless of trigger matching.
    """

    def _setup(cwd: Path) -> None:
        preamble = SKILL_PREAMBLE.format(name=skill)
        (cwd / ".skill_preamble").write_text(preamble)

    return _setup


def copy_files(*paths: str, project_root: Path) -> Callable[[Path], None]:
    """Copy files/directories from project into temp cwd, preserving relative paths."""

    def _setup(cwd: Path) -> None:
        for rel_path in paths:
            src = project_root / rel_path
            dest = cwd / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dest, symlinks=False, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dest)

    return _setup


def cleanup_globs(*patterns: str) -> Callable[[Path], None]:
    """Delete files matching globs relative to the directory passed in."""

    def _cleanup(cwd: Path) -> None:
        for pattern in patterns:
            for match in cwd.glob(pattern):
                if match.is_dir():
                    shutil.rmtree(match, ignore_errors=True)
                else:
                    match.unlink(missing_ok=True)

    return _cleanup


def compose(*fns: Callable[[Path], None]) -> Callable[[Path], None]:
    """Run multiple setup/cleanup functions in sequence."""

    def _composed(cwd: Path) -> None:
        for fn in fns:
            fn(cwd)

    return _composed
