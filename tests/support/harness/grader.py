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
from .rubric import parse_rubric_file
from .runner import RunResult

DEFAULT_GRADER_MODEL = "claude-haiku-4-5-20251001"

DEFAULT_STDOUT_LIMIT = 40_000
DEFAULT_FILE_LIMIT = 10_000


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


@_primitive("script_name")
def _grade_script_name_primitive(a: dict, run: RunResult) -> dict:
    return _grade_script_name(a["script_name"], run)


def _grade_deterministic(assertions: list[dict], run: RunResult) -> list[dict]:
    out: list[dict] = []
    for a in assertions:
        for key, fn in _PRIMITIVES.items():
            if key in a:
                out.append(fn(a, run))
                break
    return out




def _repo_root() -> Path:
    # grader.py lives at tests/support/harness/grader.py; repo root is 3 up.
    return Path(__file__).resolve().parents[3]


def _grade_script_name(skill: str, run: RunResult) -> dict:
    """Run skills/<skill>/lint.py against the agent's captured output."""
    lint_path = _repo_root() / "skills" / skill / "lint.py"
    text = f"script_name: {skill}"
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


RUBRIC_PROMPT = """\
You are a strict rubric grader. Evaluate the AGENT OUTPUT below against each RUBRIC ITEM.

For each item return one of:
- "pass": the output clearly satisfies the item
- "fail": the output clearly does not satisfy the item
- "n/a": the item does not apply to this kind of output (e.g. the correct behavior is a refusal)

Cite specific evidence from the output. No partial credit. When uncertain, fail.

Return ONLY a JSON object matching:
{{
  "items": [
    {{"text": "<item text>", "critical": true|false, "status": "pass"|"fail"|"n/a", "evidence": "<quote or observation>"}}
  ]
}}

AGENT OUTPUT (final message):
{final_message}

FILES WRITTEN:
{files_block}

RUBRIC:
{rubric_text}
"""

_RUBRIC_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "critical": {"type": "boolean"},
                        "status": {"type": "string", "enum": ["pass", "fail", "n/a"]},
                        "evidence": {"type": "string"},
                    },
                    "required": ["text", "critical", "status", "evidence"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    },
}


async def _rubric_llm_call(prompt: str, model: str) -> dict:
    """Call the LLM with structured output. Isolated so tests can monkeypatch."""
    options = ClaudeAgentOptions(model=model, output_format=_RUBRIC_SCHEMA)
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
        return structured
    raw = "".join(parts).strip()
    return _parse_grader_fallback(raw)


async def grade_rubric(
    run: RunResult,
    rubric_path: Path,
    model: str = DEFAULT_GRADER_MODEL,
) -> Grading:
    items = parse_rubric_file(rubric_path)
    if not items:
        return Grading.from_expectations([])
    rubric_text = rubric_path.read_text()
    final_msg = getattr(run, "final_message", "") or run.stdout or "(empty)"
    files_block = (
        "\n\n".join(f"--- {p} ---\n{_truncate_tail(c, DEFAULT_FILE_LIMIT)}" for p, c in run.files_written.items())
        or "(none)"
    )
    prompt = RUBRIC_PROMPT.format(
        final_message=_truncate_tail(final_msg, DEFAULT_STDOUT_LIMIT),
        files_block=files_block,
        rubric_text=rubric_text,
    )
    data = await _rubric_llm_call(prompt, model)
    expectations: list[dict] = []
    for graded in data["items"]:
        status = graded["status"]
        critical = graded["critical"]
        # Pass rule (see spec §Rubric grader):
        #   - critical + fail  => failed
        #   - critical + pass  => passed
        #   - critical + n/a   => passed (excused)
        #   - optional + any   => passed (informational only)
        if critical and status == "fail":
            passed = False
        else:
            passed = True
        expectations.append(
            {
                "text": ("[critical] " if critical else "[optional] ") + graded["text"] + f" -- {status}",
                "passed": passed,
                "evidence": graded["evidence"],
            }
        )
    return Grading.from_expectations(expectations)


async def grade(
    run: RunResult,
    assertions: list[dict],
) -> Grading:
    expectations = _grade_deterministic(assertions, run)
    return Grading.from_expectations(expectations)
