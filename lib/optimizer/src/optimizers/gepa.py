import dspy

from src.strategy import OptimizationResult, register

# Supported config keys for GEPA
GEPA_CONFIG_KEYS = {
    "auto",
    "reflection_minibatch_size",
    "use_merge",
    "max_merge_invocations",
}


@register("gepa")
class GEPAStrategy:
    """Instruction-only optimizer using reflective mutation and genetic evolution."""

    name = "gepa"

    def optimize(self, signature_cls, examples: list, config: dict) -> OptimizationResult:
        predictor = dspy.Predict(signature_cls)
        output_keys = list(signature_cls.output_fields.keys())

        def metric(example, prediction, trace=None):
            score = all(bool(getattr(prediction, k, None)) for k in output_keys)
            if not score:
                return 0.0, "Output fields are empty or missing."
            return 1.0, "All output fields present and non-empty."

        # Build GEPA kwargs from config, defaulting auto to "light"
        gepa_kwargs = {"auto": config.get("auto", "light"), "metric": metric}
        for key in GEPA_CONFIG_KEYS - {"auto"}:
            if key in config:
                gepa_kwargs[key] = config[key]

        optimizer = dspy.GEPA(**gepa_kwargs)
        compiled = optimizer.compile(predictor, trainset=examples)

        # Extract rewritten prompt from compiled module's first predictor
        predictors = compiled.predictors()
        rewritten_prompt = predictors[0].signature.__doc__ if predictors else ""

        return OptimizationResult(
            prompt=rewritten_prompt,
            metadata={
                "strategy": "gepa",
                "auto": gepa_kwargs["auto"],
            },
        )
