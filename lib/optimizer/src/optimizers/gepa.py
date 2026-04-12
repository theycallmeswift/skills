import dspy

from src.metric import build_judge_metric
from src.strategy import OptimizationResult, register

# Supported config keys for GEPA
GEPA_CONFIG_KEYS = {
    "auto",
    "max_metric_calls",
    "max_full_evals",
    "reflection_minibatch_size",
    "use_merge",
    "max_merge_invocations",
    "num_threads",
}


@register("gepa")
class GEPAStrategy:
    """Instruction-only optimizer using reflective mutation and genetic evolution."""

    name = "gepa"

    def optimize(self, signature_cls, examples: list, config: dict) -> OptimizationResult:
        predictor = dspy.Predict(signature_cls)
        output_keys = list(signature_cls.output_fields.keys())
        metric = build_judge_metric(output_keys)

        unknown = set(config.keys()) - GEPA_CONFIG_KEYS
        if unknown:
            raise ValueError(f"Unknown GEPA config keys: {unknown}")

        # GEPA requires a reflection LM — use the currently configured DSPy LM
        gepa_kwargs = {
            "metric": metric,
            "reflection_lm": dspy.settings.lm,
        }

        # Exactly one of auto, max_metric_calls, max_full_evals must be set
        budget_keys = {"auto", "max_metric_calls", "max_full_evals"}
        has_budget = budget_keys & config.keys()
        if not has_budget:
            gepa_kwargs["auto"] = "light"
        for key in GEPA_CONFIG_KEYS:
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
            },
        )
