#!/usr/bin/env python3
"""
Compute WCAG 2.2 contrast ratios for foreground/background colour pairs.

Usage:
    contrast.py FG BG [FG BG ...] [--json]
    Colours are hex: #rrggbb or #rgb, the leading # optional.
Exit codes: 0 ok; 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

HEX_RE = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
# WCAG 2.2 thresholds: normal text, then large text (18pt, or 14pt bold).
AA_NORMAL = 4.5
AA_LARGE = 3.0
AAA_NORMAL = 7.0
AAA_LARGE = 4.5
SRGB_LINEAR_THRESHOLD = 0.04045


def parse_hex(text: str) -> tuple[int, int, int]:
    """Parse `#rrggbb` or `#rgb` (hash optional) into an (r, g, b) tuple of 0-255 ints.

    Raises:
        ValueError: if the text is not a 3- or 6-digit hex colour.
    """
    match = HEX_RE.match(text.strip())
    if match is None:
        raise ValueError(f"not a hex colour: {text!r}")

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


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    """Return the WCAG relative luminance of an (r, g, b) colour, 0.0 to 1.0."""
    red, green, blue = (_linearize(channel) for channel in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: tuple[int, int, int], background: tuple[int, int, int]) -> float:
    """Return the unrounded WCAG contrast ratio (1.0 to 21.0) between two colours."""
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def evaluate_pair(fg: str, bg: str) -> dict[str, object]:
    """Score one pair against AA/AAA for normal and large text, using the unrounded ratio."""
    ratio = contrast_ratio(parse_hex(fg), parse_hex(bg))
    return {
        "fg": fg,
        "bg": bg,
        "ratio": round(ratio, 2),
        "aa_normal": ratio >= AA_NORMAL,
        "aa_large": ratio >= AA_LARGE,
        "aaa_normal": ratio >= AAA_NORMAL,
        "aaa_large": ratio >= AAA_LARGE,
    }


def format_pair(result: dict[str, object]) -> str:
    """Render one evaluated pair as the one-line human report."""

    def verdict(passed: object) -> str:
        """Spell a boolean as PASS or FAIL."""
        return "PASS" if passed else "FAIL"

    return (
        f"{result['fg']} on {result['bg']}: {result['ratio']:.2f}:1  "
        f"AA normal {verdict(result['aa_normal'])}  AA large {verdict(result['aa_large'])}  "
        f"AAA normal {verdict(result['aaa_normal'])}  AAA large {verdict(result['aaa_large'])}"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description="WCAG 2.2 contrast ratios for colour pairs.")
    parser.add_argument("colors", nargs="+", metavar="FG BG", help="foreground/background pairs")
    parser.add_argument("--json", action="store_true", help="print a JSON list instead of lines")
    args = parser.parse_args(argv)

    if len(args.colors) % 2 != 0:
        print("error: colours must come in FG BG pairs", file=sys.stderr)
        return 2

    try:
        results = [
            evaluate_pair(args.colors[index], args.colors[index + 1])
            for index in range(0, len(args.colors), 2)
        ]
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            print(format_pair(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
