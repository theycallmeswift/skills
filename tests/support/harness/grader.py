import fnmatch
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query

from .models import Grading
from .runner import RunResult

DEFAULT_GRADER_MODEL = "claude-haiku-4-5-20251001"

DEFAULT_STDOUT_LIMIT = 40_000
DEFAULT_FILE_LIMIT = 10_000
DEFAULT_TRACE_LIMIT = 50


def _resolve_source(run: RunResult, on: str | None) -> list[str]:
    """Return the list of text sources to run an assertion against.

    - None or "final_message": the final assistant text (what the user sees)
    - "stdout": the concatenated run output
    - "files.<glob>": contents of every written file whose relative path matches the glob
    """
    if on is None or on == "final_message":
        return [getattr(run, "final_message", "") or ""]
    if on == "stdout":
        return [run.stdout or ""]
    if on.startswith("files."):
        pattern = on[len("files."):]
        return [
            content
            for path, content in run.files_written.items()
            if fnmatch.fnmatch(path, pattern)
        ]
    raise ValueError(f"unknown `on` target: {on!r}")


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


_PrimitiveFn = Callable[[dict, RunResult], dict]

_PRIMITIVES: dict[str, _PrimitiveFn] = {}


def _primitive(key: str) -> Callable[[_PrimitiveFn], _PrimitiveFn]:
    def decorator(fn: _PrimitiveFn) -> _PrimitiveFn:
        _PRIMITIVES[key] = fn
        return fn
    return decorator


@_primitive("tool_called")
def _grade_tool_called(a: dict, run: RunResult) -> dict:
    needle = a["tool_called"]
    hit = _match_tool(run.tool_trace, needle)
    if hit is not None:
        return {
            "text": f"tool_called: {needle}",
            "passed": True,
            "evidence": f"matched tool '{hit['name']}' on turn {hit.get('turn', '?')}",
        }
    return {
        "text": f"tool_called: {needle}",
        "passed": False,
        "evidence": f"no matching tool in trace ({len(run.tool_trace)} entries)",
    }


@_primitive("tool_not_called")
def _grade_tool_not_called(a: dict, run: RunResult) -> dict:
    needle = a["tool_not_called"]
    hit = _match_tool(run.tool_trace, needle)
    if hit is None:
        return {
            "text": f"tool_not_called: {needle}",
            "passed": True,
            "evidence": f"no matching tool in trace ({len(run.tool_trace)} entries)",
        }
    return {
        "text": f"tool_not_called: {needle}",
        "passed": False,
        "evidence": f"found '{hit['name']}' on turn {hit.get('turn', '?')}",
    }


@_primitive("skill_invoked")
def _grade_skill_invoked(a: dict, run: RunResult) -> dict:
    skill = a["skill_invoked"]
    hit = _match_skill_invocation(run.tool_trace, skill)
    if hit is not None:
        return {
            "text": f"skill_invoked: {skill}",
            "passed": True,
            "evidence": f"Skill tool fired with skill='{hit['input'].get('skill', '?')}' on turn {hit.get('turn', '?')}",
        }
    has_any_skill = any(e.get("name") == "Skill" for e in run.tool_trace)
    if has_any_skill:
        fired = [
            e.get("input", {}).get("skill", "?")
            for e in run.tool_trace
            if e.get("name") == "Skill"
        ]
        evidence = f"Skill tool fired but with different skills: {fired}"
    else:
        evidence = "no Skill tool invocations in trace"
    return {"text": f"skill_invoked: {skill}", "passed": False, "evidence": evidence}


@_primitive("skill_not_invoked")
def _grade_skill_not_invoked(a: dict, run: RunResult) -> dict:
    skill = a["skill_not_invoked"]
    hit = _match_skill_invocation(run.tool_trace, skill)
    if hit is None:
        return {
            "text": f"skill_not_invoked: {skill}",
            "passed": True,
            "evidence": f"no {skill} Skill invocation in trace",
        }
    return {
        "text": f"skill_not_invoked: {skill}",
        "passed": False,
        "evidence": f"Skill tool fired with '{hit['input'].get('skill', '?')}' on turn {hit.get('turn', '?')}",
    }


@_primitive("regex")
def _grade_regex(a: dict, run: RunResult) -> dict:
    pattern = a["regex"]
    min_n = a.get("min", 1)
    max_n = a.get("max")  # None = no upper bound
    sources = _resolve_source(run, a.get("on"))
    count = sum(len(re.findall(pattern, s)) for s in sources)
    passed = count >= min_n and (max_n is None or count <= max_n)
    bound = f"min={min_n}" + (f", max={max_n}" if max_n is not None else "")
    return {
        "text": f"regex: {pattern} ({bound})",
        "passed": passed,
        "evidence": f"found {count} match(es) across {len(sources)} source(s)",
    }


@_primitive("not_regex")
def _grade_not_regex(a: dict, run: RunResult) -> dict:
    # Shorthand for regex with max=0.
    return _grade_regex(
        {"regex": a["not_regex"], "min": 0, "max": 0, "on": a.get("on")}, run
    )


@_primitive("contains")
def _grade_contains(a: dict, run: RunResult) -> dict:
    needle = a["contains"]
    sources = _resolve_source(run, a.get("on"))
    hit = any(needle in s for s in sources)
    return {
        "text": f"contains: {needle!r}",
        "passed": hit,
        "evidence": ("found literal" if hit else f"not found in {len(sources)} source(s)"),
    }


@_primitive("contains_all")
def _grade_contains_all(a: dict, run: RunResult) -> dict:
    needles = a["contains_all"]
    sources = _resolve_source(run, a.get("on"))
    haystack = "\n".join(sources)
    missing = [n for n in needles if n not in haystack]
    return {
        "text": f"contains_all: {needles}",
        "passed": not missing,
        "evidence": ("all present" if not missing else f"missing: {missing}"),
    }


@_primitive("not_contains")
def _grade_not_contains(a: dict, run: RunResult) -> dict:
    needle = a["not_contains"]
    sources = _resolve_source(run, a.get("on"))
    hit = any(needle in s for s in sources)
    return {
        "text": f"not_contains: {needle!r}",
        "passed": not hit,
        "evidence": ("literal found (should be absent)" if hit else "absent, as required"),
    }


@_primitive("output_len_lte")
def _grade_output_len_lte(a: dict, run: RunResult) -> dict:
    cap = a["output_len_lte"]
    sources = _resolve_source(run, a.get("on"))
    length = sum(len(s) for s in sources)
    return {
        "text": f"output_len_lte: {cap}",
        "passed": length <= cap,
        "evidence": f"length={length}",
    }


@_primitive("output_len_gte")
def _grade_output_len_gte(a: dict, run: RunResult) -> dict:
    floor = a["output_len_gte"]
    sources = _resolve_source(run, a.get("on"))
    length = sum(len(s) for s in sources)
    return {
        "text": f"output_len_gte: {floor}",
        "passed": length >= floor,
        "evidence": f"length={length}",
    }


@_primitive("token_usage_lte")
def _grade_token_usage_lte(a: dict, run: RunResult) -> dict:
    cap = a["token_usage_lte"]
    total = run.input_tokens + run.output_tokens
    return {
        "text": f"token_usage_lte: {cap}",
        "passed": total <= cap,
        "evidence": f"total_tokens={total}",
    }


@_primitive("trace_order")
def _grade_trace_order(a: dict, run: RunResult) -> dict:
    expected = a["trace_order"]
    names = [e.get("name", "") for e in run.tool_trace]
    # Match each expected tool using substring containment (like _match_tool),
    # advancing a cursor so order must be preserved. Missing expected = fail.
    cursor = 0
    missing: list[str] = []
    for needle in expected:
        found = False
        for i in range(cursor, len(names)):
            if needle in names[i]:
                cursor = i + 1
                found = True
                break
        if not found:
            missing.append(needle)
    passed = not missing
    return {
        "text": f"trace_order: {expected}",
        "passed": passed,
        "evidence": ("matched in order" if passed else f"missing or out of order: {missing}"),
    }


@_primitive("trace_count_lte")
def _grade_trace_count_lte(a: dict, run: RunResult) -> dict:
    spec = a["trace_count_lte"]
    tool = spec["tool"]
    cap = spec["n"]
    count = sum(1 for e in run.tool_trace if tool in e.get("name", ""))
    return {
        "text": f"trace_count_lte: {tool} <= {cap}",
        "passed": count <= cap,
        "evidence": f"found {count} call(s) to {tool}",
    }


@_primitive("turn_count_lte")
def _grade_turn_count_lte(a: dict, run: RunResult) -> dict:
    cap = a["turn_count_lte"]
    return {
        "text": f"turn_count_lte: {cap}",
        "passed": run.turn_count <= cap,
        "evidence": f"ran {run.turn_count} turn(s)",
    }


@_primitive("files_written_include")
def _grade_files_written_include(a: dict, run: RunResult) -> dict:
    pattern = a["files_written_include"]
    matches = [p for p in run.files_written if fnmatch.fnmatch(p, pattern)]
    return {
        "text": f"files_written_include: {pattern}",
        "passed": bool(matches),
        "evidence": (f"matched: {matches}" if matches else f"no files matched (wrote {len(run.files_written)})"),
    }


@_primitive("files_written_exclude")
def _grade_files_written_exclude(a: dict, run: RunResult) -> dict:
    pattern = a["files_written_exclude"]
    matches = [p for p in run.files_written if fnmatch.fnmatch(p, pattern)]
    return {
        "text": f"files_written_exclude: {pattern}",
        "passed": not matches,
        "evidence": ("no matches" if not matches else f"forbidden matches: {matches}"),
    }


@_primitive("files_written_count")
def _grade_files_written_count(a: dict, run: RunResult) -> dict:
    target = a["files_written_count"]
    actual = len(run.files_written)
    return {
        "text": f"files_written_count: {target}",
        "passed": actual == target,
        "evidence": f"wrote {actual} file(s)",
    }


@_primitive("file_contains")
def _grade_file_contains(a: dict, run: RunResult) -> dict:
    spec = a["file_contains"]
    path_glob = spec["path"]
    text = spec.get("text")
    pattern = spec.get("regex")
    if (text is None) == (pattern is None):
        return {
            "text": f"file_contains: {path_glob}",
            "passed": False,
            "evidence": "invalid assertion: must set exactly one of `text` or `regex`",
        }
    matches = [(p, c) for p, c in run.files_written.items() if fnmatch.fnmatch(p, path_glob)]
    if not matches:
        return {
            "text": f"file_contains: {path_glob}",
            "passed": False,
            "evidence": f"no files matched glob (wrote {len(run.files_written)})",
        }
    for path, content in matches:
        if text is not None and text in content:
            return {
                "text": f"file_contains: {path_glob} text={text!r}",
                "passed": True,
                "evidence": f"found in {path}",
            }
        if pattern is not None and re.search(pattern, content):
            return {
                "text": f"file_contains: {path_glob} regex={pattern!r}",
                "passed": True,
                "evidence": f"regex matched in {path}",
            }
    return {
        "text": f"file_contains: {path_glob}",
        "passed": False,
        "evidence": f"no matching file contained the target (checked {[p for p, _ in matches]})",
    }


@_primitive("lint")  # TEMPORARY alias until Task 9 renames to script_name
def _grade_lint_primitive(a: dict, run: RunResult) -> dict:
    return _grade_lint(a["lint"], run)


def _grade_deterministic(assertions: list[dict], run: RunResult) -> list[dict]:
    out: list[dict] = []
    for a in assertions:
        for key, fn in _PRIMITIVES.items():
            if key in a:
                out.append(fn(a, run))
                break
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
            f"--- {p} ---\n{_truncate_tail(c, file_limit)}" for p, c in run.files_written.items()
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


_DETERMINISTIC_KEYS = tuple(_PRIMITIVES.keys())


def _repo_root() -> Path:
    # grader.py lives at tests/support/harness/grader.py; repo root is 3 up.
    return Path(__file__).resolve().parents[3]


def _grade_lint(skill: str, run: RunResult) -> dict:
    """Run skills/<skill>/lint.py against the agent's captured output."""
    lint_path = _repo_root() / "skills" / skill / "lint.py"
    text = f"lint: {skill}"
    if not lint_path.exists():
        return {
            "text": text,
            "passed": False,
            "evidence": f"lint script not found at {lint_path}",
        }
    # Prefer the final assistant message (what the user actually sees), fall
    # back to concatenated stdout, then to the last file the agent wrote.
    content = getattr(run, "final_message", "") or run.stdout or ""
    if not content.strip() and run.files_written:
        # Use the last file the agent wrote as the draft.
        content = next(iter(run.files_written.values()))
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, str(lint_path), tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    passed = result.returncode == 0
    if passed:
        evidence = "lint clean (exit 0)"
    else:
        findings = result.stdout.strip() or result.stderr.strip() or "(no findings emitted)"
        evidence = f"exit {result.returncode}: {findings}"
    return {"text": text, "passed": passed, "evidence": evidence}


def _is_deterministic(assertion: dict) -> bool:
    return any(k in assertion for k in _PRIMITIVES)


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
            run,
            assertions,
            original_prompt,
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
