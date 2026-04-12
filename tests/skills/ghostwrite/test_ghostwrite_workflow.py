import pytest


@pytest.fixture(params=["email_output", "linkedin_output", "slack_output", "blog_output"])
def ghostwrite_output(request):
    """Parametrize workflow tests across all four mediums."""
    return request.getfixturevalue(request.param)


class TestGhostwriteProcess:
    """Verify the ghostwrite skill follows its prescribed process."""

    def test_invokes_ghostwrite_skill(self, ghostwrite_output):
        assert ghostwrite_output.tool_called("Skill", where={"skill": "ghostwrite"})

    def test_loads_about_swift(self, ghostwrite_output):
        assert ghostwrite_output.tool_called("Read", where={"file_path": "about-swift.md"})
