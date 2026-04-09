import textwrap

import pytest

from tests.support.harness.setup import skill_setup
from tests.skills.ghostwrite.core_checks import assert_core_rules

SOURCE = textwrap.dedent("""\
    Hey team, I wanted to flag that the sponsorship deck for Hack the North \
    needs to go out by Friday. The numbers are finalized -- 1,200 hackers, \
    38 sponsors confirmed, NPS of 87 from last year. Can someone on the \
    partnerships team send the updated version to the organizers?\
""")


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[f"Rewrite this as a Slack message:\n\n{SOURCE}"],
        setup=skill_setup("ghostwrite", project_root),
    )


def test_core_rules(result):
    assert_core_rules(result, SOURCE)


def test_no_greeting(result):
    assert result.not_matches_regex(r"(?i)^Hey (team|folks|everyone)", on="final_message")


def test_no_bullets_or_headers(result):
    assert result.passes_rubric(
        "The message is prose only. No bullet lists, numbered lists, bold text, or markdown headers.",
        on="final_message",
    )


def test_under_60_words(result):
    assert result.passes_rubric(
        "The message is 60 words or fewer.",
        on="final_message",
    )


def test_no_sign_off(result):
    assert result.not_matches_regex(r"(?m)(- Swift|Happy Hacking)", on="final_message")


def test_leads_with_request(result):
    assert result.passes_rubric(
        "The first sentence is the request or the key point, not background context.",
        on="final_message",
    )
