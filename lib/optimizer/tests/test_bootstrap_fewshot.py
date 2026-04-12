from unittest.mock import MagicMock, patch

import pytest

from src.optimizers.bootstrap_fewshot import BootstrapFewShotStrategy
from src.strategy import OptimizationResult, get_strategy


class TestBootstrapFewShotRegistration:
    def test_registered_as_bootstrap_fewshot(self):
        assert get_strategy("bootstrap_fewshot") is BootstrapFewShotStrategy


class TestBootstrapFewShotOptimize:
    def test_returns_optimization_result(self):
        strategy = BootstrapFewShotStrategy()

        mock_compiled = MagicMock()
        mock_compiled.demos = [{"source": "long text", "rewritten": "short"}]

        with patch("src.optimizers.bootstrap_fewshot.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.BootstrapFewShot.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}
            mock_sig.__doc__ = "Rewrite the input"

            result = strategy.optimize(
                signature_cls=mock_sig,
                examples=[],
                config={"max_demos": 2},
            )

        assert isinstance(result, OptimizationResult)
        assert result.metadata["strategy"] == "bootstrap_fewshot"
        assert result.metadata["demos_selected"] == 1

    def test_default_max_demos_is_4(self):
        strategy = BootstrapFewShotStrategy()

        mock_compiled = MagicMock()
        mock_compiled.demos = []

        with patch("src.optimizers.bootstrap_fewshot.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.BootstrapFewShot.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}
            mock_sig.__doc__ = "Original prompt"

            strategy.optimize(signature_cls=mock_sig, examples=[], config={})

            mock_dspy.BootstrapFewShot.assert_called_once()
            call_kwargs = mock_dspy.BootstrapFewShot.call_args[1]
            assert call_kwargs["max_bootstrapped_demos"] == 4

    def test_rejects_unknown_config_keys(self):
        strategy = BootstrapFewShotStrategy()

        with pytest.raises(ValueError, match="Unknown bootstrap_fewshot config keys"):
            strategy.optimize(signature_cls=MagicMock(), examples=[], config={"bad_key": 1})
