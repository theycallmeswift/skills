import os

import pytest


def test_copy_context_files_and_dirs(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "AGENTS.md").write_text("# agents")
    skill = src / "skills" / "ghostwrite"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# skill")
    (skill / "references").mkdir()
    (skill / "references" / "voice.md").write_text("# voice")

    cwd = tmp_path / "cwd"
    cwd.mkdir()

    from tests.support.harness.runner import copy_context_paths

    copy_context_paths(
        [src / "AGENTS.md", src / "skills" / "ghostwrite"],
        project_root=src,
        cwd=cwd,
    )

    assert (cwd / "AGENTS.md").read_text() == "# agents"
    assert (cwd / "skills" / "ghostwrite" / "SKILL.md").read_text() == "# skill"
    assert (cwd / "skills" / "ghostwrite" / "references" / "voice.md").read_text() == "# voice"


def test_copy_context_resolves_symlinks(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "AGENTS.md").write_text("# real")
    (src / "CLAUDE.md").symlink_to(src / "AGENTS.md")

    cwd = tmp_path / "cwd"
    cwd.mkdir()

    from tests.support.harness.runner import copy_context_paths

    copy_context_paths([src / "CLAUDE.md"], project_root=src, cwd=cwd)

    target = cwd / "CLAUDE.md"
    assert target.read_text() == "# real"
    assert not target.is_symlink()


def test_snapshot_captures_only_new_or_modified(tmp_path):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "existing.md").write_text("original")

    from tests.support.harness.runner import capture_changes, snapshot_files

    before = snapshot_files(cwd)

    (cwd / "existing.md").write_text("modified")
    (cwd / "new.md").write_text("brand new")
    (cwd / "subdir").mkdir()
    (cwd / "subdir" / "deep.md").write_text("deep")

    after = capture_changes(cwd, before)
    assert set(after.keys()) == {"existing.md", "new.md", "subdir/deep.md"}
    assert after["existing.md"] == "modified"
    assert after["new.md"] == "brand new"
    assert after["subdir/deep.md"] == "deep"


def test_build_agent_options_omits_model_by_default(tmp_path):
    from tests.support.harness.runner import build_agent_options

    opts = build_agent_options(cwd=tmp_path, project_root=tmp_path)
    # When not specified, model should not be set (SDK default applies).
    assert getattr(opts, "model", None) in (None, "")


def test_build_agent_options_passes_model_when_given(tmp_path):
    from tests.support.harness.runner import build_agent_options

    opts = build_agent_options(
        cwd=tmp_path,
        project_root=tmp_path,
        model="claude-haiku-4-5-20251001",
    )
    assert opts.model == "claude-haiku-4-5-20251001"


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"),
    reason="requires Claude credentials",
)
async def test_run_claude_smoke(tmp_path):
    from tests.support.harness.runner import run_claude

    result = await run_claude(
        turns=["Reply with exactly the word 'pong' and nothing else."],
        cwd=tmp_path,
        context_paths=[],
        project_root=tmp_path,
        timeout_s=60,
    )
    assert result.exit_code == 0
    assert "pong" in result.stdout.lower()
    assert result.duration_s > 0
    assert result.input_tokens > 0


def test_run_eval_calls_setup_and_cleanup(tmp_path, monkeypatch):
    from tests.support.harness.matchers import EvalResult
    from tests.support.harness.runner import RunResult, run_eval

    setup_called = []
    cleanup_called = []

    def fake_setup(cwd):
        setup_called.append(str(cwd))
        (cwd / "setup.txt").write_text("done")

    def fake_cleanup(cwd):
        cleanup_called.append(str(cwd))

    async def fake_run_claude(turns, cwd, context_paths, project_root, timeout_s=300, model=None):
        # Verify setup ran before agent
        assert (cwd / "setup.txt").exists()
        return RunResult(
            stdout="hello",
            files_written={},
            input_tokens=1,
            output_tokens=1,
            duration_s=0.01,
            exit_code=0,
            tool_trace=[],
            turn_count=len(turns),
            final_message="hello",
        )

    import tests.support.harness.runner as runner_mod

    monkeypatch.setattr(runner_mod, "run_claude", fake_run_claude)

    result = run_eval(
        project_root=tmp_path,
        turns=["test"],
        setup=fake_setup,
        cleanup=fake_cleanup,
    )

    assert isinstance(result, EvalResult)
    assert result.final_message == "hello"
    assert len(setup_called) == 1
    assert len(cleanup_called) == 1


def test_run_eval_reads_preamble_file(tmp_path, monkeypatch):
    from tests.support.harness.runner import RunResult, run_eval

    captured_turns = []

    def fake_setup(cwd):
        (cwd / ".skill_preamble").write_text("Read SKILL.md first.\n\n")

    async def fake_run_claude(turns, cwd, context_paths, project_root, timeout_s=300, model=None):
        captured_turns.extend(turns)
        return RunResult(
            stdout="ok",
            files_written={},
            input_tokens=1,
            output_tokens=1,
            duration_s=0.01,
            exit_code=0,
            tool_trace=[],
            turn_count=len(turns),
            final_message="ok",
        )

    import tests.support.harness.runner as runner_mod

    monkeypatch.setattr(runner_mod, "run_claude", fake_run_claude)

    run_eval(
        project_root=tmp_path,
        turns=["Summarize this article"],
    )
    # Without setup writing a preamble, turns pass through unchanged
    assert captured_turns == ["Summarize this article"]

    captured_turns.clear()
    run_eval(
        project_root=tmp_path,
        turns=["Summarize this article"],
        setup=fake_setup,
    )
    assert captured_turns[0].startswith("Read SKILL.md first.")
    assert "Summarize this article" in captured_turns[0]
