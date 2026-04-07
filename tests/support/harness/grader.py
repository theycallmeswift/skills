import json
from .models import Grading
from .runner import RunResult

DEFAULT_GRADER_MODEL = "claude-haiku-4-5-20251001"

GRADER_PROMPT = """\
You are a strict eval grader. Read the AGENT OUTPUT below and grade each ASSERTION as PASS or FAIL.

Rules:
- PASS only with clear evidence the assertion is true. The evidence must reflect genuine task completion, not surface-level compliance.
- FAIL if no evidence is found, evidence contradicts the assertion, or evidence is superficial (correct format but wrong content).
- When uncertain, FAIL. The burden of proof is on the assertion.
- No partial credit.
- Cite specific evidence from the output for each judgment.

ASSERTIONS:
{assertions_json}

AGENT OUTPUT (stdout):
{stdout}

FILES WRITTEN BY AGENT:
{files_block}

TOOL TRACE:
{tool_trace_json}
"""

_OUTPUT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "grading_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "expectations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "passed": {"type": "boolean"},
                            "evidence": {"type": "string"},
                        },
                        "required": ["text", "passed", "evidence"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["expectations"],
            "additionalProperties": False,
        },
    },
}


def _build_prompt(run: RunResult, assertions: list[dict]) -> str:
    files_block = (
        "\n\n".join(f"--- {p} ---\n{c}" for p, c in run.files_written.items())
        or "(none)"
    )
    return GRADER_PROMPT.format(
        assertions_json=json.dumps(assertions, indent=2),
        stdout=run.stdout or "(empty)",
        files_block=files_block,
        tool_trace_json=json.dumps(run.tool_trace, indent=2),
    )


async def grade(
    run: RunResult,
    assertions: list[dict],
    model: str | None = None,
) -> Grading:
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage

    if not assertions:
        return Grading.from_expectations([])

    options = ClaudeAgentOptions(
        model=model or DEFAULT_GRADER_MODEL,
        output_format=_OUTPUT_SCHEMA,
    )
    prompt = _build_prompt(run, assertions)

    parts: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    parts.append(block.text)

    raw = "".join(parts).strip()
    data = json.loads(raw)
    return Grading.from_expectations(data["expectations"])
