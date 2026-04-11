from pathlib import Path

from src.parser import parse_prompt


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_parse_prompt_no_frontmatter():
    fm, body = parse_prompt(FIXTURES / "prompt_plain.md")
    assert fm is None
    assert body == "Rewrite the given input to be concise and direct.\n"


def test_parse_prompt_with_frontmatter():
    fm, body = parse_prompt(FIXTURES / "prompt_frontmatter.md")
    assert fm == {"name": "rewriter", "description": "Rewrites content to be concise"}
    assert body == "Rewrite the given input to be concise and direct.\n"


def test_parse_prompt_malformed_yaml(tmp_path):
    p = tmp_path / "bad.md"
    p.write_text("---\n: [invalid\n---\n\nBody.\n")
    fm, body = parse_prompt(p)
    assert fm is None
    assert body == "---\n: [invalid\n---\n\nBody.\n"


def test_parse_prompt_no_closing_delimiter(tmp_path):
    p = tmp_path / "unclosed.md"
    p.write_text("---\nname: test\nNo closing delimiter here.\n")
    fm, body = parse_prompt(p)
    assert fm is None
    assert body.startswith("---")
