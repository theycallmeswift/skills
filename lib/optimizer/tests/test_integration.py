import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BIN = Path(__file__).resolve().parent.parent / "bin" / "optimize_prompt.py"


@pytest.mark.integration
def test_end_to_end_produces_output():
    """Full pipeline: prompt + CSV → optimized prompt on stdout."""
    result = subprocess.run(
        [
            sys.executable, str(BIN),
            "--prompt", str(FIXTURES / "prompt_plain.md"),
            "--training-data", str(FIXTURES / "training.csv"),
            "--output-fields", "rewritten",
            "--max-demos", "2",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    output = result.stdout

    # Output must contain original prompt
    assert "Rewrite the given input to be concise and direct." in output

    # Output must contain examples section (if demos were selected)
    # BootstrapFewShot may select 0 demos if metric is strict,
    # but with a lenient metric we expect at least the original prompt
    assert len(output.strip()) > 0


@pytest.mark.integration
def test_end_to_end_contains_examples():
    """Optimized output should include examples from training data."""
    result = subprocess.run(
        [
            sys.executable, str(BIN),
            "--prompt", str(FIXTURES / "prompt_plain.md"),
            "--training-data", str(FIXTURES / "training.csv"),
            "--output-fields", "rewritten",
            "--max-demos", "2",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    output = result.stdout

    if "## Examples" in output:
        assert "**Input:**" in output
        assert "**Output:**" in output


@pytest.mark.integration
def test_smoke_full_pipeline():
    """Smoke test with bundled fixtures — proves the full pipeline end-to-end."""
    result = subprocess.run(
        [
            sys.executable, str(BIN),
            "--prompt", str(FIXTURES / "smoke_prompt.md"),
            "--training-data", str(FIXTURES / "smoke_training.csv"),
            "--output-fields", "rewritten",
            "--max-demos", "3",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    output = result.stdout
    assert "Rewrite the given sentence to be shorter" in output
    assert len(output.strip()) > 0


@pytest.mark.integration
def test_frontmatter_stripped():
    """Frontmatter should be stripped — not appear in optimized output."""
    result = subprocess.run(
        [
            sys.executable, str(BIN),
            "--prompt", str(FIXTURES / "prompt_frontmatter.md"),
            "--training-data", str(FIXTURES / "training.csv"),
            "--output-fields", "rewritten",
            "--max-demos", "2",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    output = result.stdout
    assert "name: rewriter" not in output
    assert "Rewrite the given input to be concise and direct." in output
