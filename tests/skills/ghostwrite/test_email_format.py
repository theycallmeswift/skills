import textwrap

import pytest

from tests.support.harness.setup import skill_setup
from tests.skills.ghostwrite.ghostwrite_helpers import assert_core_rules

SOURCE = textwrap.dedent("""\
    Hey so I wanted to reach out because we just wrapped up Season 3 of the
    Fellowship and the numbers were really strong. We had 450 fellows complete
    the program which is up 30% from last season. 92% of them said they'd
    recommend it to a friend. I think this is a great opportunity for us to
    talk about renewing the sponsorship for next season and maybe even
    expanding the scope of what we do together. Let me know if you'd be open
    to hopping on a call next week to discuss.
""")


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[f"Rewrite this as an email to our sponsor contact Sarah:\n\n{SOURCE}"],
        setup=skill_setup("ghostwrite", project_root),
    )


def test_core_rules(result):
    assert_core_rules(result, SOURCE)


def test_leads_with_the_ask(result):
    assert result.llm_judge(
        "The first sentence contains the results, the news, or the ask. "
        "There is no preamble like 'I wanted to reach out' or 'I hope this finds you well'.",
        on="final_message",
    )


def test_preserves_key_numbers(result):
    assert result.contains_all(["450", "30%", "92%"], on="final_message")


def test_greeting_format(result):
    assert result.matches_regex(r"(?m)^Hey, Sarah --", on="final_message")


def test_sign_off(result):
    assert result.matches_regex(
        r"(?m)(- Swift|Happy Hacking,\s*\nSwift)\s*$", on="final_message"
    )


def test_no_section_headers(result):
    assert result.llm_judge(
        "The email uses narrative transitions between topics, not bold headers or section dividers.",
        on="final_message",
    )
