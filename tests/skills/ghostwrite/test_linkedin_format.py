import textwrap

import pytest

from tests.skills.ghostwrite.ghostwrite_helpers import assert_core_rules
from tests.support.harness.setup import skill_setup

SOURCE = textwrap.dedent("""\
    We just wrapped the 2026 Spring Season of the MLH Fellowship. 620 fellows
    shipped production code at 45 partner companies. Completion rate was 94%.
    Three fellows got return offers before the program ended. The new cohort
    model we piloted let us run two tracks (open source and production) without
    doubling ops headcount. Next season opens applications June 1.
""")


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[f"Rewrite this as a LinkedIn post:\n\n{SOURCE}"],
        setup=skill_setup("ghostwrite", project_root),
    )


def test_core_rules(result):
    assert_core_rules(result, SOURCE)


def test_no_markdown_bold(result):
    assert result.not_matches_regex(r"\*\*[^*]+\*\*", on="final_message")


def test_has_hashtags(result):
    assert result.matches_regex(r"#\w+", on="final_message", min=4, max=7)


def test_length_under_250_words(result):
    assert result.llm_judge(
        "The post is 250 words or fewer.",
        on="final_message",
    )


def test_no_engagement_bait_closer(result):
    assert result.not_matches_regex(
        r"(?i)let me know in the comments", on="final_message"
    )
