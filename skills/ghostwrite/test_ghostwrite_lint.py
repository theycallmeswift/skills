"""Unit tests for skills/ghostwrite/lint.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "ghostwrite_lint_under_test", Path(__file__).parent / "lint.py"
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
lint = _mod.lint


def _rules(findings: list[str]) -> set[str]:
    return {f.split(":")[1].strip() for f in findings}


def test_clean_output_passes():
    text = "Hey, Sarah,\n\nSeason 3 wrapped with 450 fellows. Want to chat about renewing?\n\n- Swift\n"
    assert lint(text) == []


def test_em_dash_fails():
    text = "We shipped it — finally."
    findings = lint(text)
    assert "no_em_dash" in _rules(findings)


def test_banned_phrase_excited_to_share():
    text = "I am excited to share our new partnership!"
    findings = lint(text)
    assert "banned_phrases" in _rules(findings)


def test_banned_phrase_leverage():
    text = "We leverage partnerships to grow."
    findings = lint(text)
    assert "banned_phrases" in _rules(findings)


def test_ai_attribution_fails():
    text = "Shipped the feature.\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n"
    findings = lint(text)
    assert "no_ai_attribution" in _rules(findings)


def test_generated_with_claude_fails():
    text = "Here is the thing.\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n"
    findings = lint(text)
    assert "no_ai_attribution" in _rules(findings)


def test_cli_entry(tmp_path: Path):
    import subprocess

    good = tmp_path / "good.md"
    good.write_text("Hey, folks, we shipped Season 3. - Swift\n")
    r = subprocess.run(
        [sys.executable, "skills/ghostwrite/lint.py", str(good)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout

    bad = tmp_path / "bad.md"
    bad.write_text("We are excited to share — big news!\n")
    r = subprocess.run(
        [sys.executable, "skills/ghostwrite/lint.py", str(bad)],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 1
    assert "FAIL" in r.stdout
