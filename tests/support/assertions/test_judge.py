import json
from unittest.mock import MagicMock

import pytest

from tests.support.assertions.judge import JudgeResult, judge


class TestJudgeResult:
    def test_passed_when_all_checks_true(self):
        result = JudgeResult(
            passed=True,
            checks={"clarity": True, "tone": True},
            reasoning={"clarity": "Clear writing", "tone": "Good tone"},
        )
        assert result.passed is True

    def test_failed_when_any_check_false(self):
        result = JudgeResult(
            passed=False,
            checks={"clarity": True, "tone": False},
            reasoning={"clarity": "Clear", "tone": "Too formal"},
        )
        assert result.passed is False


class TestJudge:
    def _mock_run_result(self, text):
        """Create a MagicMock mimicking RunResult with a .text property."""
        result = MagicMock()
        result.final_output = text
        return result

    def test_passes_when_all_criteria_met(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = self._mock_run_result(json.dumps(
            {
                "checks": {"main_point_first": True},
                "reasoning": {"main_point_first": "Opens with the key ask"},
            }
        ))

        result = judge(
            source="Please review my PR",
            output="Can you review PR #42? It adds the new auth flow.",
            rubric="Opening sentence contains the main point/ask",
            runner=mock_runner,
        )

        assert result.passed is True
        assert result.checks["main_point_first"] is True
        mock_runner.run.assert_called_once()

    def test_fails_when_criteria_not_met(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = self._mock_run_result(json.dumps(
            {
                "checks": {"main_point_first": False},
                "reasoning": {"main_point_first": "Starts with context, not the ask"},
            }
        ))

        result = judge(
            source="Please review my PR",
            output="I've been working on auth. Can you review PR #42?",
            rubric="Opening sentence contains the main point/ask",
            runner=mock_runner,
        )

        assert result.passed is False
        assert result.checks["main_point_first"] is False

    def test_prompt_includes_source_output_and_rubric(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = self._mock_run_result(json.dumps(
            {
                "checks": {"test": True},
                "reasoning": {"test": "ok"},
            }
        ))

        judge(
            source="my source",
            output="my output",
            rubric="my rubric",
            runner=mock_runner,
        )

        prompt = mock_runner.run.call_args[0][0]
        assert "my source" in prompt
        assert "my output" in prompt
        assert "my rubric" in prompt

    def test_strips_markdown_fences(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = self._mock_run_result(
            '```json\n{"checks": {"test": true}, "reasoning": {"test": "ok"}}\n```'
        )

        result = judge(source="s", output="o", rubric="r", runner=mock_runner)
        assert result.passed is True

    def test_raises_on_malformed_json(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = self._mock_run_result("not json at all")

        with pytest.raises(ValueError, match="unparseable output"):
            judge(source="s", output="o", rubric="r", runner=mock_runner)

    def test_raises_on_missing_keys(self):
        mock_runner = MagicMock()
        mock_runner.run.return_value = self._mock_run_result(json.dumps({"checks": {"a": True}}))

        with pytest.raises(ValueError, match="unparseable output"):
            judge(source="s", output="o", rubric="r", runner=mock_runner)
