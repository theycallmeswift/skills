"""Tests for contrast_table.py: WCAG maths, targets, per-theme rows, and the failing exit."""

from __future__ import annotations

import json
from pathlib import Path

import contrast_table
import pytest

TOKENS = {
    "themes": ["dark", "light"],
    "brand": {"ink": {"value": "#0B1220"}},
    "color": {
        "bg": {"dark": "{brand.ink}", "light": "#FFFFFF"},
        "fg": {"dark": "#E6EAF2", "light": "#141C2B"},
        "muted": {"dark": "#9AA4B5", "light": "#5B6474"},
    },
    "pairings": [
        {"fg": "fg", "bg": "bg", "kind": "text"},
        {"fg": "muted", "bg": "bg", "kind": "text"},
    ],
}


def test_black_on_white_is_21():
    assert round(contrast_table.contrast_ratio("#000", "#ffffff"), 2) == 21.0


def test_ratio_is_symmetric():
    assert contrast_table.contrast_ratio("#123456", "#abcdef") == contrast_table.contrast_ratio(
        "#abcdef", "#123456"
    )


def test_known_grey_on_white():
    assert round(contrast_table.contrast_ratio("#767676", "#ffffff"), 2) == 4.54


def test_text_target_sits_above_the_wcag_floor():
    tokens = json.loads(json.dumps(TOKENS))
    tokens["color"]["muted"]["light"] = "#767676"

    row = contrast_table.evaluate(tokens)[1]

    assert row["target"] == 4.6
    assert row["light"]["ratio"] > 4.5
    assert row["light"]["passed"] is False


def test_mark_target_is_3_2():
    tokens = json.loads(json.dumps(TOKENS))
    tokens["pairings"] = [{"fg": "muted", "bg": "bg", "kind": "mark"}]

    assert contrast_table.evaluate(tokens)[0]["target"] == 3.2


def test_brand_reference_and_brand_names_resolve():
    tokens = json.loads(json.dumps(TOKENS))
    tokens["pairings"] = [{"fg": "fg", "bg": "brand.ink", "kind": "text"}]

    row = contrast_table.evaluate(tokens)[0]

    assert row["dark"]["ratio"] == contrast_table.contrast_ratio("#E6EAF2", "#0B1220")


def test_cell_truncates_so_a_near_miss_never_reads_as_the_target():
    cell = contrast_table._cell({"ratio": 4.5999, "passed": False})

    assert cell == "4.59 **FAIL**"


def test_markdown_has_a_column_per_theme():
    rows = contrast_table.evaluate(TOKENS)
    markdown = contrast_table.render_markdown(TOKENS, rows)

    assert "| Foreground | Background | Kind | Target | dark | light |" in markdown
    assert "| `fg` | `bg` | text | 4.6 |" in markdown


def test_cli_exits_0_when_every_pair_passes(tmp_path: Path):
    source = tmp_path / "tokens.json"
    source.write_text(json.dumps(TOKENS))

    assert contrast_table.main([str(source)]) == 0
    assert "FAIL" not in (tmp_path / "contrast.md").read_text()


def test_cli_exits_1_and_still_writes_the_table_on_a_failing_pair(tmp_path: Path, capsys):
    tokens = json.loads(json.dumps(TOKENS))
    tokens["color"]["muted"]["dark"] = "#3A4252"
    source = tmp_path / "tokens.json"
    source.write_text(json.dumps(tokens))

    assert contrast_table.main([str(source)]) == 1
    assert "**FAIL**" in (tmp_path / "contrast.md").read_text()
    assert "FAIL muted on bg (dark)" in capsys.readouterr().err


@pytest.mark.parametrize("pairings", [None, []])
def test_cli_exits_2_without_pairings(tmp_path: Path, pairings):
    tokens = json.loads(json.dumps(TOKENS))
    tokens["pairings"] = pairings
    source = tmp_path / "tokens.json"
    source.write_text(json.dumps(tokens))

    assert contrast_table.main([str(source)]) == 2


def test_unknown_role_is_bad_input(tmp_path: Path):
    tokens = json.loads(json.dumps(TOKENS))
    tokens["pairings"] = [{"fg": "nope", "bg": "bg", "kind": "text"}]
    source = tmp_path / "tokens.json"
    source.write_text(json.dumps(tokens))

    assert contrast_table.main([str(source)]) == 2


@pytest.mark.parametrize(("kind", "target"), [("text", 3.0), ("text", 4.49), ("mark", 2.5)])
def test_pairing_target_below_the_wcag_floor_is_refused(kind, target):
    tokens = json.loads(json.dumps(TOKENS))
    tokens["pairings"] = [{"fg": "muted", "bg": "bg", "kind": kind, "target": target}]

    with pytest.raises(contrast_table.TokenError, match="below the WCAG floor"):
        contrast_table.evaluate(tokens)


def test_pairing_may_raise_its_target():
    tokens = json.loads(json.dumps(TOKENS))
    tokens["pairings"] = [{"fg": "fg", "bg": "bg", "kind": "text", "target": 7.0}]

    assert contrast_table.evaluate(tokens)[0]["target"] == 7.0
