import os
import pytest
from tests.support.harness.runner import RunResult
from tests.support.harness.grader import grade, _grade_deterministic


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
