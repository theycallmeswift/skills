"""Unit tests for validate_spec.py.

Covers: a structurally-valid #37-shape body passes; each structural rule
(required sections incl. References + Verification, no empty section, TL;DR
opener, no placeholder/TBD/template-comment text, no present-but-empty Open
Questions) flags when violated; slug + filename derivation.
"""

from __future__ import annotations

import validate_spec as vs

VALID = """\
**TL;DR** — Add a widget cache so repeated reads skip the DB.

## Problem
- **Symptom:** every read hits the DB.

## Solution
```py
cache = LRU(256)
```
A small LRU in front of the read path.

## User Stories
1. As a user, I want **fast reads**, so the page loads quickly.

## Implementation Decisions
- **Cache reads only.** Writes bypass and invalidate.

## Testing Plan
### Logic
- **Eviction is LRU** under capacity pressure.

## Documentation Plan
- **README**: document the cache knob.

## Out of Scope
- Distributed caching.

## References
- #12 — the slow-read report.

## Verification
- `make test`
"""


def test_valid_body_has_no_errors():
    assert vs.validate_spec(VALID) == []


def test_missing_required_section_flagged():
    body = VALID.replace("## References\n- #12 — the slow-read report.\n", "")
    errors = vs.validate_spec(body)
    assert any("References" in e for e in errors)


def test_missing_tldr_flagged():
    body = VALID.replace("**TL;DR** — Add a widget cache so repeated reads skip the DB.\n", "")
    assert any("TL;DR" in e for e in vs.validate_spec(body))


def test_empty_section_flagged():
    body = VALID.replace("- Distributed caching.\n", "")
    assert any("Out of Scope" in e for e in vs.validate_spec(body))


def test_placeholder_text_flagged():
    body = VALID.replace("- Distributed caching.", "- TODO: figure this out")
    assert any("placeholder" in e.lower() or "TODO" in e for e in vs.validate_spec(body))


def test_template_comment_flagged():
    body = VALID.replace(
        "- Distributed caching.", "<!-- describe negative scope -->\n- Distributed caching."
    )
    assert any("comment" in e.lower() for e in vs.validate_spec(body))


def test_present_but_empty_open_questions_flagged():
    body = VALID.replace("## References", "## Open Questions\n\n## References")
    assert any("Open Questions" in e for e in vs.validate_spec(body))


def test_present_nonempty_open_questions_ok():
    body = VALID.replace(
        "## References",
        "## Open Questions\n- Which eviction size?\n\n## References",
    )
    assert vs.validate_spec(body) == []


# ---------------------------------------------------------------------------
# fenced code blocks are content, not structure (the #37 flow diagram lives in one)


def _with_diagram(diagram_body: str) -> str:
    """VALID with a fenced block (e.g. a flow diagram) inserted into Implementation Decisions."""
    fence = f"\n```\n{diagram_body}\n```\n"
    return VALID.replace(
        "- **Cache reads only.** Writes bypass and invalidate.",
        fence + "\n- **Cache reads only.** Writes bypass and invalidate.",
    )


def test_fenced_heading_not_parsed_as_section():
    # A `## ...` line inside a fence must not become a spurious (empty) section.
    assert vs.validate_spec(_with_diagram("## not a real heading\nstep ──► step")) == []


def test_fenced_placeholder_word_not_flagged():
    assert vs.validate_spec(_with_diagram("# pseudo-code\nif TODO: pass")) == []


def test_fenced_comment_marker_not_flagged():
    assert vs.validate_spec(_with_diagram("<!-- sample html the spec describes -->")) == []


def test_slugify():
    assert vs.slugify("Add a Widget Cache!") == "add-a-widget-cache"
    assert vs.slugify("  Multi   space / slash ") == "multi-space-slash"


def test_slugify_empty_falls_back():
    assert vs.slugify("!!!") == "untitled"


def test_spec_filename():
    assert (
        vs.spec_filename("2026-06-15", "Add a Widget Cache") == "2026-06-15-add-a-widget-cache.md"
    )
