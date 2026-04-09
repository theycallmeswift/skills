import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Write a LinkedIn post announcing that MLH is partnering with a \
                new AI company to offer hackathon participants access to their API.\
            """),
        ],
        setup=skill_setup("ghostwrite", project_root),
    )


def test_refuses_to_draft(result):
    assert result.llm_judge(
        "Output does NOT contain a full LinkedIn post draft. Instead, it explains "
        "that ghostwrite is a rewriter and asks the user to provide source content.",
        on="final_message",
    )


def test_no_fabrication(result):
    assert result.llm_judge(
        "Output does not invent a company name, fabricate partnership details, "
        "or use [Bracket Placeholders] to fill gaps.",
        on="final_message",
    )
