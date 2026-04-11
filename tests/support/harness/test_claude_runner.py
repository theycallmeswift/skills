import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.support.harness.claude_runner import ClaudeRunner, RunResult, _parse_stream
from tests.fixtures.stream_json import MULTI_BLOCK_STREAM, SIMPLE_STREAM, TOOL_USE_STREAM


class TestClaudeRunnerInit:
    def test_default_model_is_haiku(self):
        with patch.dict(os.environ, {}, clear=True):
            runner = ClaudeRunner()
            assert runner.model == "haiku"

    def test_default_timeout_is_60(self):
        with patch.dict(os.environ, {}, clear=True):
            runner = ClaudeRunner()
            assert runner.timeout == 60

    def test_custom_model(self):
        runner = ClaudeRunner(model="sonnet")
        assert runner.model == "sonnet"

    def test_custom_timeout(self):
        runner = ClaudeRunner(timeout=90)
        assert runner.timeout == 90

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
        assert (runner.plugin_dir / "pyproject.toml").exists()

    def test_explicit_plugin_dir(self):
        runner = ClaudeRunner(plugin_dir="/tmp/my-plugin")
        assert runner.plugin_dir == Path("/tmp/my-plugin")

    def test_plugin_dir_from_env(self):
        with patch.dict(os.environ, {"CLAUDE_TEST_PLUGIN_DIR": "/tmp/env-plugin"}):
            runner = ClaudeRunner()
            assert runner.plugin_dir == Path("/tmp/env-plugin")


class TestClaudeRunnerRun:
    def test_run_calls_subprocess_with_stream_json(self):
        runner = ClaudeRunner(model="haiku", timeout=30)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = SIMPLE_STREAM

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = runner.run("test prompt")

            mock_run.assert_called_once()
            args = mock_run.call_args
            cmd = args[0][0]
            assert "claude" == cmd[0]
            assert "-p" == cmd[1]
            assert "test prompt" == cmd[2]
            assert "--model" in cmd
            assert "--output-format" in cmd
            assert "stream-json" in cmd
            assert "--verbose" in cmd
            assert "--plugin-dir" in cmd
            assert "--dangerously-skip-permissions" in cmd
            assert args[1]["timeout"] == 30
            assert args[1]["capture_output"] is True
            assert args[1]["text"] is True

    def test_run_returns_run_result(self):
        runner = ClaudeRunner(model="haiku", timeout=30)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = SIMPLE_STREAM

        with patch("subprocess.run", return_value=mock_result):
            result = runner.run("test prompt")
            assert isinstance(result, RunResult)
            assert result.final_output == "hello world"
            assert result.cost_usd == 0.01

    def test_run_raises_on_nonzero_exit(self):
        runner = ClaudeRunner(model="haiku", timeout=30)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "something went wrong"

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(RuntimeError, match="exited with code 1"):
                runner.run("bad prompt")


class TestParseStream:
    def test_simple_text_response(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert isinstance(result, RunResult)
        assert result.cost_usd == 0.01
        assert result.duration_ms == 1000
        assert result.num_turns == 1
        assert result.stop_reason == "end_turn"
        assert result.usage["input_tokens"] == 10
        assert result.usage["output_tokens"] == 20

    def test_excludes_system_and_result_events(self):
        result = _parse_stream(SIMPLE_STREAM)
        types = [e["type"] for e in result.events]
        assert "system" not in types
        assert "result" not in types

    def test_keeps_assistant_and_user_events(self):
        result = _parse_stream(TOOL_USE_STREAM)
        types = [e["type"] for e in result.events]
        assert types == ["assistant", "user", "assistant"]

    def test_events_is_tuple(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert isinstance(result.events, tuple)

    def test_skips_blank_lines(self):
        stream_with_blanks = "\n\n" + SIMPLE_STREAM + "\n\n"
        result = _parse_stream(stream_with_blanks)
        assert result.final_output == "hello world"


class TestRunResultFinalOutput:
    def test_simple_final_output(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert result.final_output == "hello world"

    def test_final_output_after_tool_use(self):
        result = _parse_stream(TOOL_USE_STREAM)
        assert result.final_output == "The file says hello"

    def test_final_output_from_multi_block(self):
        result = _parse_stream(MULTI_BLOCK_STREAM)
        assert result.final_output == "Here is the summary"


class TestRunResultMessages:
    def test_messages_filters_to_assistant_and_user(self):
        result = _parse_stream(TOOL_USE_STREAM)
        types = [m["type"] for m in result.messages]
        assert types == ["assistant", "user", "assistant"]

    def test_simple_has_one_message(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert len(result.messages) == 1
        assert result.messages[0]["type"] == "assistant"


class TestRunResultToolCalls:
    def test_no_tool_calls_in_simple(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert result.tool_calls == []

    def test_extracts_tool_call(self):
        result = _parse_stream(TOOL_USE_STREAM)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "Read"
        assert result.tool_calls[0]["input"] == {"file_path": "/tmp/test.txt"}

    def test_multiple_tool_calls(self):
        result = _parse_stream(MULTI_BLOCK_STREAM)
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["name"] == "Skill"


class TestRunResultToolResults:
    def test_no_tool_results_in_simple(self):
        result = _parse_stream(SIMPLE_STREAM)
        assert result.tool_results == []

    def test_extracts_tool_result(self):
        result = _parse_stream(TOOL_USE_STREAM)
        assert len(result.tool_results) == 1
        assert result.tool_results[0]["tool_use_id"] == "toolu_01"
        assert result.tool_results[0]["content"] == "file contents here"
        assert result.tool_results[0]["structured"]["type"] == "text"
