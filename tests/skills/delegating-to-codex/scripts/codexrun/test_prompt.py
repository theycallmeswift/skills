"""Tests for prompt assembly and review diff presentation."""

from __future__ import annotations

from codexrun.prompt import INLINE_MAX_BYTES, build_prompt, build_resume_prompt
from codexrun.prompt import render_diff_section as render
from support.codex import diff_info, headings

ALL_SECTIONS = [
    "TASK TEMPLATE",
    "RULES",
    "BRIEF",
    "CONTEXT",
    "IMPLEMENTER REPORT",
    "NAMED RISKS",
    "DIFF",
]
ALL_INPUTS = {"rules": "R", "context": "C", "report": "REP", "risks": "RISK", "diff": "D"}


def test_supplied_sections_are_rendered_in_order():
    prompt = build_prompt(template="TEMPLATE", brief="BRIEF TEXT", **ALL_INPUTS)

    assert headings(prompt) == ALL_SECTIONS
    assert "TEMPLATE" in prompt and "BRIEF TEXT" in prompt


def test_missing_optional_sections_are_omitted():
    prompt = build_prompt(template="T", brief="B")
    assert headings(prompt) == ["TASK TEMPLATE", "BRIEF"]


def test_no_template_omits_the_template_section():
    prompt = build_prompt(template=None, brief="B", report="REP", diff="D")
    assert headings(prompt) == ["BRIEF", "IMPLEMENTER REPORT", "DIFF"]


def test_resume_prompt_is_just_the_brief():
    prompt = build_resume_prompt("Fix finding 1.\n")
    assert headings(prompt) == ["BRIEF"]
    assert "Fix finding 1." in prompt


def test_resume_prompt_restates_no_implementer_rules():
    # A resumed review inherits a read-only sandbox and a JSON schema, so a header that
    # restated the implement rules would order edits it cannot make in a shape it cannot use.
    prompt = build_resume_prompt("Finding 1 is wrong; look again.\n")

    forbidden = ("STATUS", "working tree", "git add", "commit", "stash", "checkout")
    assert [word for word in forbidden if word in prompt] == []
    assert "rules" in prompt


def test_small_diff_is_inlined():
    section = render(diff_info(["a.py", "b.py"], "diff --git a/a.py b/a.py\n+x\n"))
    assert "diff --git a/a.py b/a.py" in section
    assert "- a.py" in section and "- b.py" in section


def test_diff_over_two_files_is_replaced_by_the_command():
    section = render(diff_info(["a", "b", "c"], "diff --git SECRET-DIFF-BODY\n"))
    assert "SECRET-DIFF-BODY" not in section
    assert "git diff abc123" in section


def test_diff_over_the_size_limit_is_replaced_by_the_command():
    section = render(diff_info(["a"], "+" + "y" * INLINE_MAX_BYTES + "\n"))
    assert len(section) < 10_000
    assert "git diff abc123" in section


def test_diff_exactly_at_the_size_limit_is_inlined():
    body = "z" * INLINE_MAX_BYTES
    assert body in render(diff_info(["a"], body))
