#!/usr/bin/env python3
"""
Generate tokens.css from tokens.json: custom properties per theme plus @font-face rules.

Usage:
    tokens_to_css.py TOKENS_JSON [--out TOKENS_CSS]

The first entry in `themes` is the default and lands on `:root`; every other theme gets a
`[data-theme="<name>"]` block holding only the colour roles. Brand colours become
`--brand-<name>`, colour roles `--<name>`, scales `--space-*`, `--radius-*`, `--text-*`,
families `--font-*`. A colour written as `{brand.<name>}` compiles to `var(--brand-<name>)`.
Font files must be self-hosted paths: `data:` and http(s) URLs are refused, since a
`default-src 'self'` policy blocks them.

Exit codes: 0 written; 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REFERENCE_RE = re.compile(r"^\{brand\.([a-z0-9-]+)\}$")
HEADER = "/* Generated from tokens.json by tokens_to_css.py. Do not edit; regenerate. */"
SCALE_PREFIXES = {"space": "space", "radius": "radius"}


class TokenError(ValueError):
    """Raised when tokens.json is malformed or breaks a rule the CSS depends on."""


def load_tokens(path: Path) -> dict[str, Any]:
    """Read and minimally validate a tokens.json file.

    Args:
        path: Path to tokens.json.

    Returns:
        The parsed token document.

    Raises:
        TokenError: if the file is missing, not JSON, or lacks `themes`.
    """
    try:
        tokens = json.loads(path.read_text())
    except FileNotFoundError as error:
        raise TokenError(f"no such file: {path}") from error
    except json.JSONDecodeError as error:
        raise TokenError(f"{path} is not valid JSON: {error}") from error

    themes = tokens.get("themes")
    if not isinstance(themes, list) or not themes:
        raise TokenError("tokens.json needs a non-empty `themes` list, default theme first")

    return tokens


def brand_value(tokens: dict[str, Any], name: str) -> str:
    """Return the hex value of one brand colour.

    Raises:
        TokenError: if the brand colour is not defined.
    """
    entry = tokens.get("brand", {}).get(name)
    if entry is None:
        raise TokenError(f"unknown brand colour: brand.{name}")
    return entry["value"] if isinstance(entry, dict) else entry


def resolve_color(tokens: dict[str, Any], value: str) -> str:
    """Resolve a `{brand.<name>}` reference to its hex value; return plain values unchanged."""
    match = REFERENCE_RE.match(value)
    if match is None:
        return value
    return brand_value(tokens, match.group(1))


def color_for(tokens: dict[str, Any], name: str, theme: str) -> str:
    """Return the resolved hex of a colour role or `brand.<name>` in one theme.

    Raises:
        TokenError: if the name or the theme value is missing.
    """
    if name.startswith("brand."):
        return brand_value(tokens, name.removeprefix("brand."))

    role = tokens.get("color", {}).get(name)
    if role is None:
        raise TokenError(f"unknown colour role: {name}")
    if theme not in role:
        raise TokenError(f"colour role {name} has no value for theme {theme}")

    return resolve_color(tokens, role[theme])


def _css_color(value: str) -> str:
    """Compile a colour value: brand references become var(), hex passes through."""
    match = REFERENCE_RE.match(value)
    if match is None:
        return value
    return f"var(--brand-{match.group(1)})"


def _steps(group: Any) -> dict[str, str]:
    """Return a scale's steps whether written as `{steps: {...}}` or a flat mapping."""
    if not isinstance(group, dict):
        return {}
    steps = group.get("steps", group)
    return {key: value for key, value in steps.items() if key != "usage"}


def _font_face(font: dict[str, Any]) -> str:
    """Render one @font-face rule for a self-hosted font.

    Raises:
        TokenError: if the font file is a data: or remote URL.
    """
    file = font["file"]
    if file.startswith("data:") or re.match(r"^(https?:)?//", file):
        raise TokenError(
            f"font {font['family']} must be a self-hosted file, not {file[:40]!r}: "
            "a default-src 'self' policy blocks data: and third-party URLs"
        )

    lines = [
        "@font-face {",
        f'  font-family: "{font["family"]}";',
        f'  src: url("{file}") format("woff2");',
        f"  font-weight: {font.get('weight', 400)};",
        f"  font-style: {font.get('style', 'normal')};",
        "  font-display: swap;",
        "}",
    ]
    licence = font.get("licence")
    if licence:
        lines.insert(0, f"/* {font['family']}: {licence} */")

    return "\n".join(lines)


def _block(selector: str, declarations: list[str]) -> str:
    """Render one CSS rule from a selector and its declarations."""
    body = "\n".join(f"  {declaration}" for declaration in declarations)
    return f"{selector} {{\n{body}\n}}"


def render_css(tokens: dict[str, Any]) -> str:
    """Render the full tokens.css text from a token document.

    Raises:
        TokenError: if a colour role misses a theme, a reference is unknown, or a font is remote.
    """
    themes = tokens["themes"]
    default_theme = themes[0]
    colors = tokens.get("color", {})

    for name in colors:
        for theme in themes:
            color_for(tokens, name, theme)

    root = [f"--brand-{name}: {brand_value(tokens, name)};" for name in tokens.get("brand", {})]
    root += [f"--{name}: {_css_color(role[default_theme])};" for name, role in colors.items()]

    for group, prefix in SCALE_PREFIXES.items():
        root += [f"--{prefix}-{key}: {value};" for key, value in _steps(tokens.get(group)).items()]

    type_tokens = tokens.get("type", {})
    for name, family in type_tokens.get("family", {}).items():
        value = family["value"] if isinstance(family, dict) else family
        root.append(f"--font-{name}: {value};")
    root += [f"--text-{key}: {value};" for key, value in _steps(type_tokens.get("scale")).items()]

    parts = [HEADER]
    parts += [_font_face(font) for font in type_tokens.get("fonts", [])]
    parts.append(_block(":root", root))

    for theme in themes[1:]:
        overrides = [f"--{name}: {_css_color(role[theme])};" for name, role in colors.items()]
        parts.append(_block(f'[data-theme="{theme}"]', overrides))

    return "\n\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, render tokens.css, and write it."""
    parser = argparse.ArgumentParser(description="Generate tokens.css from tokens.json.")
    parser.add_argument("tokens", type=Path, help="path to tokens.json")
    parser.add_argument("--out", type=Path, help="output path (default: tokens.css beside it)")
    args = parser.parse_args(argv)

    out = args.out or args.tokens.with_name("tokens.css")
    try:
        css = render_css(load_tokens(args.tokens))
    except (TokenError, KeyError) as error:
        print(f"tokens_to_css: {error}", file=sys.stderr)
        return 2

    out.write_text(css)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
