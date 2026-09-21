"""Fixtures for the agentrun test package."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from support import fake_codex
from support.codex import HOST_ENV, Workspace

FAKE_CODEX = Path(fake_codex.__file__)


@pytest.fixture
def ws(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> Workspace:
    """Build a clean Git workspace backed by the fake Codex executable."""
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "codex").symlink_to(FAKE_CODEX)

    for variable in HOST_ENV:
        monkeypatch.delenv(variable, raising=False)

    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "state"))
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ['PATH']}")

    workspace = Workspace(tmp_path, capsys)
    monkeypatch.setenv("FAKE_CODEX_LOG", str(workspace.log))
    workspace.repo.mkdir()
    workspace.git("init", "-q", "-b", "main")
    workspace.write("a.py", "x = 1\n")
    workspace.git("add", ".")
    workspace.git("commit", "-q", "-m", "init")
    monkeypatch.chdir(workspace.repo)
    return workspace
