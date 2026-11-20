"""Tests for check_refs.py: doc tokens vs CSS definitions, undefined var() uses, hex drift."""

from __future__ import annotations

from pathlib import Path

import check_refs
import pytest

CSS = """\
:root {
  --stroke-outline: #2563EB;
  --bg: #fff;
}
/* --old-token: #123456; */
.row { min-height: 40px; border-color: var(--stroke-outline); color: var(--missing); }
"""


@pytest.fixture
def project(tmp_path: Path) -> tuple[Path, Path]:
    """A docs dir and a CSS file that agree; tests edit them to plant mismatches."""
    docs = tmp_path / "docs"
    (docs / "components").mkdir(parents=True)
    css = tmp_path / "app.css"
    css.write_text(CSS)
    return docs, css


def _run(docs: Path, css: Path) -> list[str]:
    """Return the findings for one docs dir and one CSS file."""
    return check_refs.find_mismatches(sorted(docs.rglob("*.md")), [css])


def test_doc_token_missing_from_css_is_reported(project):
    docs, css = project
    (docs / "components" / "row.md").write_text("Selected rows draw `--stroke-ring`.\n")

    findings = _run(docs, css)

    assert any(
        "doc names --stroke-ring" in finding and "row.md:1" in finding for finding in findings
    )


def test_var_use_in_docs_counts_as_a_token_name(project):
    docs, css = project
    (docs / "a.md").write_text("border: 1px solid var(--stroke-ring);\n")

    assert any("--stroke-ring" in finding for finding in _run(docs, css))


def test_css_var_used_but_never_defined_is_reported(project):
    docs, css = project

    assert any("CSS uses --missing" in finding for finding in _run(docs, css))


def test_commented_out_css_is_ignored(project):
    docs, css = project
    (docs / "a.md").write_text("Old: `--old-token`.\n")

    assert any("doc names --old-token" in finding for finding in _run(docs, css))
    assert not any("#123456" in finding for finding in _run(docs, css))


def test_hex_in_docs_but_not_css_and_the_reverse(project):
    docs, css = project
    (docs / "a.md").write_text("Light background: `--brand-paper` (#F5F1E8). Outline #2563eb.\n")

    findings = _run(docs, css)

    assert any("doc value #f5f1e8 is in no CSS" in finding for finding in findings)
    assert any("CSS value #ffffff is in no doc" in finding for finding in findings)
    assert not any("#2563eb" in finding for finding in findings)


def test_short_hex_matches_long_hex(project):
    docs, css = project
    (docs / "a.md").write_text("bg #FFFFFF, outline #2563EB, `--bg`, `--stroke-outline`.\n")
    css.write_text(":root { --bg: #fff; --stroke-outline: #2563EB; }\n")

    assert _run(docs, css) == []


def test_cli_exit_codes(project, capsys):
    docs, css = project
    (docs / "a.md").write_text("bg #FFFFFF, outline #2563EB, `--bg`, `--stroke-outline`.\n")

    assert check_refs.main([str(docs), "--css", str(css)]) == 1
    assert "CSS uses --missing" in capsys.readouterr().out

    css.write_text(":root { --bg: #fff; --stroke-outline: #2563EB; }\n")
    assert check_refs.main([str(docs), "--css", str(css)]) == 0
    assert check_refs.main([str(docs / "nope"), "--css", str(css)]) == 2


def test_hex_in_tokens_json_counts_as_documented(project):
    docs, css = project
    (docs / "a.md").write_text("Outline `--stroke-outline`, bg `--bg`.\n")
    (docs / "tokens.json").write_text('{"color": {"bg": {"light": "#FFFFFF"}}, "x": "#2563EB"}')
    css.write_text(":root { --bg: #fff; --stroke-outline: #2563EB; }\n")

    assert check_refs.main([str(docs), "--css", str(css)]) == 0
