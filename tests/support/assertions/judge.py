"""LLM-based judge for semantic assertion checks.

Sends a structured rubric prompt through ClaudeRunner and parses JSON result.
"""

import json
from dataclasses import dataclass
from textwrap import dedent


@dataclass
class JudgeResult:
    """Result from an LLM judge evaluation.

    Attributes:
        passed: True if all checks passed.
        checks: Mapping of criterion name to pass/fail.
        reasoning: Mapping of criterion name to explanation.
    """

    passed: bool
    checks: dict[str, bool]
    reasoning: dict[str, str]


def judge(source: str, output: str, rubric: str, runner) -> JudgeResult:
    """Send a structured rubric prompt through the harness, parse JSON result.

    Args:
        source: The original source content.
        output: The rewritten output to evaluate.
        rubric: Natural-language criteria to judge against.
        runner: A ClaudeRunner instance.

    Returns:
        JudgeResult with pass/fail per criterion and reasoning.
    """
    prompt = dedent(f"""\
        You are a writing quality judge. Evaluate whether the OUTPUT meets the criteria.

        SOURCE (original content):
        {source}

        OUTPUT (rewritten content):
        {output}

        RUBRIC (criteria to evaluate):
        {rubric}

        Respond with ONLY a JSON object, no markdown fences, no explanation outside the JSON:
        {{
            "checks": {{"criterion_name": true/false}},
            "reasoning": {{"criterion_name": "brief explanation"}}
        }}

        Use short, descriptive criterion names derived from the rubric (e.g., "main_point_first").
        Be strict: only pass if the criterion is clearly met.""")

    raw = runner.run(prompt).final_output

    # Strip markdown fences if the model wraps the JSON
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("\n", 1)[0]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        checks = data["checks"]
        reasoning = data["reasoning"]
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Judge returned unparseable output: {e}\nRaw: {raw}") from e

    return JudgeResult(
        passed=all(checks.values()),
        checks=checks,
        reasoning=reasoning,
    )
