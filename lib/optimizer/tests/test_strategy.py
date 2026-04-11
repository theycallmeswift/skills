import pytest

from src.strategy import STRATEGIES, OptimizationResult, get_strategy, register


class TestOptimizationResult:
    def test_stores_prompt_and_metadata(self):
        result = OptimizationResult(prompt="optimized", metadata={"score": 0.9})
        assert result.prompt == "optimized"
        assert result.metadata == {"score": 0.9}

    def test_metadata_defaults_to_empty_dict(self):
        result = OptimizationResult(prompt="optimized")
        assert result.metadata == {}


class TestRegistry:
    def setup_method(self):
        self._original = STRATEGIES.copy()

    def teardown_method(self):
        STRATEGIES.clear()
        STRATEGIES.update(self._original)

    def test_register_adds_to_registry(self):
        @register("test_strategy")
        class TestStrategy:
            name = "test_strategy"

            def optimize(self, signature_cls, examples, config):
                pass

        assert "test_strategy" in STRATEGIES
        assert STRATEGIES["test_strategy"] is TestStrategy

    def test_get_strategy_returns_registered_class(self):
        @register("test_strategy")
        class TestStrategy:
            name = "test_strategy"

            def optimize(self, signature_cls, examples, config):
                pass

        assert get_strategy("test_strategy") is TestStrategy

    def test_get_strategy_raises_on_unknown(self):
        with pytest.raises(ValueError, match="Unknown strategy: nope"):
            get_strategy("nope")
