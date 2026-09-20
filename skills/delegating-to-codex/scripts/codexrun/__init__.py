"""Job manager behind codex_run.py: delegates tasks to `codex exec` as background jobs."""

from __future__ import annotations

from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "codex_run.py"
ASSETS = SCRIPT.parent.parent / "assets"


class UsageError(Exception):
    """Bad invocation or input; exit 2."""


class PreflightError(Exception):
    """Environment can't run Codex; exit 3."""
