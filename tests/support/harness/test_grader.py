import asyncio
import os

import pytest

from tests.support.harness.grader import (
    DEFAULT_STDOUT_LIMIT,
    _build_prompt,
    _grade_deterministic,
    _parse_grader_fallback,
    _truncate_tail,
    grade,
)
from tests.support.harness.models import Grading
from tests.support.harness.runner import RunResult


def test_truncate_tail_keeps_end_and_adds_marker():
    s = "a" * 100
    out = _truncate_tail(s, limit=30)
    assert out.endswith("a" * 30)
    assert "truncated" in out
    assert "70" in out


def test_truncate_tail_noop_when_under_limit():
    s = "short"
    assert _truncate_tail(s, limit=100) == "short"


def test_build_prompt_truncates_long_stdout():
    run = RunResult(
        stdout="x" * (DEFAULT_STDOUT_LIMIT + 5000),
        files_written={},
        input_tokens=0, output_tokens=0, duration_s=0.0,
        exit_code=0, tool_trace=[], turn_count=1,
    )
    prompt = _build_prompt(run, [{"text": "y"}], original_prompt="p", stdout_limit=DEFAULT_STDOUT_LIMIT)
    assert "truncated" in prompt
    assert len(prompt) < DEFAULT_STDOUT_LIMIT + 5000


def test_build_prompt_truncates_tool_trace_to_last_n():
    run = RunResult(
        stdout="x", files_written={},
        input_tokens=0, output_tokens=0, duration_s=0.0,
        exit_code=0,
        tool_trace=[{"name": f"t{i}", "input": {}, "turn": 1} for i in range(200)],
        turn_count=1,
    )
    prompt = _build_prompt(run, [{"text": "y"}], original_prompt="p", trace_limit=50)
    assert '"t199"' in prompt
    assert '"t0"' not in prompt


def _run_with_trace(trace):
    return RunResult(
        stdout="", files_written={}, input_tokens=0, output_tokens=0,
        duration_s=0.0, exit_code=0, tool_trace=trace, turn_count=1,
    )


def test_tool_called_passes_when_name_matches_substring():
    run = _run_with_trace([{"name": "mcp__brightdata__scrape_as_markdown", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"tool_called": "scrape_as_markdown"}], run)
    assert exps == [{
        "text": "tool_called: scrape_as_markdown",
        "passed": True,
        "evidence": "matched tool 'mcp__brightdata__scrape_as_markdown' on turn 1",
    }]


def test_tool_called_fails_when_absent():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"tool_called": "WebFetch"}], run)
    assert exps[0]["passed"] is False
    assert "no matching tool" in exps[0]["evidence"].lower()


def test_tool_not_called_passes_when_absent():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"tool_not_called": "WebFetch"}], run)
    assert exps[0]["passed"] is True


def test_tool_not_called_fails_when_present():
    run = _run_with_trace([{"name": "WebFetch", "input": {"url": "x"}, "turn": 2}])
    exps = _grade_deterministic([{"tool_not_called": "WebFetch"}], run)
    assert exps[0]["passed"] is False
    assert "turn 2" in exps[0]["evidence"]


def test_skill_invoked_matches_bare_name():
    run = _run_with_trace([
        {"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1},
    ])
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is True


def test_skill_invoked_matches_prefixed_name():
    run = _run_with_trace([
        {"name": "Skill", "input": {"skill": "mechaswift:ghostwrite"}, "turn": 1},
    ])
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is True


def test_skill_invoked_fails_when_different_skill():
    run = _run_with_trace([
        {"name": "Skill", "input": {"skill": "summarize"}, "turn": 1},
    ])
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False


def test_skill_invoked_fails_when_no_skill_tool_at_all():
    run = _run_with_trace([{"name": "Read", "input": {}, "turn": 1}])
    exps = _grade_deterministic([{"skill_invoked": "ghostwrite"}], run)
    assert exps[0]["passed"] is False
    assert "no Skill tool" in exps[0]["evidence"]


def test_grade_merges_deterministic_and_text_in_order(monkeypatch):
    run = _run_with_trace([
        {"name": "Skill", "input": {"skill": "ghostwrite"}, "turn": 1},
    ])
    assertions = [
        {"text": "output is a rewrite"},
        {"skill_invoked": "ghostwrite"},
        {"text": "tone is friendly"},
    ]

    async def fake_llm_grade(run_, text_assertions, model, original_prompt, input_limit=None):
        return [
            {"text": a["text"], "passed": True, "evidence": "ok"}
            for a in text_assertions
        ]

    monkeypatch.setattr("tests.support.harness.grader._grade_text_llm", fake_llm_grade)

    result: Grading = asyncio.run(grade(run, assertions))
    assert [e["text"] for e in result.expectations] == [
        "output is a rewrite",
        "skill_invoked: ghostwrite",
        "tone is friendly",
    ]
    assert all(e["passed"] for e in result.expectations)
    assert result.passed == 3
    assert result.total == 3

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    reason="requires Claude credentials",
)
async def test_grader_passes_obviously_true_assertion():
    run = RunResult(
        stdout="The answer is 42.",
        files_written={},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.1,
        exit_code=0,
    )
    assertions = [{"text": "The output mentions the number 42"}]
    g = await grade(run, assertions)
    assert g.passed == 1
    assert g.failed == 0
    assert g.expectations[0]["passed"] is True

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    reason="requires Claude credentials",
)
async def test_grader_fails_obviously_false_assertion():
    run = RunResult(
        stdout="hello world",
        files_written={},
        input_tokens=0,
        output_tokens=0,
        duration_s=0.1,
        exit_code=0,
    )
    assertions = [{"text": "The output mentions the number 42"}]
    g = await grade(run, assertions)
    assert g.passed == 0
    assert g.failed == 1


def test_parse_grader_fallback_strips_json_fence():
    raw = '```json\n{"expectations": [{"text": "x", "passed": true, "evidence": "y"}]}\n```'
    data = _parse_grader_fallback(raw)
    assert data["expectations"][0]["text"] == "x"


def test_parse_grader_fallback_plain_json():
    data = _parse_grader_fallback('{"expectations": []}')
    assert data == {"expectations": []}


def test_parse_grader_fallback_empty_raises():
    with pytest.raises(RuntimeError, match="empty"):
        _parse_grader_fallback("")
