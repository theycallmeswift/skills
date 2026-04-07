import shutil
from pathlib import Path


def copy_context_paths(paths: list[Path], project_root: Path, cwd: Path) -> None:
    """Copy each path into cwd preserving its position relative to project_root.

    Symlinks are resolved (we copy the target, not the link).
    """
    for src in paths:
        resolved = src.resolve()
        rel = src.relative_to(project_root) if src.is_absolute() else src
        dest = cwd / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if resolved.is_dir():
            shutil.copytree(resolved, dest, symlinks=False, dirs_exist_ok=True)
        else:
            shutil.copy2(resolved, dest)


def snapshot_files(cwd: Path) -> dict[str, tuple[float, int]]:
    """Return {relative_path: (mtime, size)} for every file under cwd."""
    snap: dict[str, tuple[float, int]] = {}
    for p in cwd.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(cwd))
            stat = p.stat()
            snap[rel] = (stat.st_mtime, stat.st_size)
    return snap


def capture_changes(cwd: Path, before: dict[str, tuple[float, int]]) -> dict[str, str]:
    """Return {relative_path: content} for files added or modified since `before`."""
    changes: dict[str, str] = {}
    for p in cwd.rglob("*"):
        if not p.is_file():
            continue
        rel = str(p.relative_to(cwd))
        stat = p.stat()
        prev = before.get(rel)
        if prev is None or prev != (stat.st_mtime, stat.st_size):
            try:
                changes[rel] = p.read_text()
            except UnicodeDecodeError:
                changes[rel] = f"<binary file, {stat.st_size} bytes>"
    return changes
