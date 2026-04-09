import asyncio
import json

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

DEFAULT_JUDGE_MODEL = "claude-haiku-4-5-20251001"

_JUDGE_PROMPT = """\
You are a strict rubric grader. Evaluate the CONTENT below against the RUBRIC ITEM.

Return ONLY a JSON object: {{"pass": true}} or {{"pass": false, "reasoning": "..."}}

RUBRIC ITEM: {item}

CONTENT:
{content}
"""

_JUDGE_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "pass": {"type": "boolean"},
            "reasoning": {"type": "string"},
        },
        "required": ["pass"],
        "additionalProperties": False,
    },
}


def _extract_verdict(structured: dict | None, raw_parts: list[str]) -> bool:
    """Extract pass/fail from either structured output or raw text."""
    if structured is not None:
        return structured.get("pass", False)

    raw = "".join(raw_parts).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`")

    return json.loads(raw).get("pass", False)


async def _judge_async(item: str, content: str, model: str) -> bool:
    """Send content + rubric item to an LLM judge, return pass/fail."""
    prompt = _JUDGE_PROMPT.format(item=item, content=content[:40_000])
    options = ClaudeAgentOptions(model=model, output_format=_JUDGE_SCHEMA)

    structured: dict | None = None
    raw_parts: list[str] = []

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if getattr(message, "structured_output", None):
                structured = message.structured_output
            elif getattr(message, "result", None):
                raw_parts.append(message.result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    raw_parts.append(block.text)

    return _extract_verdict(structured, raw_parts)


def judge_rubric_item(item: str, content: str, model: str | None = None) -> bool:
    """Synchronous entry point for rubric judging."""
    return asyncio.run(_judge_async(item, content, model or DEFAULT_JUDGE_MODEL))
