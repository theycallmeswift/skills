import asyncio
import json

from pydantic import BaseModel
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)

DEFAULT_EXTRACT_MODEL = "claude-haiku-4-5-20251001"

_EXTRACT_PROMPT = """\
Extract structured fields from the CONTENT below into the specified JSON schema.
Return ONLY a JSON object matching the schema. No commentary.

CONTENT:
{content}
"""


async def _extract_async(content: str, schema: dict, model: str) -> dict:
    """Send content to an LLM with a JSON schema constraint, return parsed dict."""
    prompt = _EXTRACT_PROMPT.format(content=content[:40_000])
    output_format = {"type": "json_schema", "schema": schema}
    options = ClaudeAgentOptions(model=model, output_format=output_format)

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

    if structured is not None:
        return structured

    raw = "".join(raw_parts).strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`")

    return json.loads(raw)


def extract_fields(
    content: str,
    model_class: type[BaseModel],
    llm_model: str | None = None,
) -> BaseModel:
    """Extract structured fields from text using an LLM, validate with Pydantic.

    Sends the content to Haiku with the model's JSON schema as a constraint.
    The LLM extracts field values, then Pydantic validates the result.
    """
    schema = model_class.model_json_schema()
    raw = asyncio.run(
        _extract_async(content, schema, llm_model or DEFAULT_EXTRACT_MODEL)
    )
    return model_class.model_validate(raw)
