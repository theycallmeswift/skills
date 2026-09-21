"""Tests for the start surface: template, sandbox, schema, and diff selection."""

from __future__ import annotations

import re
from textwrap import dedent

import pytest
from codexrun import ASSETS
from support.codex import commit_on_feature_branch

REVIEW_SCHEMA = str(ASSETS / "review-output.schema.json")


def test_read_only_job_records_a_thread_and_can_be_resumed(ws, monkeypatch):
    monkeypatch.setenv("FAKE_THREAD_ID", "thread-review")
    reviewed = ws.start("--template", "review", "--sandbox", "read-only", "--wait")
    findings = ws.write_input("findings.md", "Finding 1 is wrong; look again.\n")

    result = ws.start(
        "--sandbox",
        "read-only",
        "--resume",
        reviewed.job_id,
        "--wait",
        brief=findings,
    )

    assert result.return_code == 0, result.stderr
    assert ws.meta(reviewed.job_id)["thread_id"] == "thread-review"
    call = ws.calls()[-1]
    assert call["argv"][:3] == ["exec", "resume", "thread-review"]
    assert 'sandbox_mode="read-only"' in call["argv"]
    assert "Finding 1 is wrong" in call["stdin"]


def test_workspace_write_refuses_a_dirty_worktree(ws):
    ws.write("a.py", "x = 5\n")

    result = ws.start()

    assert result.return_code == 2 and "uncommitted" in result.stderr
    assert ws.calls() == []


def test_read_only_runs_on_a_dirty_worktree(ws):
    ws.write("a.py", "x = 5\n")

    result = ws.start("--sandbox", "read-only", "--wait")

    assert result.return_code == 0, result.stderr
    assert len(ws.calls()) == 1


@pytest.mark.parametrize("sandbox", ["workspace-write", "read-only"])
def test_resume_skips_the_clean_tree_check(ws, sandbox):
    first = ws.start("--wait").job_id
    ws.write("a.py", "x = 2\n")

    result = ws.start("--sandbox", sandbox, "--resume", first, "--wait")

    assert result.return_code == 0, result.stderr
    assert ws.calls()[-1]["argv"][:2] == ["exec", "resume"]


def test_template_name_resolves_to_the_bundled_asset(ws):
    result = ws.start("--template", "implement", "--wait")

    assert result.return_code == 0, result.stderr
    prompt = ws.calls()[-1]["stdin"]
    assert "=== TASK TEMPLATE ===" in prompt
    assert (ASSETS / "implement-prompt.md").read_text().strip() in prompt


def test_template_path_is_read_from_disk(ws):
    template = ws.write_input(
        "custom.md",
        dedent("""\
            You are a documentation editor.
            Rewrite the brief's target file.
        """),
    )

    result = ws.start("--template", template, "--wait")

    assert result.return_code == 0, result.stderr
    assert "You are a documentation editor." in ws.calls()[-1]["stdin"]


def test_unknown_template_path_is_reported(ws):
    result = ws.start("--template", "nope.md")

    assert result.return_code == 2 and "nope.md" in result.stderr
    assert ws.calls() == []


def test_without_a_template_the_prompt_has_no_template_section(ws):
    result = ws.start("--wait")

    assert result.return_code == 0, result.stderr
    assert "=== TASK TEMPLATE ===" not in ws.calls()[-1]["stdin"]


def test_bare_schema_uses_the_bundled_review_schema(ws):
    result = ws.start("--schema", "--wait")

    assert result.return_code == 0, result.stderr
    argv = ws.calls()[-1]["argv"]
    assert argv[argv.index("--output-schema") + 1] == REVIEW_SCHEMA


def test_schema_file_is_passed_through(ws):
    schema = ws.write_input("schema.json", '{"type": "object"}\n')

    result = ws.start("--schema", schema, "--wait")

    assert result.return_code == 0, result.stderr
    argv = ws.calls()[-1]["argv"]
    assert argv[argv.index("--output-schema") + 1] == schema


def test_without_a_schema_no_output_schema_flag(ws):
    result = ws.start("--wait")

    assert result.return_code == 0, result.stderr
    assert "--output-schema" not in ws.calls()[-1]["argv"]


def test_diff_attaches_the_worktree_diff(ws):
    ws.write("a.py", "x = 7\n")

    result = ws.start("--sandbox", "read-only", "--diff", "--wait")

    assert result.return_code == 0, result.stderr
    prompt = ws.calls()[-1]["stdin"]
    assert "=== DIFF ===" in prompt and "+x = 7" in prompt


def test_base_implies_a_diff(ws):
    commit_on_feature_branch(ws, {"c.py": "z = 1\n"})

    result = ws.start("--base", "main", "--wait")

    assert result.return_code == 0, result.stderr
    prompt = ws.calls()[-1]["stdin"]
    assert "=== DIFF ===" in prompt and "+z = 1" in prompt


def test_without_a_diff_flag_the_prompt_has_no_diff_section(ws):
    ws.write("a.py", "x = 7\n")

    result = ws.start("--sandbox", "read-only", "--wait")

    assert result.return_code == 0, result.stderr
    assert "=== DIFF ===" not in ws.calls()[-1]["stdin"]


@pytest.mark.parametrize(
    "flags, template",
    [
        ((), "job"),
        (("--template", "review"), "review"),
    ],
    ids=["no-template", "bundled-template"],
)
def test_metadata_records_the_template(ws, flags, template):
    started = ws.start(*flags, "--wait")

    assert ws.meta(started.job_id)["template"] == template


def test_a_template_path_stays_filename_safe_in_the_job_id(ws):
    template = ws.write_input("house-style.md", "Write in the house style.\n")

    started = ws.start("--template", template, "--wait")

    assert ws.meta(started.job_id)["template"] == template
    assert re.fullmatch(r"\d{8}-\d{6}-house-style-[0-9a-f]{4}", started.job_id)
