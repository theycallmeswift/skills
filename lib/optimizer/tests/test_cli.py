import json
import tempfile

import pytest
from optimize_prompt import format_metadata, load_config, main, parse_args


class TestParseArgsExisting:
    def test_parse_args_required(self):
        args = parse_args(
            ["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "out"]
        )
        assert args.prompt == "p.md"
        assert args.training_data == "t.csv"
        assert args.output_fields == ["out"]

    def test_parse_args_defaults(self):
        args = parse_args(
            ["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "out"]
        )
        assert args.model == "anthropic/claude-haiku-4-5-20251001"
        assert args.strategy == "bootstrap_fewshot"

    def test_parse_args_custom_values(self):
        args = parse_args(
            [
                "--prompt",
                "p.md",
                "--training-data",
                "t.csv",
                "--output-fields",
                "out",
                "--model",
                "anthropic/claude-sonnet-4-6-20250514",
            ]
        )
        assert args.model == "anthropic/claude-sonnet-4-6-20250514"

    def test_parse_args_multi_output_fields(self):
        args = parse_args(
            ["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "a,b"]
        )
        assert args.output_fields == ["a", "b"]


class TestParseArgsConfig:
    def test_config_flag_defaults_to_none(self):
        args = parse_args(
            ["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "out"]
        )
        assert args.config is None

    def test_config_flag_accepts_path(self):
        args = parse_args(
            [
                "--prompt",
                "p.md",
                "--training-data",
                "t.csv",
                "--output-fields",
                "out",
                "--config",
                "config.json",
            ]
        )
        assert args.config == "config.json"

    def test_max_demos_flag_removed(self):
        """--max-demos is no longer a top-level flag."""
        with pytest.raises(SystemExit):
            parse_args(
                [
                    "--prompt",
                    "p.md",
                    "--training-data",
                    "t.csv",
                    "--output-fields",
                    "out",
                    "--max-demos",
                    "4",
                ]
            )


class TestLoadConfig:
    def test_returns_empty_dict_when_none(self):
        assert load_config(None) == {}

    def test_loads_json_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"max_demos": 6}, f)
            f.flush()
            result = load_config(f.name)
        assert result == {"max_demos": 6}

    def test_raises_on_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            f.flush()
            with pytest.raises(SystemExit):
                load_config(f.name)

    def test_raises_on_missing_file(self):
        with pytest.raises(SystemExit):
            load_config("/nonexistent/config.json")


class TestFormatMetadata:
    def test_formats_as_yaml_key_value(self):
        metadata = {"strategy": "gepa", "generations": 12}
        result = format_metadata(metadata)
        assert "strategy: gepa" in result
        assert "generations: 12" in result

    def test_separator_included(self):
        result = format_metadata({"key": "value"})
        assert result.startswith("\n---\n")


class TestMissingApiKey:
    def test_missing_api_key_exits_with_error(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(SystemExit, match="1"):
            main()
