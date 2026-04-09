from pathlib import Path

from tests.support.harness.setup import (
    cleanup_globs,
    compose,
    copy_files,
    skill_setup,
)


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    root = tmp_path / "project"
    (root / "skills" / "summarize").mkdir(parents=True)
    (root / "skills" / "summarize" / "SKILL.md").write_text("# Summarize")
    (root / "skills" / "summarize" / "references").mkdir()
    (root / "skills" / "summarize" / "references" / "examples.md").write_text(
        "# Examples"
    )
    (root / "AGENTS.md").write_text("# Agents")
    (root / "tests" / "support" / "fixtures").mkdir(parents=True)
    (root / "tests" / "support" / "fixtures" / "test-paper.pdf").write_bytes(
        b"fake pdf"
    )
    return root


def test_skill_setup_copies_skill_dir_and_agents(tmp_path):
    root = _make_project(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    setup_fn = skill_setup("summarize", root)
    setup_fn(cwd)

    assert (cwd / "skills" / "summarize" / "SKILL.md").read_text() == "# Summarize"
    assert (cwd / "skills" / "summarize" / "references" / "examples.md").exists()
    assert (cwd / "AGENTS.md").read_text() == "# Agents"


def test_skill_setup_prepends_preamble(tmp_path):
    root = _make_project(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    setup_fn = skill_setup("summarize", root)
    setup_fn(cwd)

    preamble_file = cwd / ".skill_preamble"
    assert preamble_file.exists()
    assert "skills/summarize/SKILL.md" in preamble_file.read_text()


def test_copy_files_copies_to_cwd(tmp_path):
    root = _make_project(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    copy_fn = copy_files("tests/support/fixtures/test-paper.pdf", project_root=root)
    copy_fn(cwd)

    assert (cwd / "test-paper.pdf").read_text() == "fake pdf"


def test_cleanup_globs_removes_matching_files(tmp_path):
    cwd = tmp_path / "cwd"
    (cwd / "references" / "specs").mkdir(parents=True)
    (cwd / "references" / "specs" / "2026-01-01-demo.md").write_text("x")
    (cwd / "references" / "specs" / "keep.md").write_text("y")

    cleanup_fn = cleanup_globs("references/specs/2026-*-demo*.md")
    cleanup_fn(cwd)

    assert not (cwd / "references" / "specs" / "2026-01-01-demo.md").exists()
    assert (cwd / "references" / "specs" / "keep.md").exists()


def test_compose_runs_all_functions_in_order(tmp_path):
    root = _make_project(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()

    composed = compose(
        skill_setup("summarize", root),
        copy_files("tests/support/fixtures/test-paper.pdf", project_root=root),
    )
    composed(cwd)

    assert (cwd / "skills" / "summarize" / "SKILL.md").exists()
    assert (cwd / "test-paper.pdf").exists()
