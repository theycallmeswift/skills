import pytest

from tests.support.harness.setup import compose, copy_files, skill_setup
from tests.skills.summarize.structural_checks import assert_structure


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=["Summarize this PDF: test-paper.pdf"],
        setup=compose(
            skill_setup("summarize", project_root),
            copy_files("tests/support/fixtures/test-paper.pdf", project_root=project_root),
        ),
    )


def test_structure(result):
    assert_structure(result)


def test_title_from_content(result):
    assert result.passes_rubric(
        "Title is based on the document/paper title or filename, not a generic placeholder",
        on="final_message",
    )


def test_share_no_url(result):
    assert result.passes_rubric(
        "The Share code fence does not contain a URL (file input has nothing to link).",
        on="final_message",
    )


def test_uses_read(result):
    assert result.tool_called("Read")


def test_no_brightdata(result):
    assert result.not_tool_called("brightdata")


def test_no_webfetch(result):
    assert result.not_tool_called("WebFetch")
