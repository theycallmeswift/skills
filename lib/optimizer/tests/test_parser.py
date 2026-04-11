from pathlib import Path

import pytest

from src.parser import load_csv, parse_prompt, read_prompt

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_parse_prompt_no_frontmatter():
    content = read_prompt(FIXTURES / "prompt_plain.md")
    fm, body = parse_prompt(content)
    assert fm is None
    assert body == "Rewrite the given input to be concise and direct.\n"


def test_parse_prompt_with_frontmatter():
    content = read_prompt(FIXTURES / "prompt_frontmatter.md")
    fm, body = parse_prompt(content)
    assert fm == {"name": "rewriter", "description": "Rewrites content to be concise"}
    assert body == "Rewrite the given input to be concise and direct.\n"


def test_parse_prompt_malformed_yaml(tmp_path):
    p = tmp_path / "bad.md"
    p.write_text("---\n: [invalid\n---\n\nBody.\n")
    fm, body = parse_prompt(p.read_text())
    assert fm is None
    assert body == "---\n: [invalid\n---\n\nBody.\n"


def test_parse_prompt_no_closing_delimiter(tmp_path):
    p = tmp_path / "unclosed.md"
    p.write_text("---\nname: test\nNo closing delimiter here.\n")
    fm, body = parse_prompt(p.read_text())
    assert fm is None
    assert body.startswith("---")


def test_load_csv_basic():
    headers, rows = load_csv(FIXTURES / "training.csv")
    assert headers == ["source", "rewritten"]
    assert len(rows) == 3
    assert (
        rows[0]["source"]
        == "I wanted to let you know that the meeting has been moved to next Tuesday."
    )
    assert rows[0]["rewritten"] == "Meeting moved to next Tuesday."


def test_load_csv_multiline(tmp_path):
    p = tmp_path / "multi.csv"
    p.write_text('input,output\n"line1\nline2","result"\n')
    headers, rows = load_csv(p)
    assert rows[0]["input"] == "line1\nline2"


def test_load_csv_empty_file(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("")
    with pytest.raises(ValueError, match="no headers"):
        load_csv(p)


def test_load_csv_headers_only(tmp_path):
    p = tmp_path / "headers_only.csv"
    p.write_text("input,output\n")
    with pytest.raises(ValueError, match="no data"):
        load_csv(p)
