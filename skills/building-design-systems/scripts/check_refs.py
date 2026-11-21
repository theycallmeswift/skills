#!/usr/bin/env python3
"""
Cross-check design docs against the CSS that ships.

Usage:
    check_refs.py DOCS_DIR --css FILE [--css FILE ...] [--preview FILE ...]

Docs are the Markdown and JSON files under DOCS_DIR (values kept in tokens.json count as
documented). `--css` files ship; `--preview` files (HTML with <style> blocks, or CSS) don't.
Reports, with file:line locations:
  - tokens a doc names (`--name` in backticks or `var(--name)`) that no shipped CSS defines;
  - CSS variables used with var() that no shipped CSS defines;
  - hex values in the docs that no shipped CSS contains, and the reverse;
  - per-theme token values in a doc table (columns named after themes) that differ from the
    value the CSS resolves for that theme;
  - states in a doc state table that no CSS selector mentions, or whose documented outline,
    ring, border, underline, shadow, opacity or background no matching CSS rule declares
    (skipped when the CSS holds only token blocks);
  - a documented height that the CSS sets only as min-height or max-height;
  - rules that exist only in a preview, and doc lines that describe them.
Wording rules (truncation, tone, do/don't) still need reading by hand.

Exit codes: 0 docs and CSS agree; 1 mismatches found; 2 bad input.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

DOC_TOKEN_RE = re.compile(r"`(--[a-zA-Z0-9-]+)`|var\((--[a-zA-Z0-9-]+)")
CSS_DEFINITION_RE = re.compile(r"(--[a-zA-Z0-9-]+)\s*:")
CSS_USE_RE = re.compile(r"var\(\s*(--[a-zA-Z0-9-]+)")
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
# In docs a colour sits in backticks, after ":" or "(", or holds a hex letter. That skips issue
# references (`#100`) in prose and link anchors (`](#add)`), which look like hex.
DOC_HEX_RE = re.compile(
    r"(?<=`)#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b"
    r"|(?<=[:(] )#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b"
    r"|(?<=[:(])(?<!\]\()#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b"
    r"|(?<![\w#(`])#(?=[0-9]*[a-fA-F])(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b"
)
THEME_SELECTOR_RE = re.compile(r"""\[data-theme=["']?([a-z0-9-]+)["']?\]""")
STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S | re.I)
DOC_HEIGHT_RE = re.compile(r"(?:height\s+of\s+|height:\s*)(\d+)px|(\d+)px\s+tall", re.I)
BOUND_WORD_RE = re.compile(r"\b(min|max|minimum|maximum|at least)\b", re.I)
PX_RE = re.compile(r"\d+px")
# Doc table columns that mean the default theme (the one on :root).
DEFAULT_THEME_WORDS = {"default", "dark", "root", "value"}
# A documented treatment word, and the CSS properties that would draw it.
TREATMENT_PROPERTIES = {
    "outline": ("outline", "box-shadow", "border"),
    "ring": ("outline", "box-shadow", "border"),
    "border": ("border", "outline", "box-shadow"),
    "underline": ("text-decoration",),
    "shadow": ("box-shadow",),
    "opacity": ("opacity",),
    "background": ("background",),
}
ROOT = ":root"

Location = tuple[Path, int]
Themes = dict[str, dict[str, tuple[str, Location]]]


@dataclass(frozen=True)
class Rule:
    """One CSS rule: its selector, enclosing @media (or ""), declarations and location."""

    selector: str
    media: str
    declarations: tuple[tuple[str, str], ...]
    path: Path
    line: int


def normalize_hex(value: str) -> str:
    """Lowercase a hex colour and expand `#rgb` to `#rrggbb`."""
    digits = value.lstrip("#").lower()
    if len(digits) == 3:
        digits = "".join(digit * 2 for digit in digits)
    return f"#{digits}"


def _blank_comments(text: str) -> str:
    """Blank out /* comments */ in CSS text, keeping line numbers intact."""

    def blank(match: re.Match[str]) -> str:
        """Replace every character of a comment except newlines with a space."""
        return re.sub(r"[^\n]", " ", match.group(0))

    return re.sub(r"/\*.*?\*/", blank, text, flags=re.S)


def _declarations(body: str) -> tuple[tuple[str, str], ...]:
    """Split a rule body into (lowercased property, value) pairs, skipping empty ones."""
    pairs = []
    for part in body.split(";"):
        name, _, value = part.partition(":")
        if value.strip():
            pairs.append((name.strip().lower(), value.strip()))
    return tuple(pairs)


def parse_css(text: str, path: Path, line_offset: int = 0) -> list[Rule]:
    """Parse CSS into flat rules, keeping the @media each sits in.

    Args:
        text: CSS source.
        path: File the CSS came from, for locations.
        line_offset: Lines before `text` in its file (for <style> blocks inside HTML).

    Returns:
        Every rule with at least one declaration.
    """
    text = _blank_comments(text)
    rules: list[Rule] = []
    stack: list[tuple[str, int]] = []
    start = 0

    for index, char in enumerate(text):
        if char == "{":
            line = line_offset + text.count("\n", 0, index) + 1
            stack.append((" ".join(text[start:index].split()), line))
            start = index + 1
        elif char == "}":
            body = text[start:index]
            start = index + 1
            if not stack:
                continue
            prelude, line = stack.pop()
            if prelude.startswith("@"):
                continue
            media = next((outer for outer, _ in reversed(stack) if outer.startswith("@media")), "")
            declarations = _declarations(body)
            if declarations:
                rules.append(Rule(prelude, media, declarations, path, line))

    return rules


def _preview_rules(path: Path) -> list[Rule]:
    """Parse a preview file: the <style> blocks of an HTML file, or a whole CSS file."""
    text = path.read_text()
    if path.suffix.lower() not in {".html", ".htm"}:
        return parse_css(text, path)

    rules = []
    for match in STYLE_BLOCK_RE.finditer(text):
        rules += parse_css(match.group(1), path, text.count("\n", 0, match.start(1)))
    return rules


def _theme_of(selector: str) -> str | None:
    """Return the theme a selector sets tokens for: ROOT, a data-theme name, or None."""
    match = THEME_SELECTOR_RE.search(selector)
    if match:
        return match.group(1)
    if selector in {":root", "html"}:
        return ROOT
    return None


def theme_values(rules: list[Rule]) -> Themes:
    """Map each theme to its custom properties: name -> (raw value, location)."""
    themes: Themes = {}
    for rule in rules:
        theme = _theme_of(rule.selector)
        if theme is None or rule.media:
            continue
        for name, value in rule.declarations:
            if name.startswith("--"):
                themes.setdefault(theme, {})[name] = (value, (rule.path, rule.line))
    return themes


def resolve(themes: Themes, token: str, theme: str) -> str:
    """Resolve a token to a normalized hex in a theme, following var() and falling back to ROOT.

    Returns:
        The hex, or "" when the token is undefined, circular or not a colour.
    """
    seen = set()
    while token not in seen:
        seen.add(token)
        entry = themes.get(theme, {}).get(token) or themes.get(ROOT, {}).get(token)
        if entry is None:
            return ""
        reference = CSS_USE_RE.search(entry[0])
        if reference:
            token = reference.group(1)
            continue
        hex_match = HEX_RE.search(entry[0])
        return normalize_hex(hex_match.group(0)) if hex_match else ""
    return ""


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


def _cells(line: str) -> list[str]:
    """Split a Markdown table row into stripped cells."""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _tables(text: str) -> list[tuple[list[str], list[tuple[int, list[str]]]]]:
    """Return each Markdown table as (lowercased header cells, [(line number, row cells)])."""
    tables = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        starts_table = lines[index].lstrip().startswith("|") and index + 1 < len(lines)
        if starts_table and re.match(r"^\s*\|?\s*:?-{3,}", lines[index + 1]):
            header = [cell.strip("`").lower() for cell in _cells(lines[index])]
            rows = []
            index += 2
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                rows.append((index + 1, _cells(lines[index])))
                index += 1
            tables.append((header, rows))
        else:
            index += 1
    return tables


def _where(places: list[Location]) -> str:
    """Format up to three locations as `file:line`, noting how many more there are."""
    shown = ", ".join(f"{path}:{line}" for path, line in places[:3])
    extra = len(places) - 3
    return f"{shown}, +{extra} more" if extra > 0 else shown


def _theme_columns(header: list[str], named_themes: set[str]) -> dict[int, str]:
    """Map a token table's value columns to themes: data-theme names, else the default theme."""
    columns = {}
    for position, name in enumerate(header[1:], start=1):
        if name in named_themes:
            columns[position] = name
        elif name in DEFAULT_THEME_WORDS:
            columns[position] = ROOT
    return columns


def _documented_value(cell: str, themes: Themes, theme: str) -> str:
    """Return a doc cell's colour as normalized hex: its own hex, else its token resolved."""
    hex_match = HEX_RE.search(cell)
    if hex_match:
        return normalize_hex(hex_match.group(0))
    token_match = DOC_TOKEN_RE.search(cell)
    if token_match:
        return resolve(themes, token_match.group(1) or token_match.group(2), theme)
    return ""


def check_theme_tables(doc_texts: dict[Path, str], rules: list[Rule]) -> list[str]:
    """Compare per-theme token values in doc tables with the values the CSS resolves."""
    themes = theme_values(rules)
    findings = []
    for path, text in doc_texts.items():
        for header, rows in _tables(text):
            columns = _theme_columns(header, set(themes) - {ROOT})
            for line, row in rows:
                token_match = DOC_TOKEN_RE.search(row[0]) if columns and row else None
                if token_match is None:
                    continue
                token = token_match.group(1) or token_match.group(2)
                for position, theme in columns.items():
                    if position >= len(row):
                        continue
                    documented = _documented_value(row[position], themes, theme)
                    actual = resolve(themes, token, theme)
                    if documented and actual and documented != actual:
                        label = "default theme" if theme == ROOT else f"{theme} theme"
                        findings.append(
                            f"doc gives {token} in the {label} as {row[position]}, which is "
                            f"{documented}; the CSS resolves it to {actual} ({path}:{line})"
                        )
    return findings


def check_state_tables(doc_texts: dict[Path, str], rules: list[Rule]) -> list[str]:
    """Check each documented state against the CSS selectors and properties that draw it."""
    findings = []
    for path, text in doc_texts.items():
        for header, rows in _tables(text):
            if not header or header[0] != "state":
                continue
            for line, row in rows:
                state = row[0].strip("`* ").lower() if row else ""
                if not state or state == "default":
                    continue

                matching = [rule for rule in rules if state in rule.selector.lower()]
                if not matching:
                    findings.append(
                        f"doc documents state '{state}', which no CSS selector mentions "
                        f"({path}:{line})"
                    )
                    continue

                treatment = " ".join(row[1:]).lower()
                declared = {name for rule in matching for name, _ in rule.declarations}
                css_places = _where([(rule.path, rule.line) for rule in matching])
                for word, properties in TREATMENT_PROPERTIES.items():
                    documented = re.search(rf"\b{word}\b", treatment)
                    if documented and not any(name.startswith(properties) for name in declared):
                        article = "an" if word[0] in "aeiou" else "a"
                        findings.append(
                            f"doc gives state '{state}' {article} {word}, but no CSS rule for it "
                            f"declares {' or '.join(properties)} ({path}:{line}; CSS {css_places})"
                        )
    return findings


def check_heights(doc_texts: dict[Path, str], rules: list[Rule]) -> list[str]:
    """Flag a documented height that the CSS sets only as min-height or max-height."""
    heights: dict[str, set[str]] = {}
    for rule in rules:
        for name, value in rule.declarations:
            if name in {"height", "min-height", "max-height"}:
                heights.setdefault(value.lower(), set()).add(name)

    findings = []
    for path, text in doc_texts.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in DOC_HEIGHT_RE.finditer(line):
                value = f"{match.group(1) or match.group(2)}px"
                declared = heights.get(value, set())
                if declared and "height" not in declared and not BOUND_WORD_RE.search(line):
                    findings.append(
                        f"doc gives a height of {value}; the CSS sets only "
                        f"{' and '.join(sorted(declared))}: {value} ({path}:{line_number})"
                    )
    return findings


def check_preview_only(
    doc_texts: dict[Path, str], shipped: list[Rule], preview: list[Rule]
) -> list[str]:
    """Flag preview rules absent from shipped CSS, and doc lines that describe them."""
    shipped_keys = {
        (rule.media, rule.selector, name, value)
        for rule in shipped
        for name, value in rule.declarations
    }
    findings = []
    preview_px: dict[str, Rule] = {}
    for rule in preview:
        missing = [
            f"{name}: {value}"
            for name, value in rule.declarations
            if (rule.media, rule.selector, name, value) not in shipped_keys
        ]
        if not missing:
            continue
        scope = f"{rule.media} " if rule.media else ""
        findings.append(
            f"preview-only rule {scope}{rule.selector} {{ {'; '.join(missing)} }} is in no "
            f"shipped CSS ({rule.path}:{rule.line})"
        )
        for px in PX_RE.findall(rule.media):
            preview_px.setdefault(px, rule)

    shipped_media = " ".join(rule.media for rule in shipped)
    for path, text in doc_texts.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            for px, rule in preview_px.items():
                if re.search(rf"\b{px}\b", line) and px not in shipped_media:
                    findings.append(
                        f"doc describes a {px} layout that exists only in the preview "
                        f"({path}:{line_number}; preview {rule.path}:{rule.line})"
                    )
    return findings


def find_mismatches(docs: list[Path], css: list[Path], previews: Sequence[Path] = ()) -> list[str]:
    """Compare docs with shipped CSS (and previews); return one finding per mismatch."""
    doc_texts = {path: path.read_text() for path in docs}
    markdown = {path: text for path, text in doc_texts.items() if path.suffix == ".md"}
    css_texts = {path: _blank_comments(path.read_text()) for path in css}
    shipped = [rule for path, text in css_texts.items() for rule in parse_css(text, path)]
    preview = [rule for path in previews for rule in _preview_rules(path)]

    defined = _scan(css_texts, CSS_DEFINITION_RE)
    used = _scan(css_texts, CSS_USE_RE)
    css_hex = _scan(css_texts, HEX_RE, normalize_hex)
    doc_tokens = _scan(markdown, DOC_TOKEN_RE)
    doc_hex = _scan(doc_texts, DOC_HEX_RE, normalize_hex)

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

    findings += check_theme_tables(markdown, shipped)
    # Token-only CSS (a generated tokens.css) draws no components, so states can't be checked.
    if any(_theme_of(rule.selector) is None for rule in shipped):
        findings += check_state_tables(markdown, shipped)
    findings += check_heights(markdown, shipped)
    findings += check_preview_only(markdown, shipped, preview)
    return findings


def _doc_files(docs_dir: Path) -> list[Path]:
    """Return the Markdown and JSON files under a docs directory, sorted."""
    return sorted([*docs_dir.rglob("*.md"), *docs_dir.rglob("*.json")])


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, print every mismatch, and exit 1 if there are any."""
    parser = argparse.ArgumentParser(description="Cross-check design docs against CSS.")
    parser.add_argument("docs", type=Path, help="directory of Markdown design docs")
    parser.add_argument("--css", type=Path, action="append", required=True, help="shipped CSS")
    parser.add_argument(
        "--preview", type=Path, action="append", default=[], help="preview HTML or CSS"
    )
    args = parser.parse_args(argv)

    if not args.docs.is_dir():
        print(f"check_refs: not a directory: {args.docs}", file=sys.stderr)
        return 2
    missing = [path for path in [*args.css, *args.preview] if not path.is_file()]
    if missing:
        print(f"check_refs: no such file: {missing[0]}", file=sys.stderr)
        return 2

    findings = find_mismatches(_doc_files(args.docs), args.css, args.preview)
    for finding in findings:
        print(finding)
    if not findings:
        print("docs and CSS agree")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
