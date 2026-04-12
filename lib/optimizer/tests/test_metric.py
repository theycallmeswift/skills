from unittest.mock import MagicMock, patch

import pytest

from src.metric import build_judge_metric


class TestBuildJudgeMetric:
    def test_returns_callable(self):
        metric = build_judge_metric(["rewritten"])
        assert callable(metric)

    def test_accepts_gepa_five_arg_signature(self):
        """Metric must accept (gold, pred, trace, pred_name, pred_trace)."""
        metric = build_judge_metric(["rewritten"])

        gold = MagicMock()
        gold.rewritten = "Short version."
        pred = MagicMock()
        pred.rewritten = "A short version."

        with patch("src.metric.dspy") as mock_dspy:
            mock_judge = MagicMock()
            mock_judge.return_value = MagicMock(score="0.8")
            mock_dspy.Predict.return_value = mock_judge

            # Should not raise — all 5 args accepted
            result = metric(gold, pred, trace=None, pred_name=None, pred_trace=None)
            assert isinstance(result, float)

    def test_returns_zero_for_empty_output(self):
        metric = build_judge_metric(["rewritten"])

        gold = MagicMock()
        gold.rewritten = "Expected output."
        pred = MagicMock()
        pred.rewritten = ""

        # No LLM call needed — short circuits on empty
        result = metric(gold, pred)
        assert result == 0.0

    def test_returns_zero_for_missing_output(self):
        metric = build_judge_metric(["rewritten"])

        gold = MagicMock(spec=[])
        pred = MagicMock(spec=[])

        result = metric(gold, pred)
        assert result == 0.0

    def test_calls_judge_with_gold_and_pred(self):
        metric = build_judge_metric(["rewritten"])

        gold = MagicMock()
        gold.rewritten = "Meeting moved to next Tuesday."
        pred = MagicMock()
        pred.rewritten = "The meeting is rescheduled for Tuesday."

        with patch("src.metric.dspy") as mock_dspy:
            mock_judge = MagicMock()
            mock_judge.return_value = MagicMock(score="0.7")
            mock_dspy.Predict.return_value = mock_judge

            result = metric(gold, pred)

            mock_judge.assert_called_once()
            call_kwargs = mock_judge.call_args[1]
            assert "Meeting moved to next Tuesday." in call_kwargs["expected"]
            assert "The meeting is rescheduled for Tuesday." in call_kwargs["actual"]
            assert result == 0.7

    def test_clamps_score_above_1(self):
        metric = build_judge_metric(["rewritten"])

        gold = MagicMock()
        gold.rewritten = "Expected."
        pred = MagicMock()
        pred.rewritten = "Actual."

        with patch("src.metric.dspy") as mock_dspy:
            mock_judge = MagicMock()
            mock_judge.return_value = MagicMock(score="1.5")
            mock_dspy.Predict.return_value = mock_judge

            assert metric(gold, pred) == 1.0

    def test_clamps_score_below_0(self):
        metric = build_judge_metric(["rewritten"])

        gold = MagicMock()
        gold.rewritten = "Expected."
        pred = MagicMock()
        pred.rewritten = "Actual."

        with patch("src.metric.dspy") as mock_dspy:
            mock_judge = MagicMock()
            mock_judge.return_value = MagicMock(score="-0.3")
            mock_dspy.Predict.return_value = mock_judge

            assert metric(gold, pred) == 0.0

    def test_handles_non_numeric_score_gracefully(self):
        metric = build_judge_metric(["rewritten"])

        gold = MagicMock()
        gold.rewritten = "Expected."
        pred = MagicMock()
        pred.rewritten = "Actual."

        with patch("src.metric.dspy") as mock_dspy:
            mock_judge = MagicMock()
            mock_judge.return_value = MagicMock(score="not a number")
            mock_dspy.Predict.return_value = mock_judge

            assert metric(gold, pred) == 0.0

    def test_averages_across_multiple_output_fields(self):
        metric = build_judge_metric(["summary", "title"])

        gold = MagicMock()
        gold.summary = "A good summary."
        gold.title = "A good title."
        pred = MagicMock()
        pred.summary = "OK summary."
        pred.title = "OK title."

        with patch("src.metric.dspy") as mock_dspy:
            mock_judge = MagicMock()
            # First call returns 0.6, second returns 0.8
            mock_judge.side_effect = [
                MagicMock(score="0.6"),
                MagicMock(score="0.8"),
            ]
            mock_dspy.Predict.return_value = mock_judge

            result = metric(gold, pred)
            assert result == pytest.approx(0.7)
