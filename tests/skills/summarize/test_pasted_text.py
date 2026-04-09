import textwrap

import pytest

from tests.support.harness.setup import skill_setup
from tests.skills.summarize.structural_checks import assert_structure


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Summarize this for me:

                The rise of the pull request has fundamentally reshaped how software teams collaborate. Originally introduced by GitHub in 2008 as a lightweight way to propose changes across forks, the pull request has evolved into the primary unit of code review, discussion, and integration in modern engineering workflows. Teams argue about PR size, PR templates, PR etiquette, and how long a PR can sit in review before it becomes stale. Companies have built entire product lines around PR automation -- linters that comment inline, bots that auto-assign reviewers based on CODEOWNERS, dashboards that show how long each PR spent waiting at each stage.

                But the pull request has a dark side. Large PRs are where bugs hide, because reviewers skim when they should read. Small PRs fragment context, forcing reviewers to hold a mental model across six tabs. Teams that merge PRs too fast ship bugs; teams that merge too slow ship nothing. The median PR in a busy repository sits in review for two days, and those two days are where velocity goes to die. Solving the pull request problem has become a cottage industry: trunk-based development advocates, stacked diff tools like Graphite, and AI review bots all claim to have the answer.

                The real answer is probably boring: small, focused changes; reviewers who actually read; and a team culture that treats a pending PR as a shared problem, not one person's backlog item.\
            """),
        ],
        setup=skill_setup("summarize", project_root),
    )


def test_structure(result):
    assert_structure(result)


def test_no_scrape(result):
    assert result.not_tool_called("scrape_as_markdown")


def test_no_scrape_batch(result):
    assert result.not_tool_called("scrape_batch")


def test_no_webfetch(result):
    assert result.not_tool_called("WebFetch")


def test_no_websearch(result):
    assert result.not_tool_called("WebSearch")
