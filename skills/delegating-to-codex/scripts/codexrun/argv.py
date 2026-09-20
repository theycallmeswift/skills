"""The exact `codex exec` argv for a job."""

from __future__ import annotations

from pathlib import Path

from codexrun import ASSETS

EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")
EXEC_FLAGS = ["--json", "--strict-config"]


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
    """Build the exact ``codex exec`` command for a job.

    Args:
        mode: Job mode, either ``implement`` or ``review``.
        worktree: Repository worktree in which Codex runs.
        job_dir: State directory that receives Codex's final message.
        effort: Model reasoning effort setting.
        model: Optional model override.
        tier: Optional service tier override.
        network: Whether an implementation job may access the network.
        thread_id: Existing Codex thread to resume.
        schema: Optional review output schema override.

    Returns:
        The complete subprocess argument vector.

    Raises:
        ValueError: If the mode is unknown or review-only constraints are violated.
    """
    _validate(mode, network=network, thread_id=thread_id)

    task_settings = _task_settings(effort, model=model, tier=tier)
    network_settings = _network_settings(network)
    output_flags = ["-o", str(job_dir / "last.md"), "-"]

    if thread_id:
        return _resume_argv(thread_id, task_settings, network_settings, output_flags)

    if mode == "implement":
        return _implement_argv(worktree, task_settings, network_settings, output_flags)

    output_schema = schema or ASSETS / "review-output.schema.json"
    return _review_argv(worktree, output_schema, task_settings, output_flags)


def _validate(mode: str, *, network: bool, thread_id: str | None) -> None:
    """Validate mode-specific command options."""
    if mode == "review" and (network or thread_id):
        raise ValueError("review runs read-only and fresh: no network, no resume")
    if mode not in ("implement", "review"):
        raise ValueError(f"unknown mode: {mode}")


def _task_settings(effort: str, *, model: str | None, tier: str | None) -> list[str]:
    """Build explicit model task settings."""
    settings = ["-c", f"model_reasoning_effort={effort}"]
    if tier:
        settings.extend(["-c", f"service_tier={tier}"])
    if model:
        settings.extend(["-m", model])
    return settings


def _network_settings(enabled: bool) -> list[str]:
    """Build the workspace-write network configuration when enabled."""
    if not enabled:
        return []
    return ["-c", "sandbox_workspace_write.network_access=true"]


def _resume_argv(
    thread_id: str,
    task_settings: list[str],
    network_settings: list[str],
    output_flags: list[str],
) -> list[str]:
    """Build argv for resuming an implementation thread."""
    # Resume accepts sandbox config but not the --sandbox or --cd flags.
    sandbox_setting = ["-c", 'sandbox_mode="workspace-write"']
    return [
        "codex",
        "exec",
        "resume",
        thread_id,
        *EXEC_FLAGS,
        *sandbox_setting,
        *task_settings,
        *network_settings,
        *output_flags,
    ]


def _implement_argv(
    worktree: Path,
    task_settings: list[str],
    network_settings: list[str],
    output_flags: list[str],
) -> list[str]:
    """Build argv for a fresh implementation job."""
    sandbox_flags = ["--sandbox", "workspace-write", "--cd", str(worktree)]
    return [
        "codex",
        "exec",
        *sandbox_flags,
        *EXEC_FLAGS,
        *task_settings,
        *network_settings,
        *output_flags,
    ]


def _review_argv(
    worktree: Path,
    schema: Path,
    task_settings: list[str],
    output_flags: list[str],
) -> list[str]:
    """Build argv for a fresh read-only review job."""
    sandbox_flags = ["--sandbox", "read-only", "--ephemeral", "--cd", str(worktree)]
    return [
        "codex",
        "exec",
        *sandbox_flags,
        *EXEC_FLAGS,
        *task_settings,
        "--output-schema",
        str(schema),
        *output_flags,
    ]
