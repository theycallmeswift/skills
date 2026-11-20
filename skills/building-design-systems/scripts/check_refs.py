#!/usr/bin/env python3
"""
Cross-check design docs against the CSS that ships.

Usage:
    check_refs.py DOCS_DIR --css FILE [--css FILE ...]

Reports, with file:line locations:
  - tokens a doc names (`--name` in backticks or `var(--name)`) that no CSS file defines;
  - CSS variables used with var() that no CSS file defines;
  - hex values in the docs that no CSS file contains, and the reverse.
Docs are the Markdown and JSON files under DOCS_DIR, so values kept in tokens.json count as
documented. It catches names and values only: a documented
state, size rule or layout the CSS never draws still needs reading by hand.

Exit codes: 0 docs and CSS agree; 1 mismatches found; 2 bad input.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable
from pathlib import Path

DOC_TOKEN_RE = re.compile(r"`(--[a-zA-Z0-9-]+)`|var\((--[a-zA-Z0-9-]+)")
CSS_DEFINITION_RE = re.compile(r"(--[a-zA-Z0-9-]+)\s*:")
CSS_USE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)")
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")

Location = tuple[Path, int]


def normalize_hex(value: str) -> str:
    """Lowercase a hex colour and expand `#rgb` to `#rrggbb`."""
    digits = value.lstrip("#").lower()
    if len(digits) == 3:
        digits = "".join(digit * 2 for digit in digits)
    return f"#{digits}"


def _scan(
    texts: dict[Path, str], pattern: re.Pattern[str], transform: Callable[[str], str] = str
) -> dict[str, list[Location]]:
    """Map each match of `pattern` (its first non-empty group, or the whole match) to locations."""
    found: dict[str, list[Location]] = {}
    for path, text in texts.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in pattern.finditer(line):
                groups = [group for group in match.groups() if group]
                key = transform(groups[0] if groups else match.group(0))
                found.setdefault(key, []).append((path, line_number))
    return found


def _strip_css_comments(text: str) -> str:
    """Blank out /* comments */ in CSS text, keeping line numbers intact."""

    def blank(match: re.Match[str]) -> str:
        """Replace every character of a comment except newlines with a space."""
        return re.sub(r"[^\n]", " ", match.group(0))

    return re.sub(r"/\*.*?\*/", blank, text, flags=re.S)


def find_mismatches(docs: list[Path], css: list[Path]) -> list[str]:
    """Compare docs and CSS; return one human-readable finding per mismatch."""
    doc_texts = {path: path.read_text() for path in docs}
    css_texts = {path: _strip_css_comments(path.read_text()) for path in css}

    defined = _scan(css_texts, CSS_DEFINITION_RE)
    used = _scan(css_texts, CSS_USE_RE)
    css_hex = _scan(css_texts, HEX_RE, normalize_hex)
    doc_tokens = _scan(doc_texts, DOC_TOKEN_RE)
    doc_hex = _scan(doc_texts, HEX_RE, normalize_hex)

    findings = []
    for token, places in sorted(doc_tokens.items()):
        if token not in defined:
            findings.append(f"doc names {token}, which no CSS defines ({_where(places)})")
    for token, places in sorted(used.items()):
        if token not in defined:
            findings.append(f"CSS uses {token}, which no CSS defines ({_where(places)})")
    for value, places in sorted(doc_hex.items()):
        if value not in css_hex:
            findings.append(f"doc value {value} is in no CSS ({_where(places)})")
    for value, places in sorted(css_hex.items()):
        if value not in doc_hex:
            findings.append(f"CSS value {value} is in no doc ({_where(places)})")

    return findings


def _where(places: list[Location]) -> str:
    """Format up to three locations as `file:line`, noting how many more there are."""
    shown = ", ".join(f"{path}:{line}" for path, line in places[:3])
    extra = len(places) - 3
    return f"{shown}, +{extra} more" if extra > 0 else shown


def _doc_files(docs_dir: Path) -> list[Path]:
    """Return the Markdown and JSON files under a docs directory, sorted."""
    return sorted([*docs_dir.rglob("*.md"), *docs_dir.rglob("*.json")])


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, print every mismatch, and exit 1 if there are any."""
    parser = argparse.ArgumentParser(description="Cross-check design docs against CSS.")
    parser.add_argument("docs", type=Path, help="directory of Markdown design docs")
    parser.add_argument("--css", type=Path, action="append", required=True, help="CSS file")
    args = parser.parse_args(argv)

    if not args.docs.is_dir():
        print(f"check_refs: not a directory: {args.docs}", file=sys.stderr)
        return 2
    missing = [path for path in args.css if not path.is_file()]
    if missing:
        print(f"check_refs: no such CSS file: {missing[0]}", file=sys.stderr)
        return 2

    findings = find_mismatches(_doc_files(args.docs), args.css)
    for finding in findings:
        print(finding)
    if not findings:
        print("docs and CSS agree on every token name and hex value")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
