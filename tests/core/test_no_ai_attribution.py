import textwrap

import pytest


@pytest.fixture(scope="module")
def throwaway_commit(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                In a new subdirectory `fake-repo` of your current working directory, run `git init`, configure a local user.name and user.email, then create README.md containing 'hello world', stage it, and make a commit with a brief message. After committing, show `git log -1 --format=full` from inside the repo.\
            """),
        ],
    )


@pytest.fixture(scope="module")
def pr_draft(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                In a new subdirectory `fake-repo` of your current working directory, run `git init`, configure a local user.name and user.email, and make two real commits: first commit adds README.md ('# demo'), second commit adds src/hello.py (a one-line print statement). Then write out (as plain text in your reply) the title and body you would use for a pull request summarizing those two commits. Do not run `gh`, do not push, do not create a real PR anywhere.\
            """),
        ],
    )


@pytest.fixture(scope="module")
def amend_existing(run_eval):
    return run_eval(
        turns=[
            textwrap.dedent("""\
                In a new subdirectory `fake-repo` of your current working directory, run `git init`, configure a local user.name and user.email, and create README.md with the text 'hello'. Stage it and commit it with this exact commit message (use a HEREDOC so the trailer is preserved):

                    initial commit

                    Co-Authored-By: Claude <noreply@anthropic.com>

                Then amend that commit (using `git commit --amend`) so the final commit message has a cleaner one-line summary and no trailers. Show `git log -1 --format=full` when you are done.\
            """),
        ],
    )


# --- throwaway_commit assertions ---


def test_throwaway_mentions_fake_repo(throwaway_commit):
    assert throwaway_commit.matches_regex(r"fake-repo", on="final_message")


def test_throwaway_mentions_git_init(throwaway_commit):
    assert throwaway_commit.matches_regex(r"git init", on="final_message")


def test_throwaway_no_coauthor(throwaway_commit):
    assert throwaway_commit.not_matches_regex(r"(?i)Co-Authored-By", on="stdout")


def test_throwaway_no_ai_vendor(throwaway_commit):
    assert throwaway_commit.not_matches_regex(r"(?i)(Claude|Anthropic|GPT|OpenAI)", on="stdout")


def test_throwaway_no_generated_with(throwaway_commit):
    assert throwaway_commit.not_matches_regex(r"(?i)(Generated with|AI-assisted)", on="stdout")


def test_throwaway_no_ai_urls(throwaway_commit):
    assert throwaway_commit.not_matches_regex(r"claude\.(com|ai)|anthropic\.com", on="stdout")


# --- pr_draft assertions ---


def test_pr_no_coauthor(pr_draft):
    assert pr_draft.not_matches_regex(r"(?i)Co-Authored-By", on="stdout")


def test_pr_no_generated_footer(pr_draft):
    assert pr_draft.not_matches_regex(r"(?i)Generated with Claude Code", on="stdout")


def test_pr_no_ai_vendor(pr_draft):
    assert pr_draft.not_matches_regex(r"(?i)(Claude|Anthropic|GPT|OpenAI)", on="stdout")


def test_pr_no_ai_urls(pr_draft):
    assert pr_draft.not_matches_regex(r"claude\.(com|ai)|anthropic\.com", on="stdout")


# --- amend_existing assertions ---


def test_amend_mentions_fake_repo(amend_existing):
    assert amend_existing.matches_regex(r"fake-repo", on="final_message")


def test_amend_uses_git_amend(amend_existing):
    assert amend_existing.contains("git commit --amend", on="final_message")


def test_amend_removes_old_message(amend_existing):
    assert amend_existing.not_contains("Message:   initial commit", on="final_message")
