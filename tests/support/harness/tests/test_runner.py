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
