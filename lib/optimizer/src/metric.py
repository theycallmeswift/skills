import dspy


class JudgeOutput(dspy.Signature):
    """Rate how well the actual output matches the expected output in quality and intent.

    Consider: Does the actual output achieve the same goal as the expected output?
    Is the quality comparable? Are there meaningful differences in accuracy, style, or completeness?
    """

    expected = dspy.InputField(desc="The gold-standard expected output")
    actual = dspy.InputField(desc="The model's actual output to evaluate")
    score = dspy.OutputField(desc="A float between 0.0 (completely wrong) and 1.0 (perfect match)")


def build_judge_metric(output_keys):
    """Create a metric that uses an LLM judge to score output quality.

    Returns a function compatible with GEPA's 5-argument metric signature.
    The judge compares each output field against the gold standard and averages scores.
    """
    judge = None

    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        nonlocal judge
        if judge is None:
            judge = dspy.Predict(JudgeOutput)

        scores = []
        for key in output_keys:
            expected = str(getattr(gold, key, "") or "")
            actual = str(getattr(pred, key, "") or "")

            if not actual:
                return 0.0

            result = judge(expected=expected, actual=actual)

            try:
                score = float(result.score)
                score = max(0.0, min(1.0, score))
            except (ValueError, TypeError):
                score = 0.0

            scores.append(score)

        return sum(scores) / len(scores) if scores else 0.0

    return metric
