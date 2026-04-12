import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BIN = Path(__file__).resolve().parent.parent / "bin" / "optimize_prompt.py"


def run_optimizer(strategy="bootstrap_fewshot", prompt="prompt_plain.md", config=None):
    """Helper to run the optimizer CLI and return stdout/stderr."""
    cmd = [
        sys.executable,
        str(BIN),
        "--prompt",
        str(FIXTURES / prompt),
        "--training-data",
        str(FIXTURES / "training.csv"),
        "--output-fields",
        "rewritten",
        "--strategy",
        strategy,
    ]
    if config:
        cmd.extend(["--config", config])
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result


def split_output(stdout):
    """Split stdout into prompt and metadata sections."""
    parts = stdout.rsplit("\n---\n", 1)
    prompt = parts[0]
    metadata = parts[1] if len(parts) > 1 else ""
    return prompt, metadata


@pytest.mark.integration
class TestBootstrapFewShotIntegration:
    def test_end_to_end_produces_output(self):
        result = run_optimizer()
        assert result.returncode == 0, f"stderr: {result.stderr}"
        prompt, metadata = split_output(result.stdout)
        assert "Rewrite the given input to be concise and direct." in prompt
        assert len(prompt.strip()) > 0

    def test_contains_examples(self):
        result = run_optimizer()
        assert result.returncode == 0, f"stderr: {result.stderr}"
        prompt, metadata = split_output(result.stdout)
        assert "## Examples" in prompt
        assert "**Input:**" in prompt
        assert "**Output:**" in prompt

    def test_metadata_includes_strategy(self):
        result = run_optimizer()
        assert result.returncode == 0, f"stderr: {result.stderr}"
        _, metadata = split_output(result.stdout)
        assert "strategy: bootstrap_fewshot" in metadata
        assert "demos_selected:" in metadata

    def test_smoke_full_pipeline(self):
        result = run_optimizer(prompt="smoke_prompt.md")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        prompt, _ = split_output(result.stdout)
        assert "Rewrite the given sentence to be shorter" in prompt

    def test_frontmatter_stripped(self):
        result = run_optimizer(prompt="prompt_frontmatter.md")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        prompt, _ = split_output(result.stdout)
        assert "name: rewriter" not in prompt
        assert "Rewrite the given input to be concise and direct." in prompt

    def test_config_json_max_demos(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text('{"max_demos": 1}')
        result = run_optimizer(config=str(config_file))
        assert result.returncode == 0, f"stderr: {result.stderr}"
        _, metadata = split_output(result.stdout)
        assert "max_demos: 1" in metadata


@pytest.mark.integration
class TestGEPAIntegration:
    @pytest.fixture()
    def gepa_config(self, tmp_path):
        config_file = tmp_path / "gepa_config.json"
        config_file.write_text('{"max_metric_calls": 12, "num_threads": 1}')
        return str(config_file)

    def test_end_to_end_produces_rewritten_prompt(self, gepa_config):
        result = run_optimizer(strategy="gepa", config=gepa_config)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        prompt, metadata = split_output(result.stdout)
        # GEPA rewrites the prompt — it should be non-empty
        assert len(prompt.strip()) > 0
        # Should NOT have Examples section (GEPA is instruction-only)
        assert "## Examples" not in prompt

    def test_metadata_includes_gepa_strategy(self, gepa_config):
        result = run_optimizer(strategy="gepa", config=gepa_config)
        assert result.returncode == 0, f"stderr: {result.stderr}"
        _, metadata = split_output(result.stdout)
        assert "strategy: gepa" in metadata
