"""The exact `codex exec` argv for a job."""

from __future__ import annotations

from pathlib import Path

EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")
READ_ONLY_SANDBOX = "read-only"
WRITABLE_SANDBOX = "workspace-write"
SANDBOXES = (READ_ONLY_SANDBOX, WRITABLE_SANDBOX)
EXEC_FLAGS = ["--json", "--strict-config"]


def writes_to_disk(sandbox: str) -> bool:
    """Whether Codex may change the worktree under this sandbox."""
    return sandbox == WRITABLE_SANDBOX


def build_argv(
    *,
    worktree: Path,
    job_dir: Path,
    effort: str,
    sandbox: str = WRITABLE_SANDBOX,
    model: str | None = None,
    tier: str | None = None,
    network: bool = False,
    thread_id: str | None = None,
    schema: Path | None = None,
) -> list[str]:
    """Build the exact ``codex exec`` command for a job.

    Args:
        worktree: Repository worktree in which Codex runs.
        job_dir: State directory that receives Codex's final message.
        effort: Model reasoning effort setting.
        sandbox: Codex sandbox the job runs under.
        model: Optional model override.
        tier: Optional service tier override.
        network: Whether the job may access the network.
        thread_id: Existing Codex thread to resume.
        schema: Optional JSON schema the final message must satisfy.

    Returns:
        The complete subprocess argument vector.

    Raises:
        ValueError: If the sandbox is unknown.
    """
    if sandbox not in SANDBOXES:
        raise ValueError(f"unknown sandbox: {sandbox}")

    command = (
        _resume_command(thread_id, sandbox) if thread_id else _fresh_command(worktree, sandbox)
    )

    return [
        *command,
        *_task_settings(effort, model=model, tier=tier),
        *_network_settings(network),
        *_schema_settings(schema),
        "-o",
        str(job_dir / "last.md"),
        "-",
    ]


def _fresh_command(worktree: Path, sandbox: str) -> list[str]:
    """Build the command and sandbox flags for a fresh job."""
    return ["codex", "exec", "--sandbox", sandbox, "--cd", str(worktree), *EXEC_FLAGS]


def _resume_command(thread_id: str, sandbox: str) -> list[str]:
    """Build the command and sandbox settings for a resumed thread."""
    # Resume accepts sandbox config but not the --sandbox or --cd flags.
    return [
        "codex",
        "exec",
        "resume",
        thread_id,
        *EXEC_FLAGS,
        "-c",
        f'sandbox_mode="{sandbox}"',
    ]


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


def _schema_settings(schema: Path | None) -> list[str]:
    """Require a schema-shaped final message when the caller asked for one."""
    if schema is None:
        return []
    return ["--output-schema", str(schema)]
