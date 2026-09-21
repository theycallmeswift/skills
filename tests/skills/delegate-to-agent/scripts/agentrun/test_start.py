"""Tests for the start surface: template, sandbox, schema, and diff selection."""

from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent

import pytest
from agentrun import ASSETS
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


def test_start_ignores_its_own_input_files_in_the_worktree(ws):
    brief = ws.write("notes/brief.md", "Make x equal 2.\n")

    result = ws.start("--wait", brief=str(brief))

    assert result.return_code == 0, result.stderr
    assert len(ws.calls()) == 1


def test_start_still_refuses_other_untracked_files(ws):
    ws.write("brief.md", "Make x equal 2.\n")
    ws.write("stray.py", "junk\n")

    result = ws.start(brief="brief.md")

    assert result.return_code == 2 and "stray.py" in result.stderr
    assert ws.calls() == []


@pytest.mark.parametrize("sandbox", ["workspace-write", "read-only"])
def test_resume_skips_the_clean_tree_check(ws, sandbox):
    first = ws.start("--wait").job_id
    ws.write("a.py", "x = 2\n")

    result = ws.start("--sandbox", sandbox, "--resume", first, "--wait")

    assert result.return_code == 0, result.stderr
    assert ws.calls()[-1]["argv"][:2] == ["exec", "resume"]


def test_a_resume_that_escalates_to_a_writable_sandbox_refuses_a_dirty_worktree(ws):
    reviewed = ws.start("--sandbox", "read-only", "--wait").job_id
    ws.write("a.py", "x = 5\n")  # the user's own work: a read-only parent wrote nothing
    calls_before = len(ws.calls())

    result = ws.start("--sandbox", "workspace-write", "--resume", reviewed)

    assert result.return_code == 2 and "uncommitted" in result.stderr
    assert len(ws.calls()) == calls_before


def test_a_fix_round_on_a_writable_parent_keeps_the_dirty_tree_exemption(ws):
    first = ws.start("--sandbox", "workspace-write", "--wait").job_id
    ws.write("a.py", "x = 2\n")  # the delegate's own edits, which the fix round must see

    result = ws.start("--sandbox", "workspace-write", "--resume", first, "--wait")

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


def test_unknown_template_names_the_bundled_options(ws):
    result = ws.start("--template", "implmenet")

    assert result.return_code == 2
    assert "implmenet" in result.stderr
    assert "implement, review" in result.stderr
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


def test_missing_schema_file_is_named(ws):
    result = ws.start("--schema", "nope.json")

    assert result.return_code == 2 and "nope.json" in result.stderr
    assert ws.calls() == []


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


def test_a_resumed_job_is_recorded_as_a_resume(ws):
    first = ws.start("--template", "implement", "--wait").job_id

    resumed = ws.start("--template", "review", "--diff", "--resume", first, "--wait")

    assert resumed.return_code == 0, resumed.stderr
    assert ws.meta(resumed.job_id)["template"] == "resume"
    assert re.fullmatch(r"\d{8}-\d{6}-resume-[0-9a-f]{4}", resumed.job_id)
    assert "--template, --diff ignored on --resume" in resumed.stderr


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


def test_resume_inherits_the_read_only_sandbox_and_its_schema(ws):
    reviewed = ws.start(
        "--template", "review", "--sandbox", "read-only", "--schema", "--wait"
    ).job_id
    findings = ws.write_input("findings.md", "Finding 1 is wrong; look again.\n")

    result = ws.start("--resume", reviewed, "--wait", brief=findings)

    assert result.return_code == 0, result.stderr
    argv = ws.calls()[-1]["argv"]
    assert 'sandbox_mode="read-only"' in argv
    assert argv[argv.index("--output-schema") + 1] == REVIEW_SCHEMA


def test_an_explicit_sandbox_overrides_the_inherited_one(ws):
    reviewed = ws.start("--sandbox", "read-only", "--wait").job_id

    result = ws.start("--sandbox", "workspace-write", "--resume", reviewed, "--wait")

    assert result.return_code == 0, result.stderr
    assert 'sandbox_mode="workspace-write"' in ws.calls()[-1]["argv"]


def test_an_explicit_schema_overrides_the_inherited_one(ws):
    reviewed = ws.start("--sandbox", "read-only", "--schema", "--wait").job_id
    other = ws.write_input("other.json", '{"type": "object"}\n')

    result = ws.start("--schema", other, "--resume", reviewed, "--wait")

    assert result.return_code == 0, result.stderr
    argv = ws.calls()[-1]["argv"]
    assert argv[argv.index("--output-schema") + 1] == other


def test_resuming_a_writable_job_stays_writable_and_schemaless(ws):
    first = ws.start("--wait").job_id

    result = ws.start("--resume", first, "--wait")

    assert result.return_code == 0, result.stderr
    argv = ws.calls()[-1]["argv"]
    assert 'sandbox_mode="workspace-write"' in argv
    assert "--output-schema" not in argv


def test_a_relative_schema_is_recorded_as_an_absolute_path(ws, monkeypatch):
    ws.write_input("schema.json", '{"type": "object"}\n')
    monkeypatch.chdir(ws.inputs)

    started = ws.start(
        "--cd", str(ws.repo), "--sandbox", "read-only", "--schema", "schema.json", "--wait"
    )

    assert started.return_code == 0, started.stderr
    recorded = ws.meta(started.job_id)["schema"]
    assert Path(recorded).is_absolute()
    assert Path(recorded).resolve() == (ws.inputs / "schema.json").resolve()


def test_an_inherited_relative_schema_survives_a_resume_from_another_directory(ws, monkeypatch):
    ws.write_input("schema.json", '{"type": "object"}\n')
    monkeypatch.chdir(ws.inputs)
    reviewed = ws.start(
        "--cd", str(ws.repo), "--sandbox", "read-only", "--schema", "schema.json", "--wait"
    ).job_id
    monkeypatch.chdir(ws.root)

    result = ws.start("--cd", str(ws.repo), "--resume", reviewed, "--wait")

    assert result.return_code == 0, result.stderr
    argv = ws.calls()[-1]["argv"]
    inherited = argv[argv.index("--output-schema") + 1]
    assert Path(inherited).resolve() == (ws.inputs / "schema.json").resolve()


def test_an_inherited_schema_that_has_been_cleaned_up_is_named_as_missing(ws):
    schema = ws.write_input("scratch.json", '{"type": "object"}\n')
    reviewed = ws.start("--sandbox", "read-only", "--schema", schema, "--wait").job_id
    Path(schema).unlink()  # review inputs live in scratch space, which gets cleaned up
    calls_before = len(ws.calls())

    result = ws.start("--resume", reviewed)

    assert result.return_code == 2
    assert "inherited schema" in result.stderr and "scratch.json" in result.stderr
    assert len(ws.calls()) == calls_before


def test_resuming_a_job_that_recorded_no_sandbox_falls_back_to_the_default(ws):
    first = ws.start("--sandbox", "read-only", "--wait").job_id
    ws.forget_meta(first, "sandbox", "schema")

    result = ws.start("--resume", first, "--wait")

    assert result.return_code == 0, result.stderr
    argv = ws.calls()[-1]["argv"]
    assert 'sandbox_mode="workspace-write"' in argv
    assert "--output-schema" not in argv


def test_base_is_named_among_the_flags_a_resume_ignores(ws):
    first = ws.start("--wait").job_id

    resumed = ws.start("--base", "main", "--resume", first, "--wait")

    assert resumed.return_code == 0, resumed.stderr
    assert "--base ignored on --resume" in resumed.stderr
    assert "=== DIFF ===" not in ws.calls()[-1]["stdin"]


@pytest.mark.parametrize(
    "flags, sandbox, schema",
    [
        ((), "workspace-write", None),
        (("--sandbox", "read-only", "--schema"), "read-only", REVIEW_SCHEMA),
    ],
    ids=["defaults", "read-only-schema"],
)
def test_metadata_records_the_sandbox_and_schema(ws, flags, sandbox, schema):
    started = ws.start(*flags, "--wait")

    meta = ws.meta(started.job_id)
    assert (meta["sandbox"], meta["schema"]) == (sandbox, schema)
