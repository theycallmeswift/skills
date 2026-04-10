import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.support.harness.claude_runner import ClaudeRunner


class TestClaudeRunnerInit:
    def test_default_model_is_haiku(self):
        runner = ClaudeRunner()
        assert runner.model == "haiku"

    def test_default_timeout_is_60(self):
        runner = ClaudeRunner()
        assert runner.timeout == 60

    def test_custom_model(self):
        runner = ClaudeRunner(model="sonnet")
        assert runner.model == "sonnet"

    def test_custom_timeout(self):
        runner = ClaudeRunner(timeout=60)
        assert runner.timeout == 60

    def test_run_id_is_8_hex_chars(self):
        runner = ClaudeRunner()
        assert len(runner.run_id) == 8
        int(runner.run_id, 16)  # raises if not hex

    def test_default_cwd_under_tmp(self):
        runner = ClaudeRunner()
        assert "tmp/tests" in str(runner.cwd)
        assert runner.run_id in str(runner.cwd)

    def test_cwd_from_env(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_CWD": "/tmp/custom"}):
            runner = ClaudeRunner()
            assert runner.cwd == Path("/tmp/custom")

    def test_explicit_cwd_overrides_env(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_CWD": "/tmp/custom"}):
            runner = ClaudeRunner(cwd="/tmp/explicit")
            assert runner.cwd == Path("/tmp/explicit")

    def test_env_overrides_for_model_and_timeout(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_MODEL": "sonnet", "CLAUDE_TEST_TIMEOUT": "60"}):
            runner = ClaudeRunner()
            assert runner.model == "sonnet"
            assert runner.timeout == 60

    def test_explicit_kwargs_override_env(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_MODEL": "sonnet", "CLAUDE_TEST_TIMEOUT": "60"}):
            runner = ClaudeRunner(model="haiku", timeout=10)
            assert runner.model == "haiku"
            assert runner.timeout == 10

    def test_default_plugin_dir_is_project_root(self):
        runner = ClaudeRunner()
        assert runner.plugin_dir.name in ("mechaswift", "testing-eval-strategy")
        assert (runner.plugin_dir / "pyproject.toml").exists()

    def test_explicit_plugin_dir(self):
        runner = ClaudeRunner(plugin_dir="/tmp/my-plugin")
        assert runner.plugin_dir == Path("/tmp/my-plugin")

    def test_plugin_dir_from_env(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_PLUGIN_DIR": "/tmp/env-plugin"}):
            runner = ClaudeRunner()
            assert runner.plugin_dir == Path("/tmp/env-plugin")


class TestClaudeRunnerRun:
    def test_run_calls_subprocess_with_correct_args(self):
        runner = ClaudeRunner(model="haiku", timeout=30)
        mock_result = MagicMock()
        mock_result.stdout = "  hello world  "

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = runner.run("test prompt")

            mock_run.assert_called_once()
            args = mock_run.call_args
            cmd = args[0][0]
            assert cmd[:6] == [
                "claude",
                "-p",
                "test prompt",
                "--model",
                "haiku",
                "--output-format",
            ]
            assert "text" in cmd
            assert "--plugin-dir" in cmd
            assert args[1]["timeout"] == 30
            assert args[1]["capture_output"] is True
            assert args[1]["text"] is True
            assert result == "hello world"
