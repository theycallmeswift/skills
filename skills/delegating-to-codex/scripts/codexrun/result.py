"""What a finished job reports back: a bounded final message, its usage, and the gate verdict."""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

from codexrun.events import format_usage
from codexrun.state import (
    GATE_LOG,
    LAST_MESSAGE,
    STDERR_LOG,
    GateResult,
    GateStatus,
    JobMeta,
    refresh,
)

EXIT_BY_STATUS = {"running": 4, "completed": 0}
# A gate that failed or could not run outranks the delegate's own clean exit.
GATE_FAILURE_EXIT_CODE = 5
GATE_FAILURE_STATUSES: tuple[GateStatus, ...] = ("failed", "error")
# What a final message may spend of the orchestrating agent's context. The terminal could
# take far more; the context window the result lands in is the scarce resource.
RESULT_MAX_BYTES = 16 * 1024
# Back up to the last line break this close to the cut so the head ends on a whole line.
NEWLINE_LOOKBACK_CHARS = 512


class CappedMessage(NamedTuple):
    """Codex's final message, trimmed to the byte cap when it ran past it.

    Attributes:
        text: The message, or its head when it exceeded the cap.
        full_bytes: Size of the untrimmed message, or None when nothing was trimmed.
    """

    text: str
    full_bytes: int | None


def show_result(job_dir: Path, *, as_json: bool) -> int:
    """Print a job result and return its status-specific exit code."""
    meta = refresh(job_dir)
    message = _cap_message(_last_message(job_dir))

    if as_json:
        truncation = _truncation_fields(job_dir, message)
        print(json.dumps({**meta, "last_message": message.text, **truncation}, indent=2))
    else:
        _print_result(job_dir, meta, message)

    return _exit_code(meta)


def _exit_code(meta: JobMeta) -> int:
    """Map a job to its exit code, reporting a gate verdict ahead of the delegate's own."""
    gate = meta.get("gate")
    if gate and gate["status"] in GATE_FAILURE_STATUSES:
        return GATE_FAILURE_EXIT_CODE

    return EXIT_BY_STATUS.get(meta["status"], 1)


def _last_message(job_dir: Path) -> str:
    """Read Codex's final message when one was written."""
    message_path = job_dir / LAST_MESSAGE
    if not message_path.is_file():
        return ""
    return message_path.read_text(encoding="utf-8")


def _cap_message(message: str) -> CappedMessage:
    """Trim a final message to the byte cap, on a line boundary when one is near the cut."""
    encoded = message.encode("utf-8")
    if len(encoded) <= RESULT_MAX_BYTES:
        return CappedMessage(message, full_bytes=None)

    # Ignoring the errors drops a character the cut landed inside, rather than raising
    # or leaving a replacement character behind.
    head = encoded[:RESULT_MAX_BYTES].decode("utf-8", errors="ignore")

    last_line_break = head.rfind("\n")
    if last_line_break != -1 and last_line_break >= len(head) - NEWLINE_LOOKBACK_CHARS:
        head = head[:last_line_break]

    return CappedMessage(head, full_bytes=len(encoded))


def _truncation_pointer(job_dir: Path, message: CappedMessage) -> str:
    """Point at the untrimmed message on disk, or return nothing to add when it all fit."""
    if message.full_bytes is None:
        return ""

    size = _kilobytes(message.full_bytes)
    return f"... truncated ({size}); full message: {job_dir / LAST_MESSAGE}"


def _truncation_fields(job_dir: Path, message: CappedMessage) -> dict[str, str | bool]:
    """Name the file holding the untrimmed message, or return nothing to add when it all fit."""
    if message.full_bytes is None:
        return {}

    return {"last_message_truncated": True, "last_message_path": str(job_dir / LAST_MESSAGE)}


def _kilobytes(byte_count: int) -> str:
    """Render a size in KB, keeping a decimal while a whole number would round the cut away."""
    kilobytes = byte_count / 1024
    if kilobytes >= 100:
        return f"{kilobytes:.0f} KB"

    return f"{kilobytes:.1f} KB"


def _print_result(job_dir: Path, meta: JobMeta, message: CappedMessage) -> None:
    """Print a human-readable terminal result."""
    if meta["status"] == "running":
        print(f"job {meta['id']} still running")
        return

    exit_code = meta.get("exit_code")
    exit_suffix = f" (exit {exit_code})" if exit_code is not None else ""

    print(f"job {meta['id']}: {meta['status']}{exit_suffix}")
    _print_answer(job_dir, meta, message)
    print(format_usage(meta.get("usage")))

    gate = meta.get("gate")
    if gate:
        print(_gate_line(job_dir, gate))


def _print_answer(job_dir: Path, meta: JobMeta, message: CappedMessage) -> None:
    """Print the delegate's final message, or what stands in for it when there is none."""
    if not message.text.strip():
        print(meta.get("error") or _no_message(job_dir))
        return

    print(message.text.rstrip())

    pointer = _truncation_pointer(job_dir, message)
    if pointer:
        print(pointer)


def _gate_line(job_dir: Path, gate: GateResult) -> str:
    """Summarize the gate in one line, pointing at its log only when the log holds more."""
    command = gate["command"]
    status = gate["status"]

    if status == "passed":
        return f"gate: passed - {command}"

    if status == "skipped":
        return f"gate: skipped (job failed) - {command}"

    if status == "error":
        return f"gate: error ({gate.get('reason', 'could not run')}) - {command}"

    exit_code = gate.get("exit_code")
    exit_suffix = f" (exit {exit_code})" if exit_code is not None else ""
    return f"gate: failed{exit_suffix} - {command}; output: {job_dir / GATE_LOG}"


def _no_message(job_dir: Path) -> str:
    """Explain a missing final message by pointing at stderr; diagnostics are not an answer."""
    stderr_path = job_dir / STDERR_LOG
    if not stderr_path.is_file():
        return "(no final message)"

    return f"(no final message); stderr: {stderr_path}"
