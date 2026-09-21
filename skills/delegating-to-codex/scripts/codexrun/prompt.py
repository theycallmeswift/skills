"""The prompt Codex reads on stdin: task template plus the orchestrator's inputs."""

from __future__ import annotations

from codexrun.git import DiffInfo

INLINE_MAX_FILES = 2
INLINE_MAX_BYTES = 256 * 1024
RESUME_HEADER = (
    "Follow-up from the orchestrator on the task above. Apply the fixes below under the "
    "same rules: leave changes in the working tree (no git add/commit/stash/checkout), "
    "and end with the same STATUS final message.\n"
)


def build_prompt(
    *,
    template: str | None,
    brief: str,
    rules: str | None = None,
    context: str | None = None,
    report: str | None = None,
    risks: str | None = None,
    diff: str | None = None,
) -> str:
    """Build a complete delegation prompt.

    Args:
        template: Optional task template the job follows.
        brief: Task-specific instructions.
        rules: Optional rules supplied by the orchestrator.
        context: Optional supporting context.
        report: Optional implementer report to review.
        risks: Optional named risks.
        diff: Optional diff description.

    Returns:
        Populated sections in their required reading order.
    """
    sections = [
        ("TASK TEMPLATE", template),
        ("RULES", rules),
        ("BRIEF", brief),
        ("CONTEXT", context),
        ("IMPLEMENTER REPORT", report),
        ("NAMED RISKS", risks),
        ("DIFF", diff),
    ]
    populated_sections = (_section(name, text) for name, text in sections if text is not None)
    return "\n".join(populated_sections)


def build_resume_prompt(brief: str) -> str:
    """Build the compact follow-up prompt for a resumed thread."""
    return RESUME_HEADER + "\n" + _section("BRIEF", brief)


def render_diff_section(info: DiffInfo) -> str:
    """Inline a small diff; for a large one, hand Codex the commands to inspect it."""
    all_files = info.files + [f"{filename} (untracked)" for filename in info.untracked]
    listing = "\n".join(f"- {filename}" for filename in all_files)
    size = len(info.text.encode())

    if len(all_files) <= INLINE_MAX_FILES and size <= INLINE_MAX_BYTES:
        return _inline_diff(info, listing)

    return _large_diff(info, listing, file_count=len(all_files), size=size)


def _inline_diff(info: DiffInfo, listing: str) -> str:
    """Render a small diff inline with its changed-file listing."""
    introduction = f"Scope: {info.label}\nChanged files:\n{listing}\n\n"
    untracked_note = ""
    if info.untracked:
        untracked_note = "Untracked files are new and not in the diff; read them directly.\n\n"

    return introduction + untracked_note + f"Diff (from `{info.commands[0]}`):\n{info.text}"


def _large_diff(info: DiffInfo, listing: str, *, file_count: int, size: int) -> str:
    """Render commands for inspecting a diff that is too large to inline."""
    commands = "\n".join(f"  {command}" for command in info.commands)
    return (
        f"Scope: {info.label}\n"
        f"The diff is too large to inline ({file_count} files, {size // 1024} KB). "
        f"Inspect it yourself with read-only git:\n{commands}\n"
        "Read untracked files directly.\n\n"
        f"Changed files:\n{listing}\n"
    )


def _section(name: str, text: str) -> str:
    """Render a named prompt section."""
    return f"=== {name} ===\n{text.strip()}\n"
