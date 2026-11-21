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


THEMED_CSS = """\
:root { --brand-paper: #F5F1E8; --bg: #101828; --stroke-outline: #84CAFF; --muted: #98A2B3; }
[data-theme="light"] { --bg: #FFFFFF; }
.row { min-height: 44px; }
.row[aria-selected="true"] { outline: 2px solid var(--stroke-outline); }
.row[data-state="queued"] { color: var(--muted); }
.lockup { background: var(--brand-paper); }
"""


@pytest.fixture
def themed(tmp_path: Path) -> tuple[Path, Path]:
    """A docs dir and a two-theme CSS file for the per-rule checks."""
    docs = tmp_path / "docs"
    docs.mkdir()
    css = tmp_path / "app.css"
    css.write_text(THEMED_CSS)
    return docs, css


def test_theme_table_value_that_differs_from_the_css_theme_is_reported(themed):
    docs, css = themed
    (docs / "color.md").write_text(
        "| Role | Dark | Light |\n|---|---|---|\n| `--bg` | `#101828` | `--brand-paper` |\n"
    )

    findings = _run(docs, css)

    assert any(
        "--bg in the light theme" in finding and "#f5f1e8" in finding and "#ffffff" in finding
        for finding in findings
    )
    assert not any("default theme" in finding for finding in findings)


def test_theme_table_that_matches_is_quiet(themed):
    docs, css = themed
    (docs / "color.md").write_text(
        "| Role | Dark | Light |\n|---|---|---|\n| `--bg` | `#101828` | `#FFFFFF` |\n"
    )

    assert not any(" theme as " in finding for finding in _run(docs, css))


def test_documented_state_the_css_never_draws_is_reported(themed):
    docs, css = themed
    (docs / "row.md").write_text(
        "| State | Treatment |\n|---|---|\n"
        "| queued | `--muted` text and a 1px dashed `--muted` outline |\n"
        "| selected | 2px ring in `--stroke-outline` |\n"
    )

    findings = _run(docs, css)

    assert any("state 'queued' an outline" in finding for finding in findings)
    assert not any("state 'selected'" in finding for finding in findings)


def test_documented_state_with_no_selector_is_reported(themed):
    docs, css = themed
    (docs / "row.md").write_text("| State | Treatment |\n|---|---|\n| loading | spinner |\n")

    assert any("state 'loading', which no CSS selector" in f for f in _run(docs, css))


def test_fixed_height_where_css_sets_min_height_is_reported(themed):
    docs, css = themed
    (docs / "row.md").write_text("Rows have a fixed height of 44px.\n")

    assert any("height of 44px" in f and "min-height" in f for f in _run(docs, css))


def test_minimum_height_wording_is_quiet(themed):
    docs, css = themed
    (docs / "row.md").write_text("Rows have a minimum height of 44px.\n")

    assert not any("height of 44px" in finding for finding in _run(docs, css))


def test_preview_only_rule_and_the_doc_that_describes_it_are_reported(themed, tmp_path):
    docs, css = themed
    (docs / "grid.md").write_text("On phones (under 600px wide) the grid has two columns.\n")
    preview = tmp_path / "preview.html"
    preview.write_text(
        "<html><head>\n<style>\n@media (max-width: 600px) {\n"
        "  .dashboard { grid-template-columns: repeat(2, 1fr); }\n}\n</style>\n</head></html>\n"
    )

    findings = check_refs.find_mismatches(sorted(docs.rglob("*.md")), [css], [preview])

    assert any("preview-only rule @media (max-width: 600px) .dashboard" in f for f in findings)
    assert any("600px layout that exists only in the preview" in f for f in findings)


def test_preview_rule_that_also_ships_is_quiet(themed, tmp_path):
    docs, css = themed
    preview = tmp_path / "preview.html"
    preview.write_text("<style>.row { min-height: 44px; }</style>")

    findings = check_refs.find_mismatches([], [css], [preview])

    assert not any("preview-only" in finding for finding in findings)


@pytest.mark.parametrize("text", ["See #100 for history.", "Jump to [add](#add).", "Issue #123."])
def test_issue_numbers_and_anchors_are_not_colours(project, text):
    docs, css = project
    (docs / "a.md").write_text(text + "\n")

    assert not any("doc value" in finding for finding in _run(docs, css))


def test_digit_only_hex_in_backticks_is_a_colour(project):
    docs, css = project
    (docs / "a.md").write_text("Ink `#101828`.\n")

    assert any("doc value #101828" in finding for finding in _run(docs, css))


def test_eval_fixture_reports_all_five_planted_mismatches():
    workspace = (
        Path(__file__).resolve().parents[4]
        / "evals/building-design-systems/doc-css-contradictions/workspace"
    )
    docs = workspace / "docs/design"

    findings = "\n".join(
        check_refs.find_mismatches(
            sorted(docs.rglob("*.md")),
            [workspace / "web/app.css"],
            [workspace / "preview/preview.html"],
        )
    )

    assert "doc names --stroke-ring" in findings
    assert "doc gives a height of 44px; the CSS sets only min-height" in findings
    assert "state 'queued' an outline" in findings
    assert "--bg in the light theme as `--brand-paper`" in findings
    assert "600px layout that exists only in the preview" in findings


def test_state_check_is_skipped_for_token_only_css(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "button.md").write_text("| State | Treatment |\n|---|---|\n| hover | darker |\n")
    css = tmp_path / "tokens.css"
    css.write_text(":root { --accent: #2563EB; }\n")

    assert not any("documents state" in finding for finding in _run(docs, css))
