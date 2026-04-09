import textwrap

import pytest

from tests.support.harness.setup import skill_setup


@pytest.fixture(scope="module")
def result(run_eval, project_root):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Write me a prompt for an LLM that extracts the parties, \
                effective date, and termination clauses from a contract PDF. \
                The output should be JSON so we can stick it in a database.\
            """),
        ],
        setup=skill_setup("prompt-engineer", project_root),
    )


def test_has_code_block(result):
    assert result.matches_regex(r"```[\s\S]*?```", on="final_message")


def test_no_preamble(result):
    assert result.not_matches_regex(
        r"^(Here is your prompt|Sure, I can help)", on="final_message"
    )


def test_mentions_required_fields(result):
    assert result.contains_all(
        ["parties", "effective_date", "termination"], on="final_message"
    )


def test_no_generic_assistant_role(result):
    assert result.not_matches_regex(
        r"(?i)You are (a|an) (helpful|friendly)\s*(AI\s*)?assistant",
        on="final_message",
    )


def test_json_only_output(result):
    assert result.passes_rubric(
        "The produced prompt instructs the target LLM to return only JSON "
        "with no prose wrapper, markdown fences, or commentary.",
        on="final_message",
    )


def test_handles_missing_fields(result):
    assert result.passes_rubric(
        "The produced prompt specifies what to do when a required field is "
        "missing or not found in the document (e.g. return null, omit, or "
        "indicate unknown).",
        on="final_message",
    )


def test_handles_long_input(result):
    assert result.passes_rubric(
        "The produced prompt addresses how to handle long or multi-page "
        "document input (e.g. process the full document, chunking, or "
        "explicit length handling).",
        on="final_message",
    )
