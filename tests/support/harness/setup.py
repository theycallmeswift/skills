import shutil
from collections.abc import Callable
from pathlib import Path

SKILL_PREAMBLE = "Before responding, read and follow skills/{name}/SKILL.md.\n\n"


def skill_setup(skill: str, project_root: Path) -> Callable[[Path], None]:
    """Copy skill dir + AGENTS.md into temp cwd, write preamble file."""

    def _setup(cwd: Path) -> None:
        # Copy skill directory
        skill_dir = project_root / "skills" / skill
        dest_skill = cwd / "skills" / skill
        dest_skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, dest_skill, symlinks=False, dirs_exist_ok=True)

        # Copy AGENTS.md
        agents_src = project_root / "AGENTS.md"
        if agents_src.exists():
            shutil.copy2(agents_src, cwd / "AGENTS.md")

        # Write preamble file for runner to prepend to first turn
        preamble = SKILL_PREAMBLE.format(name=skill)
        (cwd / ".skill_preamble").write_text(preamble)

    return _setup


def copy_files(*paths: str, project_root: Path) -> Callable[[Path], None]:
    """Copy files from project into temp cwd (flat, not preserving directory structure)."""

    def _setup(cwd: Path) -> None:
        for rel_path in paths:
            src = project_root / rel_path
            dest = cwd / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
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
