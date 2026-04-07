from pathlib import Path


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

    from tests.support.harness.runner import snapshot_files, capture_changes
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
