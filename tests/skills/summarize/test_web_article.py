import textwrap

import pytest

from tests.support.harness.setup import skill_setup
from tests.skills.summarize.structural_checks import assert_structure


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Summarize this page for me https://www.anthropic.com/research/claude-character\
            """),
        ],
        setup=skill_setup("summarize", project_root),
    )


def test_structure(result):
    assert_structure(result)


def test_title_is_source_link(result):
    assert result.matches_regex(
        r"\[.*\]\(https://www\.anthropic\.com/research/claude-character[^)]*\)",
        on="final_message",
    )


def test_share_includes_url(result):
    assert result.passes_rubric(
        "The Share code fence contains the bare source URL on its own line.",
        on="final_message",
    )


def test_uses_brightdata(result):
    assert result.tool_called("scrape_as_markdown")


def test_no_webfetch(result):
    assert result.not_tool_called("WebFetch")


def test_no_websearch(result):
    assert result.not_tool_called("WebSearch")
