"""Tests for request guards and environment preflight checks."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "argv",
    [
        ["start"],
        ["start", "--effort", "ultra"],
    ],
    ids=["missing", "unknown"],
)
def test_effort_is_required_and_validated(ws, argv):
    with pytest.raises(SystemExit) as exc:
        ws.run(*argv, "--brief", ws.brief)

    assert exc.value.code == 2


def test_brief_is_required(ws):
    result = ws.run("start", "--effort", "high")

    assert result.return_code == 2 and "--brief" in result.stderr


def test_missing_input_file_is_named(ws):
    result = ws.start("--risks", "nope.md")

    assert result.return_code == 2 and "nope.md" in result.stderr
    assert ws.calls() == []


def test_not_a_git_repo(ws):
    plain = ws.root / "plain"
    plain.mkdir()

    result = ws.start("--cd", str(plain))

    assert result.return_code == 2 and "git" in result.stderr.lower()


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


def test_preflight_ok(ws):
    assert ws.run("preflight").return_code == 0


@pytest.mark.parametrize(
    "env, message",
    [
        ({"PATH": "/usr/bin:/bin"}, "codex"),
        ({"FAKE_CODEX_LOGIN_RC": "1"}, "codex login"),
        ({"CODEX_THREAD_ID": "abc"}, "already running inside Codex"),
    ],
    ids=["codex-missing", "logged-out", "inside-codex"],
)
def test_preflight_failures(ws, monkeypatch, env, message):
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    result = ws.run("preflight")

    assert result.return_code == 3 and message in result.stderr


def test_start_runs_preflight(ws, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_LOGIN_RC", "1")

    result = ws.start()

    assert result.return_code == 3
    assert ws.calls() == []
