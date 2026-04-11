import pytest


@pytest.fixture(params=["pasted_output", "url_output", "file_output"])
def summarize_output(request):
    """Parametrize process tests across all three input types."""
    return request.getfixturevalue(request.param)


class TestSummarizeProcess:
    """Verify the summarize skill follows its prescribed process."""

    def test_dispatches_ghostwrite_subagent(self, summarize_output):
        agent_calls = [
            c for c in summarize_output.tool_calls if c["name"] == "Agent"
        ]
        ghostwrite_calls = [
            c for c in agent_calls
            if "ghostwrite" in c["input"].get("prompt", "").lower()
        ]
        assert len(ghostwrite_calls) >= 1, (
            f"Expected summarize to dispatch a ghostwrite subagent. "
            f"Agent calls found: {[c['input'].get('description', '') for c in agent_calls]}"
        )
