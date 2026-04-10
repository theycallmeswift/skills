"""Generic Claude Code test runner. Invokes `claude -p` as a subprocess."""

import os
import subprocess
import uuid
from pathlib import Path


class ClaudeRunner:
    """Runs prompts through Claude CLI and returns text output.

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

    def run(self, prompt: str) -> str:
        """Run a prompt through `claude -p` and return stripped stdout.

        Args:
            prompt: The text prompt to send.

        Returns:
            The CLI's stdout, stripped of leading/trailing whitespace.
        """
        result = subprocess.run(
            [
                "claude",
                "-p",
                prompt,
                "--model",
                self.model,
                "--output-format",
                "text",
                "--plugin-dir",
                str(self.plugin_dir),
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
        return result.stdout.strip()
