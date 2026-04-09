import textwrap

import pytest

from tests.support.harness.setup import skill_setup
from tests.skills.ghostwrite.ghostwrite_helpers import assert_core_rules

SOURCE = textwrap.dedent("""\
    MLH ran Global Hack Week in March 2026. It was our biggest one yet --
    18,000 participants across 120 countries over 7 days. We tried a new
    format this time where each day had a themed challenge (Day 1 was AI,
    Day 2 was open source, Day 3 was hardware, etc). The daily themes drove
    way more engagement than the old format where everything was open-ended.
    Completion rates went from 34% to 61%. The most popular challenge was
    the Day 5 "ship a CLI tool" challenge with 4,200 submissions. We're
    going to keep the themed format for future GHWs.
""")


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[f"Rewrite this as a blog post for DEV:\n\n{SOURCE}"],
        setup=skill_setup("ghostwrite", project_root),
    )


def test_core_rules(result):
    assert_core_rules(result, SOURCE)


def test_has_section_headers(result):
    assert result.matches_regex(r"(?m)^#{1,3}\s+\S", on="final_message", min=2)


def test_has_call_to_action(result):
    assert result.llm_judge(
        "The post ends with a clear call-to-action.",
        on="final_message",
    )


def test_uses_concrete_examples(result):
    assert result.llm_judge(
        "The post references specific numbers, tools, or names from the source "
        "rather than vague claims like 'huge turnout' or 'great results'.",
        on="final_message",
    )
