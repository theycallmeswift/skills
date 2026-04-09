from pathlib import Path

import pytest

from tests.support.harness.rubric import parse_rubric_file, parse_rubric_text


def test_parses_critical_and_optional_bullets():
    text = """# Ghostwrite Rubric

Intro paragraph grader sees as context.

## Critical

- Preserves every factual claim
- Reads in Swift's voice

## Optional

- Contractions used where natural
"""
    items = parse_rubric_text(text)
    assert items == [
        {"text": "Preserves every factual claim", "critical": True},
        {"text": "Reads in Swift's voice", "critical": True},
        {"text": "Contractions used where natural", "critical": False},
    ]


def test_ignores_content_outside_known_sections():
    text = """# Rubric

## Notes

- ignored bullet

## Critical

- kept bullet
"""
    items = parse_rubric_text(text)
    assert items == [{"text": "kept bullet", "critical": True}]


def test_missing_file_returns_empty_list(tmp_path):
    missing = tmp_path / "no.md"
    assert parse_rubric_file(missing) == []


def test_parses_real_file(tmp_path):
    p = tmp_path / "RUBRIC.md"
    p.write_text("## Critical\n\n- a\n- b\n")
    items = parse_rubric_file(p)
    assert [i["text"] for i in items] == ["a", "b"]


def test_rejects_malformed_critical_header():
    text = "## critical\n\n- bad"  # lowercase — we're strict
    items = parse_rubric_text(text)
    assert items == []  # header doesn't match, so no items captured
