"""Check that this environment can run Codex."""

from __future__ import annotations

import os
import shutil
import subprocess

from codexrun import PreflightError


def preflight() -> None:
    """Verify that the current environment can launch Codex.

    Raises:
        PreflightError: If delegation is nested, Codex is missing, login checks time out,
            or Codex is logged out.
    """
    if os.environ.get("CODEX_THREAD_ID"):
        raise PreflightError("already running inside Codex; do the work directly")

    if not shutil.which("codex"):
        raise PreflightError("`codex` not found on PATH; install the Codex CLI first")

    try:
        result = subprocess.run(["codex", "login", "status"], capture_output=True, timeout=60)
    except subprocess.TimeoutExpired as error:
        raise PreflightError("`codex login status` timed out; check the Codex CLI") from error

    if result.returncode != 0:
        raise PreflightError("Codex is not logged in; run `codex login`")
