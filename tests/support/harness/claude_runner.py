"""Claude Code test runner. Invokes `claude -p` and parses stream-json output."""

import dataclasses
import json
import os
import subprocess
import uuid
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class RunResult:
    """Parsed result from a stream-json Claude CLI invocation."""

    events: tuple[dict, ...]
    cost_usd: float
    duration_ms: int
    num_turns: int
    usage: dict
    stop_reason: str

    @property
    def final_output(self) -> str:
        """Final assistant message text."""
        for event in reversed(self.events):
            if event.get("type") != "assistant":
                continue
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    return block["text"]
        return ""

    @property
    def messages(self) -> list[dict]:
        """All assistant and user events, in order."""
        return [e for e in self.events if e.get("type") in ("assistant", "user")]

    @property
    def tool_calls(self) -> list[dict]:
        """All tool_use blocks across all assistant events, in order."""
        calls = []
        for event in self.events:
            if event.get("type") != "assistant":
                continue
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    calls.append({"name": block["name"], "input": block["input"]})
        return calls

    def tool_called(self, name: str, *, where: dict[str, str] | None = None) -> bool:
        """True if any tool call matches the name and optional input filters.

        Args:
            name: Tool name to match.
            where: Optional dict of {input_key: substring} filters.
                   Each value is matched case-insensitively against the
                   corresponding input field.
        """
        for c in self.tool_calls:
            if c["name"] != name:
                continue
            if where is None:
                return True
            if all(
                v.lower() in c["input"].get(k, "").lower()
                for k, v in where.items()
            ):
                return True
        return False

    def not_tool_called(self, name: str, *, where: dict[str, str] | None = None) -> bool:
        """True if no tool call matches the name and optional input filters."""
        return not self.tool_called(name, where=where)

    @property
    def tool_results(self) -> list[dict]:
        """All tool result events, in order."""
        results = []
        for event in self.events:
            if event.get("type") != "user":
                continue
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "tool_result":
                    results.append({
                        "tool_use_id": block.get("tool_use_id"),
                        "content": block.get("content", ""),
                        "structured": event.get("tool_use_result"),
                    })
        return results


def _parse_stream(raw: str) -> RunResult:
    """Parse NDJSON stream-json output into a RunResult."""
    events = []
    metadata = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        parsed = json.loads(line)
        event_type = parsed.get("type")
        if event_type in ("assistant", "user"):
            events.append(parsed)
        elif event_type == "result":
            metadata = parsed

    return RunResult(
        events=tuple(events),
        cost_usd=metadata.get("total_cost_usd", 0.0),
        duration_ms=metadata.get("duration_ms", 0),
        num_turns=metadata.get("num_turns", 0),
        usage=metadata.get("usage", {}),
        stop_reason=metadata.get("stop_reason", ""),
    )


class ClaudeRunner:
    """Runs prompts through Claude CLI and returns parsed RunResult.

    Config hierarchy: explicit kwargs > env vars > defaults.

    Env vars:
        CLAUDE_TEST_MODEL: model name (default: haiku)
        CLAUDE_TEST_TIMEOUT: seconds (default: 30)
        CLAUDE_TEST_CWD: working directory for subprocess
        CLAUDE_TEST_PLUGIN_DIR: plugin directory to load (default: project root)
    """

    def __init__(
        self,
        model: str | None = None,
        timeout: int | None = None,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        plugin_dir: str | Path | None = None,
    ):
        self.model = model or os.environ.get("CLAUDE_TEST_MODEL", "haiku")
        self.timeout = timeout or int(os.environ.get("CLAUDE_TEST_TIMEOUT", "60"))
        self.run_id = uuid.uuid4().hex[:8]
        self.cwd = self._resolve_cwd(cwd)
        self.cwd.mkdir(parents=True, exist_ok=True)
        self.env = {**os.environ, **(env or {})}
        self.plugin_dir = self._resolve_plugin_dir(plugin_dir)

    def _resolve_plugin_dir(self, explicit: str | Path | None) -> Path:
        if explicit:
            return Path(explicit)
        if env_dir := os.environ.get("CLAUDE_TEST_PLUGIN_DIR"):
            return Path(env_dir)
        return Path(__file__).parents[3]

    def _resolve_cwd(self, explicit: str | Path | None) -> Path:
        if explicit:
            return Path(explicit)
        if env_cwd := os.environ.get("CLAUDE_TEST_CWD"):
            return Path(env_cwd)
        project_root = Path(__file__).parents[3]
        return project_root / "tmp" / "tests" / self.run_id

    def run(self, prompt: str) -> RunResult:
        """Run a prompt through `claude -p` and return parsed stream-json result.

        Args:
            prompt: The text prompt to send.

        Returns:
            A RunResult with the full conversation trace and metadata.
        """
        result = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--model",
                self.model,
                "--output-format",
                "stream-json",
                "--verbose",
                "--plugin-dir",
                str(self.plugin_dir),
                "--dangerously-skip-permissions",
            ],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            cwd=self.cwd,
            env=self.env,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"claude -p exited with code {result.returncode}\nstderr: {result.stderr.strip()}"
            )
        return _parse_stream(result.stdout)
