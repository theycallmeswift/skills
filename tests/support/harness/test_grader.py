import os
import pytest
from tests.support.harness.runner import RunResult
from tests.support.harness.grader import grade

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
