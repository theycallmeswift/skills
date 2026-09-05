#!/usr/bin/env python3
"""
Structurally lint a candidate to-spec body and derive its dated-slug filename.

Checks the mechanically-checkable skim-first section rules — required sections
present (incl. References + Verification), a TL;DR opener, no empty section (which
also catches a present-but-empty Open Questions), and no leftover placeholder/TBD
text or template comments. Structure only: groundedness of a `file:line` claim is
semantic and stays a judge/eval concern, never a regex.

Usage:
    python3 validate_spec.py path/to/spec.md
Exit codes: 0 clean; 1 if any structural error (printed to stderr).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = (
    "Problem",
    "Solution",
    "User Stories",
    "Implementation Decisions",
    "Testing Plan",
    "Documentation Plan",
    "Out of Scope",
    "References",
    "Verification",
)
# Drop XXX (collides with real identifiers); these are unambiguous spec placeholders.
PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|PLACEHOLDER)\b|lorem ipsum", re.IGNORECASE)
H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
# A ```-fenced block: spec structure lives in prose, not inside code samples. The
# #37 format puts a flow diagram in a fence and the Solution leads with a fenced
# artifact; their contents must not be read as headings, placeholders, or comments.
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def _strip_code_fences(body: str) -> str:
    """Blank out ```-fenced blocks so structural scans see only prose."""
    return FENCE_RE.sub("", body)


def _sections(body: str) -> list[tuple[str, str]]:
    """Return [(heading_text, section_body), …] for each H2, body up to the next H2."""
    matches = list(H2_RE.finditer(body))
    out = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out.append((m.group(1).strip(), body[start:end].strip()))
    return out


def validate_spec(body: str) -> list[str]:
    """Return a list of structural errors (empty == valid)."""
    errors: list[str] = []
    # Scan prose only — a fenced diagram/artifact is content, not spec structure.
    scan = _strip_code_fences(body)
    sections = _sections(scan)
    headings_lower = [h.lower() for h, _ in sections]

    # TL;DR opener: present in the preamble before the first H2.
    first_h2 = H2_RE.search(scan)
    preamble = scan[: first_h2.start()] if first_h2 else scan
    if "tl;dr" not in preamble.lower():
        errors.append("Missing TL;DR opener before the first section.")

    # Required sections present (word-boundary prefix tolerates 'Problem Statement' etc.).
    for required in REQUIRED_SECTIONS:
        rl = required.lower()
        if not any(h == rl or h.startswith(rl + " ") for h in headings_lower):
            errors.append(f"Missing required section: ## {required}")

    # No empty section (covers a present-but-empty Open Questions too).
    for heading, sec_body in sections:
        if not sec_body:
            errors.append(f"Empty section: ## {heading}")

    # No leftover placeholder text or template comments.
    if PLACEHOLDER_RE.search(scan):
        errors.append("Leftover placeholder/TBD text (TODO/TBD/FIXME/PLACEHOLDER/lorem ipsum).")
    if "<!--" in scan:
        errors.append("Leftover template comment (<!-- … -->).")

    return errors


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return s or "untitled"


def spec_filename(date_str: str, title: str) -> str:
    return f"{date_str}-{slugify(title)}.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Structurally lint a to-spec body.")
    parser.add_argument("path", help="path to the candidate spec markdown file")
    args = parser.parse_args()

    body = Path(args.path).read_text(encoding="utf-8")
    errors = validate_spec(body)
    if errors:
        print(f"validate_spec: {len(errors)} structural error(s) in {args.path}:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"validate_spec: {args.path} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
