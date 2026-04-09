import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                This prompt isn't working, can you fix it?

                ```
                You are a helpful AI assistant that helps users. Please be very \
                thorough but also concise. I would really appreciate it if you \
                could analyze the following customer feedback and tell me what \
                you think about it. Make sure to consider all aspects and provide \
                a detailed yet brief summary. Thank you so much!

                {feedback}
                ```\
            """),
        ],
        setup=skill_setup("prompt-engineer", project_root),
    )


def test_has_code_block(result):
    assert result.matches_regex(r"```[\s\S]*?```", on="final_message")


def test_has_changes_section(result):
    assert result.matches_regex(
        r"(?im)(^\*\*changes\*\*|^##?\s*changes|^##?\s*what changed)",
        on="final_message",
    )


def test_removes_padding(result):
    assert result.not_matches_regex(
        r"(?i)helpful AI assistant", on="final_message"
    )
    assert result.not_matches_regex(r"\bPlease\b", on="final_message")
    assert result.not_matches_regex(r"\bThank you\b", on="final_message")


def test_specifies_output_format(result):
    assert result.passes_rubric(
        "The rewritten prompt includes a concrete output format "
        "(e.g. bullet points, JSON, specific structure).",
        on="final_message",
    )


def test_resolves_contradiction(result):
    assert result.passes_rubric(
        "The rewritten prompt does not contain the contradiction "
        "'thorough but concise' or equivalent conflicting instructions.",
        on="final_message",
    )
