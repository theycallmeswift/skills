import json

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query

from .models import Grading
from .runner import RunResult

DEFAULT_GRADER_MODEL = "claude-haiku-4-5-20251001"

DEFAULT_STDOUT_LIMIT = 40_000
DEFAULT_FILE_LIMIT = 10_000
DEFAULT_TRACE_LIMIT = 50


def _truncate_tail(s: str, limit: int) -> str:
    """Keep the last `limit` characters of `s`, prepending a truncation marker."""
    if len(s) <= limit:
        return s
    dropped = len(s) - limit
    return f"[... truncated {dropped} chars ...]\n{s[-limit:]}"

GRADER_PROMPT = """\
You are a strict eval grader. Read the AGENT OUTPUT below and grade each ASSERTION as PASS or FAIL.

Rules:
- PASS only with clear evidence the assertion is true. The evidence must reflect genuine task completion, not surface-level compliance.
- FAIL if no evidence is found, evidence contradicts the assertion, or evidence is superficial (correct format but wrong content).
- When uncertain, FAIL. The burden of proof is on the assertion.
- No partial credit.
- Cite specific evidence from the output for each judgment.

Return ONLY a JSON object matching this schema (no prose, no markdown fences):
{{
  "expectations": [
    {{"text": "<assertion text>", "passed": true|false, "evidence": "<specific quote or observation>"}}
  ]
}}

ORIGINAL PROMPT:
{original_prompt}

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
}


def _match_tool(trace: list[dict], needle: str) -> dict | None:
    """Return the first trace entry whose name contains `needle`, else None."""
    for entry in trace:
        if needle in entry.get("name", ""):
            return entry
    return None


def _match_skill_invocation(trace: list[dict], skill: str) -> dict | None:
    """Return the first Skill tool entry whose input.skill matches.

    Accepts both bare ('ghostwrite') and prefixed ('mechaswift:ghostwrite') forms.
    """
    for entry in trace:
        if entry.get("name") != "Skill":
            continue
        inv = entry.get("input", {}).get("skill", "")
        if inv == skill or inv.endswith(f":{skill}"):
            return entry
    return None


def _grade_deterministic(assertions: list[dict], run: RunResult) -> list[dict]:
    """Evaluate deterministic assertions against the tool trace."""
    out: list[dict] = []
    for a in assertions:
        if "tool_called" in a:
            needle = a["tool_called"]
            hit = _match_tool(run.tool_trace, needle)
            if hit is not None:
                out.append({
                    "text": f"tool_called: {needle}",
                    "passed": True,
                    "evidence": f"matched tool '{hit['name']}' on turn {hit.get('turn', '?')}",
                })
            else:
                out.append({
                    "text": f"tool_called: {needle}",
                    "passed": False,
                    "evidence": f"no matching tool in trace ({len(run.tool_trace)} entries)",
                })
        elif "tool_not_called" in a:
            needle = a["tool_not_called"]
            hit = _match_tool(run.tool_trace, needle)
            if hit is None:
                out.append({
                    "text": f"tool_not_called: {needle}",
                    "passed": True,
                    "evidence": f"no matching tool in trace ({len(run.tool_trace)} entries)",
                })
            else:
                out.append({
                    "text": f"tool_not_called: {needle}",
                    "passed": False,
                    "evidence": f"found '{hit['name']}' on turn {hit.get('turn', '?')}",
                })
        elif "skill_invoked" in a:
            skill = a["skill_invoked"]
            hit = _match_skill_invocation(run.tool_trace, skill)
            if hit is not None:
                out.append({
                    "text": f"skill_invoked: {skill}",
                    "passed": True,
                    "evidence": f"Skill tool fired with skill='{hit['input'].get('skill', '?')}' on turn {hit.get('turn', '?')}",
                })
            else:
                has_any_skill = any(e.get("name") == "Skill" for e in run.tool_trace)
                if has_any_skill:
                    fired = [e.get("input", {}).get("skill", "?") for e in run.tool_trace if e.get("name") == "Skill"]
                    evidence = f"Skill tool fired but with different skills: {fired}"
                else:
                    evidence = "no Skill tool invocations in trace"
                out.append({
                    "text": f"skill_invoked: {skill}",
                    "passed": False,
                    "evidence": evidence,
                })
    return out


def _build_prompt(
    run: RunResult,
    assertions: list[dict],
    original_prompt: str,
    stdout_limit: int = DEFAULT_STDOUT_LIMIT,
    file_limit: int = DEFAULT_FILE_LIMIT,
    trace_limit: int = DEFAULT_TRACE_LIMIT,
) -> str:
    stdout = _truncate_tail(run.stdout or "(empty)", stdout_limit)
    files_block = (
        "\n\n".join(
            f"--- {p} ---\n{_truncate_tail(c, file_limit)}"
            for p, c in run.files_written.items()
        )
        or "(none)"
    )
    trace = run.tool_trace[-trace_limit:] if len(run.tool_trace) > trace_limit else run.tool_trace
    trace_note = ""
    if len(run.tool_trace) > trace_limit:
        trace_note = f"[... {len(run.tool_trace) - trace_limit} earlier entries truncated ...]\n"
    return GRADER_PROMPT.format(
        original_prompt=original_prompt or "(none)",
        assertions_json=json.dumps(assertions, indent=2),
        stdout=stdout,
        files_block=files_block,
        tool_trace_json=trace_note + json.dumps(trace, indent=2),
    )


_DETERMINISTIC_KEYS = ("tool_called", "tool_not_called", "skill_invoked")


def _is_deterministic(assertion: dict) -> bool:
    return any(k in assertion for k in _DETERMINISTIC_KEYS)


async def _grade_text_llm(
    run: RunResult,
    assertions: list[dict],
    model: str | None,
    original_prompt: str,
    input_limit: int | None = None,
) -> list[dict]:
    if not assertions:
        return []

    options = ClaudeAgentOptions(
        model=model or DEFAULT_GRADER_MODEL,
        output_format=_OUTPUT_SCHEMA,
    )
    if input_limit is None:
        prompt = _build_prompt(run, assertions, original_prompt)
    else:
        scale = input_limit / DEFAULT_STDOUT_LIMIT
        prompt = _build_prompt(
            run, assertions, original_prompt,
            stdout_limit=input_limit,
            file_limit=int(DEFAULT_FILE_LIMIT * scale),
            trace_limit=max(DEFAULT_TRACE_LIMIT, int(DEFAULT_TRACE_LIMIT * scale)),
        )

    structured: dict | None = None
    parts: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            if getattr(message, "structured_output", None):
                structured = message.structured_output
            elif getattr(message, "result", None):
                parts.append(message.result)
        elif isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    parts.append(block.text)

    if structured is not None:
        return structured["expectations"]

    raw = "".join(parts).strip()
    return _parse_grader_fallback(raw)["expectations"]


def _parse_grader_fallback(raw: str) -> dict:
    """Parse a grader response that didn't come back as structured output.

    Strips markdown code fences if present, then JSON-decodes. Raises
    RuntimeError on empty input.
    """
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`")
    if not raw:
        raise RuntimeError("grader returned empty response")
    return json.loads(raw)


async def grade(
    run: RunResult,
    assertions: list[dict],
    model: str | None = None,
    original_prompt: str = "",
    input_limit: int | None = None,
) -> Grading:
    if not assertions:
        return Grading.from_expectations([])

    text_assertions = [a for a in assertions if not _is_deterministic(a)]
    llm_expectations = await _grade_text_llm(
        run, text_assertions, model, original_prompt, input_limit=input_limit
    )

    llm_iter = iter(llm_expectations)
    merged: list[dict] = []
    for a in assertions:
        if _is_deterministic(a):
            merged.extend(_grade_deterministic([a], run))
        else:
            merged.append(next(llm_iter))

    return Grading.from_expectations(merged)
