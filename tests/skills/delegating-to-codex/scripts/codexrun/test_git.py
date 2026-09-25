"""Tests for collecting and presenting the diff used by review jobs."""

from __future__ import annotations

from support.codex import commit_on_feature_branch


def test_uncommitted_small_diff_is_inlined_after_the_report_and_risks(ws):
    ws.write("a.py", "x = 2\n")
    ws.write("b.py", "y = 1\n")
    report = ws.write_input("report.md", "STATUS: DONE, all tests pass\n")

    result = ws.start(
        "--template",
        "review",
        "--sandbox",
        "read-only",
        "--schema",
        "--diff",
        "--report",
        report,
        "--risks",
        ws.risks,
        "--wait",
    )

    assert result.return_code == 0
    call = ws.calls()[-1]
    assert call["argv"][:4] == ["exec", "--sandbox", "read-only", "--cd"]
    assert "--ephemeral" not in call["argv"]
    assert "--output-schema" in call["argv"]
    prompt = call["stdin"]
    assert "=== IMPLEMENTER REPORT ===" in prompt and "all tests pass" in prompt
    assert "+x = 2" in prompt
    assert "b.py" in prompt
    assert prompt.index("=== NAMED RISKS ===") < prompt.index("=== DIFF ===")


def test_large_branch_diff_is_handed_over_as_a_command(ws):
    files = {name: f"# {name} BODYMARK\n" for name in ("c.py", "d.py", "e.py")}
    base = commit_on_feature_branch(ws, files)

    result = ws.start("--diff", "--wait")

    assert result.return_code == 0
    prompt = ws.calls()[-1]["stdin"]
    assert f"git diff {base}" in prompt
    assert "c.py" in prompt
    assert "BODYMARK" not in prompt


def test_explicit_base(ws):
    first = ws.head()
    ws.write("a.py", "x = 3\n")
    ws.git("commit", "-q", "-am", "second")

    result = ws.start("--base", first, "--wait")

    assert result.return_code == 0
    assert "+x = 3" in ws.calls()[-1]["stdin"]


def test_nothing_to_diff(ws):
    result = ws.start("--diff")

    assert result.return_code == 2 and "nothing to diff" in result.stderr
    assert ws.calls() == []


def test_input_files_in_the_worktree_do_not_count_as_changes(ws):
    base = commit_on_feature_branch(ws, {"a.py": "x = 9\n"})
    ws.write("brief.md", "Review it.\n")

    result = ws.start("--diff", "--wait", brief="brief.md")

    assert result.return_code == 0, result.stderr
    prompt = ws.calls()[-1]["stdin"]
    assert "merge-base with main" in prompt and base in prompt
    assert "+x = 9" in prompt
    assert "brief.md (untracked)" not in prompt
