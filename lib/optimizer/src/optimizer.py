import dspy


def optimize(signature_cls, examples, max_demos=4):
    """Run BootstrapFewShot optimization, return compiled Predict module.

    Assumes dspy.configure(lm=...) has already been called.
    The compiled module's .demos attribute contains the selected few-shot examples.
    """
    predictor = dspy.Predict(signature_cls)
    output_keys = list(signature_cls.output_fields.keys())

    def metric(example, prediction, trace=None):
        return all(bool(getattr(prediction, k, None)) for k in output_keys)

    optimizer = dspy.BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=max_demos,
    )
    return optimizer.compile(predictor, trainset=examples)
