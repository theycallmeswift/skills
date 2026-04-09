import textwrap

import pytest


@pytest.fixture(scope="module")
def ghostwrite_trigger(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Rewrite this in my voice as a Slack message to the team:

                Hey everyone, I wanted to share some quick thoughts on where we are heading into Q2. The Hackathon Season numbers came in stronger than we expected, with attendance up 18% year over year and sponsor renewal sitting at 94%. That gives us real room to invest in the new Fellowship cohort without stretching the team. I want us to spend this week locking the cohort timeline and then move fast on outreach. Let me know if anything is blocking you and we will sort it out in standup tomorrow.\
            """),
        ],
    )


@pytest.fixture(scope="module")
def scope_trigger(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                help me scope a new feature where users can schedule recurring exports of their data\
            """),
        ],
    )


@pytest.fixture(scope="module")
def summarize_trigger(run_eval):
    return run_eval(
        turns=[
            "tl;dr this for me: https://www.anthropic.com/news/claude-4",
        ],
    )


@pytest.fixture(scope="module")
def prompt_engineer_trigger(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                write me a prompt for an LLM that extracts structured JSON from invoices\
            """),
        ],
    )


@pytest.fixture(scope="module")
def trivia_no_skill(run_eval):
    return run_eval(turns=["what is 2 + 2?"])


@pytest.fixture(scope="module")
def no_ghostwrite_on_fresh(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                Write me a brand new 200-word blog post about why Rust's borrow checker is good for beginners. This is a fresh post -- I have no source content for you to rewrite.\
            """),
        ],
    )


# --- Trigger tests ---


def test_ghostwrite_triggers(ghostwrite_trigger):
    assert ghostwrite_trigger.skill_invoked("ghostwrite")


def test_scope_triggers(scope_trigger):
    assert scope_trigger.skill_invoked("scope")


def test_summarize_triggers(summarize_trigger):
    assert summarize_trigger.skill_invoked("summarize")


def test_prompt_engineer_triggers(prompt_engineer_trigger):
    assert prompt_engineer_trigger.skill_invoked("prompt-engineer")


# --- Non-trigger tests ---


def test_trivia_no_skill_invoked(trivia_no_skill):
    assert trivia_no_skill.not_tool_called("Skill")
    assert trivia_no_skill.contains("4", on="final_message")


def test_fresh_draft_no_ghostwrite(no_ghostwrite_on_fresh):
    assert no_ghostwrite_on_fresh.not_skill_invoked("ghostwrite")
