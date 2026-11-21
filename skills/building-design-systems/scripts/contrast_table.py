#!/usr/bin/env python3
"""
Compute every allowed colour pairing in tokens.json, per theme, and write contrast.md.

Usage:
    contrast_table.py TOKENS_JSON [--out CONTRAST_MD]

Pairings come from the `pairings` list in tokens.json: `{"fg": "muted", "bg": "surface",
"kind": "text"}`, where fg and bg name a colour role or `brand.<name>`. Targets sit above the
WCAG floors so rounding can't tip a pair into failure: text 4.6:1 (floor 4.5), marks 3.2:1
(floor 3.0). A pairing may set a higher `target`, never one below its floor.

Exit codes: 0 every pair meets its target; 1 one or more pairs fail (table still written);
2 bad input.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from tokens_to_css import TokenError, color_for, load_tokens

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
TARGETS = {"text": 4.6, "mark": 3.2}
# A pairing may raise its own target but never drop below the WCAG AA floor for its kind.
FLOORS = {"text": 4.5, "mark": 3.0}
SRGB_LINEAR_THRESHOLD = 0.04045


def parse_hex(text: str) -> tuple[int, int, int]:
    """Parse `#rrggbb` or `#rgb` into an (r, g, b) tuple of 0-255 ints.

    Raises:
        TokenError: if the text is not a 3- or 6-digit hex colour.
    """
    match = HEX_RE.match(text.strip())
    if match is None:
        raise TokenError(f"not a hex colour: {text!r}")

    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(digit * 2 for digit in digits)

    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def _linearize(channel: int) -> float:
    """Convert one 0-255 sRGB channel to linear light."""
    value = channel / 255
    if value <= SRGB_LINEAR_THRESHOLD:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """Return the WCAG relative luminance of a hex colour, 0.0 to 1.0."""
    red, green, blue = (_linearize(channel) for channel in parse_hex(hex_color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the unrounded WCAG contrast ratio (1.0 to 21.0) between two hex colours."""
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def evaluate(tokens: dict[str, Any]) -> list[dict[str, Any]]:
    """Score every pairing in every theme against its target.

    Returns:
        One row per pairing: fg, bg, kind, target, and per-theme `{ratio, passed}` cells.

    Raises:
        TokenError: if there are no pairings, a kind is unknown, or a colour is missing.
    """
    pairings = tokens.get("pairings")
    if not pairings:
        raise TokenError("tokens.json has no `pairings` list to check")

    rows = []
    for pairing in pairings:
        kind = pairing.get("kind", "text")
        if kind not in TARGETS:
            raise TokenError(f"unknown pairing kind {kind!r}; use text or mark")
        target = float(pairing.get("target", TARGETS[kind]))
        if target < FLOORS[kind]:
            raise TokenError(
                f"{pairing['fg']} on {pairing['bg']}: target {target} is below the WCAG floor "
                f"of {FLOORS[kind]} for {kind}"
            )

        cells = {}
        for theme in tokens["themes"]:
            ratio = contrast_ratio(
                color_for(tokens, pairing["fg"], theme), color_for(tokens, pairing["bg"], theme)
            )
            cells[theme] = {"ratio": ratio, "passed": ratio >= target}

        rows.append(
            {"fg": pairing["fg"], "bg": pairing["bg"], "kind": kind, "target": target, **cells}
        )

    return rows


def _shown(ratio: float) -> str:
    """Format a ratio to two places, truncating so 4.599 never shows as a passing 4.60."""
    return f"{int(ratio * 100) / 100:.2f}"


def _cell(cell: dict[str, Any]) -> str:
    """Format one ratio cell with its pass or fail mark."""
    mark = "pass" if cell["passed"] else "**FAIL**"
    return f"{_shown(cell['ratio'])} {mark}"


def render_markdown(tokens: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    """Render contrast.md from evaluated rows."""
    themes = tokens["themes"]
    header = ["Foreground", "Background", "Kind", "Target", *themes]
    lines = [
        "# Contrast",
        "",
        "Generated from `tokens.json` by `contrast_table.py`. Do not hand-edit; regenerate.",
        f"Targets: text {TARGETS['text']}:1, marks {TARGETS['mark']}:1. "
        "Use only the pairings listed here.",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "---|" * len(header),
    ]
    for row in rows:
        cells = [f"`{row['fg']}`", f"`{row['bg']}`", row["kind"], f"{row['target']}"]
        cells += [_cell(row[theme]) for theme in themes]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, write contrast.md, and exit non-zero on any failing pair."""
    parser = argparse.ArgumentParser(description="Write contrast.md from tokens.json.")
    parser.add_argument("tokens", type=Path, help="path to tokens.json")
    parser.add_argument("--out", type=Path, help="output path (default: contrast.md beside it)")
    args = parser.parse_args(argv)

    out = args.out or args.tokens.with_name("contrast.md")
    try:
        tokens = load_tokens(args.tokens)
        rows = evaluate(tokens)
    except (TokenError, KeyError) as error:
        print(f"contrast_table: {error}", file=sys.stderr)
        return 2

    out.write_text(render_markdown(tokens, rows))
    print(f"wrote {out}")

    failures = [
        (row, theme) for row in rows for theme in tokens["themes"] if not row[theme]["passed"]
    ]
    for row, theme in failures:
        ratio = _shown(row[theme]["ratio"])
        print(
            f"FAIL {row['fg']} on {row['bg']} ({theme}): {ratio} < {row['target']}",
            file=sys.stderr,
        )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
