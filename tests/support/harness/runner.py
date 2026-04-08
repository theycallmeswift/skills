import asyncio
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    ToolUseBlock,
)

TURN_SEPARATOR = "\n\n--- turn {n} ---\n\n"


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


@dataclass
class RunResult:
    stdout: str
    files_written: dict[str, str]
    input_tokens: int
    output_tokens: int
    duration_s: float
    exit_code: int  # 0 = success, 1 = error, 124 = timeout
    tool_trace: list[dict] = field(default_factory=list)
    turn_count: int = 1
    error: str | None = None
    # The final contiguous assistant text run (after the last tool use in the
    # last turn). This is what a human user actually sees as "the answer",
    # distinct from `stdout` which concatenates all intermediate narration.
    final_message: str = ""


def build_agent_options(
    cwd: Path,
    project_root: Path,
    model: str | None = None,
) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions, only setting `model` when explicitly provided
    so the SDK default (session model) is preserved otherwise."""
    kwargs: dict = dict(
        cwd=str(cwd),
        plugins=[{"type": "local", "path": str(project_root)}],
        setting_sources=["project"],
        max_buffer_size=64 * 1024 * 1024,
        permission_mode="bypassPermissions",
    )
    if model is not None:
        kwargs["model"] = model
    return ClaudeAgentOptions(**kwargs)


async def run_claude(
    turns: list[str],
    cwd: Path,
    context_paths: list[Path],
    project_root: Path,
    timeout_s: float = 300,
    model: str | None = None,
) -> RunResult:
    """Run a scripted multi-turn conversation through the Claude Agent SDK.

    `turns` is a list of user messages sent sequentially. The agent's responses
    between turns are collected and concatenated into `stdout` with visible
    separators. The entire session shares one timeout.
    """
    if not turns:
        raise ValueError("run_claude requires at least one turn")

    copy_context_paths(context_paths, project_root=project_root, cwd=cwd)
    before = snapshot_files(cwd)

    stdout_parts: list[str] = []
    final_message_parts: list[str] = []
    tool_trace: list[dict] = []
    input_tokens = 0
    output_tokens = 0
    error: str | None = None
    exit_code = 0
    turns_sent = 0

    options = build_agent_options(cwd=cwd, project_root=project_root, model=model)

    start = time.monotonic()
    try:
        async with asyncio.timeout(timeout_s):
            async with ClaudeSDKClient(options=options) as client:
                for i, turn in enumerate(turns, start=1):
                    if len(turns) > 1:
                        stdout_parts.append(TURN_SEPARATOR.format(n=i))
                    # Reset final-message buffer at each new turn; the final
                    # answer is the last contiguous text run in the last turn.
                    final_message_parts = []
                    await client.query(turn)
                    turns_sent = i
                    async for message in client.receive_response():
                        if isinstance(message, AssistantMessage):
                            for block in message.content:
                                if isinstance(block, ToolUseBlock):
                                    tool_trace.append(
                                        {
                                            "name": block.name,
                                            "input": block.input,
                                            "turn": i,
                                        }
                                    )
                                    # Any tool use invalidates the in-progress
                                    # "final answer" — the user's view is only
                                    # the text AFTER the last tool call.
                                    final_message_parts = []
                                elif hasattr(block, "text"):
                                    stdout_parts.append(block.text)
                                    final_message_parts.append(block.text)
                        elif isinstance(message, ResultMessage):
                            usage = getattr(message, "usage", None) or {}
                            input_tokens += usage.get("input_tokens", 0)
                            output_tokens += usage.get("output_tokens", 0)
    except TimeoutError:
        exit_code = 124
        error = f"timed out after {timeout_s}s (on turn {turns_sent or 1}/{len(turns)})"
    except Exception as e:  # noqa: BLE001
        exit_code = 1
        error = f"{type(e).__name__}: {e}"

    duration = time.monotonic() - start
    files_written = capture_changes(cwd, before)

    return RunResult(
        stdout="".join(stdout_parts),
        files_written=files_written,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        duration_s=duration,
        exit_code=exit_code,
        tool_trace=tool_trace,
        turn_count=len(turns),
        error=error,
        final_message="".join(final_message_parts),
    )
