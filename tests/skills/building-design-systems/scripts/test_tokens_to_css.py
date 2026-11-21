"""Tests for tokens_to_css.py: per-theme custom properties, brand references, fonts, exit codes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import tokens_to_css

TOKENS = {
    "themes": ["dark", "light"],
    "brand": {"ink": {"value": "#0B1220", "usage": "Logo ink."}},
    "color": {
        "bg": {"dark": "{brand.ink}", "light": "#FFFFFF", "usage": "Page background."},
        "muted": {"dark": "#9AA4B5", "light": "#5B6474", "usage": "Secondary text."},
    },
    "space": {"usage": "Gaps.", "steps": {"1": "4px", "2": "8px"}},
    "radius": {"usage": "Corners.", "steps": {"sm": "4px"}},
    "type": {
        "fonts": [
            {"family": "Inter", "weight": "400 700", "file": "/fonts/inter.woff2", "licence": "OFL"}
        ],
        "family": {"sans": {"value": "Inter, sans-serif", "usage": "UI text."}},
        "scale": {"usage": "Sizes.", "steps": {"md": "15px"}},
    },
}


def _block(css: str, selector: str) -> str:
    """Return the body of the first rule with this selector."""
    start = css.index(selector + " {")
    return css[start : css.index("}", start)]


def test_default_theme_lands_on_root():
    root = _block(tokens_to_css.render_css(TOKENS), ":root")

    assert "--muted: #9AA4B5;" in root
    assert "--brand-ink: #0B1220;" in root


def test_other_themes_get_a_data_theme_block_with_colour_roles_only():
    light = _block(tokens_to_css.render_css(TOKENS), '[data-theme="light"]')

    assert "--bg: #FFFFFF;" in light
    assert "--muted: #5B6474;" in light
    assert "--space-1" not in light


def test_brand_reference_compiles_to_var():
    root = _block(tokens_to_css.render_css(TOKENS), ":root")

    assert "--bg: var(--brand-ink);" in root


def test_scales_and_type_become_prefixed_properties():
    root = _block(tokens_to_css.render_css(TOKENS), ":root")

    for declaration in ("--space-2: 8px;", "--radius-sm: 4px;", "--text-md: 15px;"):
        assert declaration in root
    assert "--font-sans: Inter, sans-serif;" in root


def test_self_hosted_font_gets_font_face():
    css = tokens_to_css.render_css(TOKENS)

    assert '@font-face {\n  font-family: "Inter";' in css
    assert 'src: url("/fonts/inter.woff2") format("woff2");' in css
    assert "font-weight: 400 700;" in css


@pytest.mark.parametrize(
    "file",
    ["data:font/woff2;base64,AAAA", "https://fonts.gstatic.com/x.woff2", "//cdn.example/x.woff2"],
)
def test_remote_or_data_font_is_refused(file):
    tokens = json.loads(json.dumps(TOKENS))
    tokens["type"]["fonts"][0]["file"] = file

    with pytest.raises(tokens_to_css.TokenError, match="self-hosted"):
        tokens_to_css.render_css(tokens)


def test_role_missing_a_theme_is_an_error():
    tokens = json.loads(json.dumps(TOKENS))
    del tokens["color"]["muted"]["light"]

    with pytest.raises(tokens_to_css.TokenError, match="muted has no value for theme light"):
        tokens_to_css.render_css(tokens)


def test_unknown_brand_reference_is_an_error():
    tokens = json.loads(json.dumps(TOKENS))
    tokens["color"]["bg"]["dark"] = "{brand.nope}"

    with pytest.raises(tokens_to_css.TokenError, match="brand.nope"):
        tokens_to_css.render_css(tokens)


def test_cli_writes_css_beside_tokens(tmp_path: Path):
    source = tmp_path / "tokens.json"
    source.write_text(json.dumps(TOKENS))

    assert tokens_to_css.main([str(source)]) == 0
    assert (tmp_path / "tokens.css").read_text().startswith("/* Generated from tokens.json")


def test_cli_exits_2_without_themes(tmp_path: Path, capsys):
    source = tmp_path / "tokens.json"
    source.write_text(json.dumps({"color": {}}))

    assert tokens_to_css.main([str(source)]) == 2
    assert "themes" in capsys.readouterr().err
