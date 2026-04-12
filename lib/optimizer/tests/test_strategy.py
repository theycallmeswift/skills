import pytest

from src.optimizers.bootstrap_fewshot import BootstrapFewShotStrategy
from src.optimizers.gepa import GEPAStrategy
from src.strategy import STRATEGIES, OptimizationResult, get_strategy


class TestOptimizationResult:
    def test_stores_prompt_and_metadata(self):
        result = OptimizationResult(prompt="optimized", metadata={"score": 0.9})
        assert result.prompt == "optimized"
        assert result.metadata == {"score": 0.9}

    def test_metadata_defaults_to_empty_dict(self):
        result = OptimizationResult(prompt="optimized")
        assert result.metadata == {}


class TestRegistry:
    def test_contains_bootstrap_fewshot(self):
        assert STRATEGIES["bootstrap_fewshot"] is BootstrapFewShotStrategy

    def test_contains_gepa(self):
        assert STRATEGIES["gepa"] is GEPAStrategy

    def test_get_strategy_returns_registered_class(self):
        assert get_strategy("bootstrap_fewshot") is BootstrapFewShotStrategy
        assert get_strategy("gepa") is GEPAStrategy

    def test_get_strategy_raises_on_unknown(self):
        with pytest.raises(ValueError, match="Unknown strategy: nope"):
            get_strategy("nope")
