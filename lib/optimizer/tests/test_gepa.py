from unittest.mock import MagicMock, patch

from src.strategy import STRATEGIES, OptimizationResult, get_strategy


class TestGEPARegistration:
    def test_registered_as_gepa(self):
        import src.optimizers.gepa  # noqa: F401

        assert "gepa" in STRATEGIES

    def test_get_strategy_returns_class(self):
        import src.optimizers.gepa  # noqa: F401

        cls = get_strategy("gepa")
        assert cls.name == "gepa"


class TestGEPAOptimize:
    def test_returns_optimization_result(self):
        import src.optimizers.gepa  # noqa: F401

        cls = get_strategy("gepa")
        strategy = cls()

        mock_compiled = MagicMock()
        mock_predict = MagicMock()
        mock_predict.signature.__doc__ = "Rewritten optimized prompt"
        mock_compiled.predictors.return_value = [mock_predict]

        with patch("src.optimizers.gepa.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.GEPA.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}
            mock_sig.__doc__ = "Original prompt"

            result = strategy.optimize(
                signature_cls=mock_sig,
                examples=[],
                config={"auto": "light"},
            )

        assert isinstance(result, OptimizationResult)
        assert result.prompt == "Rewritten optimized prompt"
        assert result.metadata["strategy"] == "gepa"

    def test_default_config_uses_light_auto(self):
        import src.optimizers.gepa  # noqa: F401

        cls = get_strategy("gepa")
        strategy = cls()

        mock_compiled = MagicMock()
        mock_predict = MagicMock()
        mock_predict.signature.__doc__ = "Rewritten prompt"
        mock_compiled.predictors.return_value = [mock_predict]

        with patch("src.optimizers.gepa.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.GEPA.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}
            mock_sig.__doc__ = "Original prompt"

            strategy.optimize(signature_cls=mock_sig, examples=[], config={})

            call_kwargs = mock_dspy.GEPA.call_args[1]
            assert call_kwargs.get("auto") == "light"

    def test_config_passes_through_gepa_params(self):
        import src.optimizers.gepa  # noqa: F401

        cls = get_strategy("gepa")
        strategy = cls()

        mock_compiled = MagicMock()
        mock_predict = MagicMock()
        mock_predict.signature.__doc__ = "Rewritten prompt"
        mock_compiled.predictors.return_value = [mock_predict]

        with patch("src.optimizers.gepa.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.GEPA.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}
            mock_sig.__doc__ = "Original prompt"

            strategy.optimize(
                signature_cls=mock_sig,
                examples=[],
                config={
                    "auto": "medium",
                    "reflection_minibatch_size": 5,
                    "use_merge": False,
                },
            )

            call_kwargs = mock_dspy.GEPA.call_args[1]
            assert call_kwargs["auto"] == "medium"
            assert call_kwargs["reflection_minibatch_size"] == 5
            assert call_kwargs["use_merge"] is False
