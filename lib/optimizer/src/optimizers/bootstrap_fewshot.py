import dspy

from src.extractor import extract_demos, format_optimized_prompt
from src.strategy import OptimizationResult, register

BOOTSTRAP_CONFIG_KEYS = {"max_demos"}


@register("bootstrap_fewshot")
class BootstrapFewShotStrategy:
    """Selects optimal few-shot examples from training data."""

    name = "bootstrap_fewshot"

    def optimize(self, signature_cls, examples: list, config: dict) -> OptimizationResult:
        unknown = set(config.keys()) - BOOTSTRAP_CONFIG_KEYS
        if unknown:
            raise ValueError(f"Unknown bootstrap_fewshot config keys: {unknown}")

        max_demos = config.get("max_demos", 4)

        predictor = dspy.Predict(signature_cls)
        output_keys = list(signature_cls.output_fields.keys())
        input_keys = list(signature_cls.input_fields.keys())

        def metric(example, prediction, trace=None):
            return all(bool(getattr(prediction, k, None)) for k in output_keys)

        optimizer = dspy.BootstrapFewShot(
            metric=metric,
            max_bootstrapped_demos=max_demos,
        )
        compiled = optimizer.compile(predictor, trainset=examples)

        demos = extract_demos(compiled)
        original_prompt = signature_cls.__doc__ or ""
        prompt = format_optimized_prompt(original_prompt, demos, input_keys, output_keys)

        return OptimizationResult(
            prompt=prompt,
            metadata={
                "strategy": "bootstrap_fewshot",
                "demos_selected": len(demos),
                "max_demos": max_demos,
            },
        )
