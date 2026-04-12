# Optimizer Strategy System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the optimizer's `--strategy` flag functional with a pluggable interface and add GEPA as the second optimization strategy.

**Architecture:** Strategy protocol + decorator registry in `src/strategy.py`. Each strategy lives in its own file under `src/optimizers/`. The CLI dispatches via registry lookup and passes strategy-specific config from an optional JSON file.

**Tech Stack:** Python 3.12, DSPy >=3.x, pytest, dataclasses

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `src/strategy.py` | `Strategy` protocol, `OptimizationResult` dataclass, registry dict, `register()` decorator, `get_strategy()` |
| Create | `src/optimizers/__init__.py` | Imports strategy modules to trigger registration |
| Create | `src/optimizers/bootstrap_fewshot.py` | BootstrapFewShot strategy (migrated from `src/optimizer.py`) |
| Create | `src/optimizers/gepa.py` | GEPA strategy implementation |
| Modify | `bin/optimize_prompt.py` | Registry dispatch, `--config` flag, metadata output |
| Delete | `src/optimizer.py` | Replaced by `src/optimizers/bootstrap_fewshot.py` |
| Modify | `src/extractor.py` | No changes (used by bootstrap_fewshot internally) |
| Create | `tests/test_strategy.py` | Unit tests for protocol, registry, result |
| Create | `tests/test_bootstrap_fewshot.py` | Unit tests for migrated strategy |
| Create | `tests/test_gepa.py` | Unit tests for GEPA strategy |
| Modify | `tests/test_cli.py` | Add tests for `--config`, metadata output, strategy dispatch |
| Modify | `tests/test_integration.py` | Add GEPA integration test |
| Modify | `pyproject.toml` | Bump dspy to >=3.0 |

---

### Task 1: Strategy Protocol & Registry

**Files:**
- Create: `src/strategy.py`
- Create: `tests/test_strategy.py`

- [ ] **Step 1: Write failing tests for strategy registry**

Create `tests/test_strategy.py`:

```python
from textwrap import dedent

import pytest

from src.strategy import OptimizationResult, Strategy, get_strategy, register, STRATEGIES


class TestOptimizationResult:
    def test_stores_prompt_and_metadata(self):
        result = OptimizationResult(prompt="optimized", metadata={"score": 0.9})
        assert result.prompt == "optimized"
        assert result.metadata == {"score": 0.9}

    def test_metadata_defaults_to_empty_dict(self):
        result = OptimizationResult(prompt="optimized")
        assert result.metadata == {}


class TestRegistry:
    def setup_method(self):
        self._original = STRATEGIES.copy()

    def teardown_method(self):
        STRATEGIES.clear()
        STRATEGIES.update(self._original)

    def test_register_adds_to_registry(self):
        @register("test_strategy")
        class TestStrategy:
            name = "test_strategy"

            def optimize(self, signature_cls, examples, config):
                pass

        assert "test_strategy" in STRATEGIES
        assert STRATEGIES["test_strategy"] is TestStrategy

    def test_get_strategy_returns_registered_class(self):
        @register("test_strategy")
        class TestStrategy:
            name = "test_strategy"

            def optimize(self, signature_cls, examples, config):
                pass

        assert get_strategy("test_strategy") is TestStrategy

    def test_get_strategy_raises_on_unknown(self):
        with pytest.raises(ValueError, match="Unknown strategy: nope"):
            get_strategy("nope")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd lib/optimizer && python -m pytest tests/test_strategy.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.strategy'`

- [ ] **Step 3: Implement strategy.py**

Create `src/strategy.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class OptimizationResult:
    """Result returned by any optimization strategy."""

    prompt: str
    metadata: dict = field(default_factory=dict)


class Strategy(Protocol):
    """Protocol that all optimization strategies must implement."""

    name: str

    def optimize(self, signature_cls, examples: list, config: dict) -> OptimizationResult: ...


STRATEGIES: dict[str, type[Strategy]] = {}


def register(name: str):
    """Decorator to register a strategy class in the global registry."""

    def decorator(cls):
        STRATEGIES[name] = cls
        return cls

    return decorator


def get_strategy(name: str) -> type[Strategy]:
    """Look up a strategy by name. Raises ValueError if not found."""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd lib/optimizer && python -m pytest tests/test_strategy.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd lib/optimizer && git add src/strategy.py tests/test_strategy.py
git commit -m "Add Strategy protocol and registry"
```

---

### Task 2: BootstrapFewShot Strategy Migration

**Files:**
- Create: `src/optimizers/__init__.py`
- Create: `src/optimizers/bootstrap_fewshot.py`
- Create: `tests/test_bootstrap_fewshot.py`
- Delete: `src/optimizer.py`

- [ ] **Step 1: Write failing tests for BootstrapFewShot strategy**

Create `tests/test_bootstrap_fewshot.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from src.strategy import OptimizationResult, get_strategy, STRATEGIES


class TestBootstrapFewShotRegistration:
    def test_registered_as_bootstrap_fewshot(self):
        # Import triggers registration
        import src.optimizers.bootstrap_fewshot  # noqa: F401

        assert "bootstrap_fewshot" in STRATEGIES

    def test_get_strategy_returns_class(self):
        import src.optimizers.bootstrap_fewshot  # noqa: F401

        cls = get_strategy("bootstrap_fewshot")
        assert cls.name == "bootstrap_fewshot"


class TestBootstrapFewShotOptimize:
    def test_returns_optimization_result(self):
        import src.optimizers.bootstrap_fewshot  # noqa: F401

        cls = get_strategy("bootstrap_fewshot")
        strategy = cls()

        # Mock the DSPy calls
        mock_compiled = MagicMock()
        mock_compiled.demos = [{"source": "long text", "rewritten": "short"}]

        with patch("src.optimizers.bootstrap_fewshot.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.BootstrapFewShot.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}

            result = strategy.optimize(
                signature_cls=mock_sig,
                examples=[],
                config={"max_demos": 2},
            )

        assert isinstance(result, OptimizationResult)
        assert "## Examples" in result.prompt or len(result.prompt) > 0
        assert "strategy" in result.metadata
        assert result.metadata["strategy"] == "bootstrap_fewshot"

    def test_default_max_demos_is_4(self):
        import src.optimizers.bootstrap_fewshot  # noqa: F401

        cls = get_strategy("bootstrap_fewshot")
        strategy = cls()

        mock_compiled = MagicMock()
        mock_compiled.demos = []

        with patch("src.optimizers.bootstrap_fewshot.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.BootstrapFewShot.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}
            mock_sig.__doc__ = "Original prompt"

            strategy.optimize(signature_cls=mock_sig, examples=[], config={})

            mock_dspy.BootstrapFewShot.assert_called_once_with(
                metric=mock_dspy.BootstrapFewShot.call_args[1]["metric"],
                max_bootstrapped_demos=4,
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd lib/optimizer && python -m pytest tests/test_bootstrap_fewshot.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.optimizers'`

- [ ] **Step 3: Create optimizers package and migrate bootstrap_fewshot**

Create `src/optimizers/__init__.py`:

```python
from . import bootstrap_fewshot  # noqa: F401
```

Create `src/optimizers/bootstrap_fewshot.py`:

```python
import dspy

from src.extractor import extract_demos, format_optimized_prompt
from src.strategy import OptimizationResult, register


@register("bootstrap_fewshot")
class BootstrapFewShotStrategy:
    """Selects optimal few-shot examples from training data."""

    name = "bootstrap_fewshot"

    def optimize(self, signature_cls, examples: list, config: dict) -> OptimizationResult:
        max_demos = config.get("max_demos", 4)

        predictor = dspy.Predict(signature_cls)
        output_keys = list(signature_cls.output_fields.keys())
        input_keys = list(signature_cls.input_fields.keys())

        def metric(example, prediction, trace=None):
            return all(bool(getattr(prediction, k, None)) for k in output_keys)

        optimizer = dspy.BootstrapFewShot(
            metric=metric,
            max_bootstrapped_demos=max_demos,
        )
        compiled = optimizer.compile(predictor, trainset=examples)

        demos = extract_demos(compiled)
        original_prompt = signature_cls.__doc__ or ""
        prompt = format_optimized_prompt(original_prompt, demos, input_keys, output_keys)

        return OptimizationResult(
            prompt=prompt,
            metadata={
                "strategy": "bootstrap_fewshot",
                "demos_selected": len(demos),
                "max_demos": max_demos,
            },
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd lib/optimizer && python -m pytest tests/test_bootstrap_fewshot.py -v`
Expected: All tests PASS

- [ ] **Step 5: Delete old optimizer.py**

```bash
cd lib/optimizer && git rm src/optimizer.py
```

- [ ] **Step 6: Commit**

```bash
cd lib/optimizer && git add src/optimizers/ tests/test_bootstrap_fewshot.py
git commit -m "Migrate BootstrapFewShot to strategy interface"
```

---

### Task 3: CLI Update — Registry Dispatch, Config, Metadata

**Files:**
- Modify: `bin/optimize_prompt.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for new CLI features**

Add to `tests/test_cli.py`:

```python
import json
import tempfile
from textwrap import dedent
from unittest.mock import patch

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd lib/optimizer && python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ImportError: cannot import name 'format_metadata' from 'optimize_prompt'`

- [ ] **Step 3: Rewrite bin/optimize_prompt.py**

Replace `bin/optimize_prompt.py` with:

```python
#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dspy

import src.optimizers  # noqa: F401 — triggers strategy registration
from src.bridge import build_signature, rows_to_examples
from src.parser import load_csv, parse_prompt, read_prompt
from src.strategy import get_strategy


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Optimize a prompt using DSPy strategies")
    parser.add_argument("--prompt", required=True, help="Path to prompt file, or - for stdin")
    parser.add_argument("--training-data", required=True, help="Path to CSV file")
    parser.add_argument(
        "--output-fields", required=True, help="Comma-separated output column names"
    )
    parser.add_argument(
        "--model",
        default="anthropic/claude-haiku-4-5-20251001",
        help="Model identifier for DSPy (default: anthropic/claude-haiku-4-5-20251001)",
    )
    parser.add_argument(
        "--strategy",
        default="bootstrap_fewshot",
        help="Optimization strategy (default: bootstrap_fewshot)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to JSON file with strategy-specific configuration",
    )

    args = parser.parse_args(argv)
    args.output_fields = [f.strip() for f in args.output_fields.split(",")]
    return args


def load_config(config_path):
    """Load strategy config from JSON file. Returns empty dict if path is None."""
    if config_path is None:
        return {}
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)


def format_metadata(metadata):
    """Format metadata dict as YAML-style key: value lines with separator."""
    lines = [f"{k}: {v}" for k, v in metadata.items()]
    return "\n---\n" + "\n".join(lines)


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set. Export it before running.", file=sys.stderr)
        sys.exit(1)

    args = parse_args()
    config = load_config(args.config)

    lm = dspy.LM(args.model)
    dspy.configure(lm=lm)

    content = read_prompt(args.prompt)
    _, prompt = parse_prompt(content)
    headers, rows = load_csv(args.training_data)
    input_fields = [h for h in headers if h not in args.output_fields]

    signature = build_signature(prompt, input_fields, args.output_fields)
    examples = rows_to_examples(rows, input_fields)

    strategy_cls = get_strategy(args.strategy)
    strategy = strategy_cls()
    result = strategy.optimize(signature_cls=signature, examples=examples, config=config)

    print(result.prompt)
    print(format_metadata(result.metadata))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd lib/optimizer && python -m pytest tests/test_cli.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd lib/optimizer && git add bin/optimize_prompt.py tests/test_cli.py
git commit -m "CLI: registry dispatch, --config flag, metadata output"
```

---

### Task 4: GEPA Strategy

**Files:**
- Create: `src/optimizers/gepa.py`
- Modify: `src/optimizers/__init__.py`
- Create: `tests/test_gepa.py`

- [ ] **Step 1: Write failing tests for GEPA strategy**

Create `tests/test_gepa.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from src.strategy import OptimizationResult, get_strategy, STRATEGIES


class TestGEPARegistration:
    def test_registered_as_gepa(self):
        import src.optimizers.gepa  # noqa: F401

        assert "gepa" in STRATEGIES

    def test_get_strategy_returns_class(self):
        import src.optimizers.gepa  # noqa: F401

        cls = get_strategy("gepa")
        assert cls.name == "gepa"


class TestGEPAOptimize:
    def test_returns_optimization_result(self):
        import src.optimizers.gepa  # noqa: F401

        cls = get_strategy("gepa")
        strategy = cls()

        mock_compiled = MagicMock()
        # GEPA rewrites instructions — access via the compiled module's signature
        mock_predict = MagicMock()
        mock_predict.signature.__doc__ = "Rewritten optimized prompt"
        mock_compiled.predictors.return_value = [mock_predict]

        with patch("src.optimizers.gepa.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.GEPA.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}
            mock_sig.__doc__ = "Original prompt"

            result = strategy.optimize(
                signature_cls=mock_sig,
                examples=[],
                config={"auto": "light"},
            )

        assert isinstance(result, OptimizationResult)
        assert result.metadata["strategy"] == "gepa"

    def test_default_config_uses_light_auto(self):
        import src.optimizers.gepa  # noqa: F401

        cls = get_strategy("gepa")
        strategy = cls()

        mock_compiled = MagicMock()
        mock_predict = MagicMock()
        mock_predict.signature.__doc__ = "Rewritten prompt"
        mock_compiled.predictors.return_value = [mock_predict]

        with patch("src.optimizers.gepa.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.GEPA.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}
            mock_sig.__doc__ = "Original prompt"

            strategy.optimize(signature_cls=mock_sig, examples=[], config={})

            # Verify GEPA was called with auto="light" default
            call_kwargs = mock_dspy.GEPA.call_args[1]
            assert call_kwargs.get("auto") == "light"

    def test_config_passes_through_gepa_params(self):
        import src.optimizers.gepa  # noqa: F401

        cls = get_strategy("gepa")
        strategy = cls()

        mock_compiled = MagicMock()
        mock_predict = MagicMock()
        mock_predict.signature.__doc__ = "Rewritten prompt"
        mock_compiled.predictors.return_value = [mock_predict]

        with patch("src.optimizers.gepa.dspy") as mock_dspy:
            mock_optimizer = MagicMock()
            mock_optimizer.compile.return_value = mock_compiled
            mock_dspy.GEPA.return_value = mock_optimizer
            mock_dspy.Predict.return_value = MagicMock()

            mock_sig = MagicMock()
            mock_sig.output_fields = {"rewritten": None}
            mock_sig.input_fields = {"source": None}
            mock_sig.__doc__ = "Original prompt"

            strategy.optimize(
                signature_cls=mock_sig,
                examples=[],
                config={
                    "auto": "medium",
                    "reflection_minibatch_size": 5,
                    "use_merge": False,
                },
            )

            call_kwargs = mock_dspy.GEPA.call_args[1]
            assert call_kwargs["auto"] == "medium"
            assert call_kwargs["reflection_minibatch_size"] == 5
            assert call_kwargs["use_merge"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd lib/optimizer && python -m pytest tests/test_gepa.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.optimizers.gepa'`

- [ ] **Step 3: Implement GEPA strategy**

Create `src/optimizers/gepa.py`:

```python
import dspy

from src.strategy import OptimizationResult, register

# Supported config keys for GEPA
GEPA_CONFIG_KEYS = {
    "auto",
    "reflection_minibatch_size",
    "use_merge",
    "max_merge_invocations",
}


@register("gepa")
class GEPAStrategy:
    """Instruction-only optimizer using reflective mutation and genetic evolution."""

    name = "gepa"

    def optimize(self, signature_cls, examples: list, config: dict) -> OptimizationResult:
        predictor = dspy.Predict(signature_cls)
        output_keys = list(signature_cls.output_fields.keys())

        def metric(example, prediction, trace=None):
            score = all(bool(getattr(prediction, k, None)) for k in output_keys)
            if not score:
                return 0.0, "Output fields are empty or missing."
            return 1.0, "All output fields present and non-empty."

        # Build GEPA kwargs from config, defaulting auto to "light"
        gepa_kwargs = {"auto": config.get("auto", "light"), "metric": metric}
        for key in GEPA_CONFIG_KEYS - {"auto"}:
            if key in config:
                gepa_kwargs[key] = config[key]

        optimizer = dspy.GEPA(**gepa_kwargs)
        compiled = optimizer.compile(predictor, trainset=examples)

        # Extract rewritten prompt from compiled module's first predictor
        predictors = compiled.predictors()
        rewritten_prompt = predictors[0].signature.__doc__ if predictors else ""

        return OptimizationResult(
            prompt=rewritten_prompt,
            metadata={
                "strategy": "gepa",
                "auto": gepa_kwargs["auto"],
            },
        )
```

- [ ] **Step 4: Update optimizers/__init__.py to include gepa**

Update `src/optimizers/__init__.py`:

```python
from . import bootstrap_fewshot, gepa  # noqa: F401
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd lib/optimizer && python -m pytest tests/test_gepa.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
cd lib/optimizer && git add src/optimizers/gepa.py src/optimizers/__init__.py tests/test_gepa.py
git commit -m "Add GEPA optimization strategy"
```

---

### Task 5: Integration Tests

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Update existing integration tests for metadata output**

The existing integration tests check stdout. Now stdout includes metadata after `---`. Update assertions to account for this.

Replace `tests/test_integration.py`:

```python
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BIN = Path(__file__).resolve().parent.parent / "bin" / "optimize_prompt.py"


def run_optimizer(strategy="bootstrap_fewshot", prompt="prompt_plain.md", max_demos=2, config=None):
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
    def test_end_to_end_produces_rewritten_prompt(self):
        result = run_optimizer(strategy="gepa")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        prompt, metadata = split_output(result.stdout)
        # GEPA rewrites the prompt — it should be non-empty
        assert len(prompt.strip()) > 0
        # Should NOT have Examples section (GEPA is instruction-only)
        assert "## Examples" not in prompt

    def test_metadata_includes_gepa_strategy(self):
        result = run_optimizer(strategy="gepa")
        assert result.returncode == 0, f"stderr: {result.stderr}"
        _, metadata = split_output(result.stdout)
        assert "strategy: gepa" in metadata
        assert "auto:" in metadata
```

- [ ] **Step 2: Run bootstrap_fewshot integration tests to verify they pass**

Run: `cd lib/optimizer && python -m pytest tests/test_integration.py::TestBootstrapFewShotIntegration -v -m integration`
Expected: All PASS (requires ANTHROPIC_API_KEY)

- [ ] **Step 3: Run GEPA integration tests**

Run: `cd lib/optimizer && python -m pytest tests/test_integration.py::TestGEPAIntegration -v -m integration`
Expected: All PASS (requires ANTHROPIC_API_KEY and dspy>=3.x)

- [ ] **Step 4: Commit**

```bash
cd lib/optimizer && git add tests/test_integration.py
git commit -m "Integration tests for strategy system and GEPA"
```

---

### Task 6: Dependency Bump & Cleanup

**Files:**
- Modify: `pyproject.toml`
- Delete: `src/optimizer.py` (if not already deleted in Task 2)

- [ ] **Step 1: Bump dspy version in pyproject.toml**

Update `pyproject.toml` dependencies:

```toml
[project]
name = "prompt-optimizer"
version = "0.2.0"
description = "DSPy-based prompt optimizer with pluggable strategies"
requires-python = ">=3.11"
dependencies = [
    "dspy>=3.0",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.15.9",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: requires API key and makes LLM calls"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]
```

- [ ] **Step 2: Verify src/optimizer.py is deleted**

Run: `ls lib/optimizer/src/optimizer.py`
Expected: `No such file or directory`

- [ ] **Step 3: Run full unit test suite**

Run: `cd lib/optimizer && python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All unit tests PASS

- [ ] **Step 4: Commit**

```bash
cd lib/optimizer && git add pyproject.toml
git commit -m "Bump dspy to >=3.0, version to 0.2.0"
```

---

### Task 7: Full Smoke Test

**Files:** None (verification only)

- [ ] **Step 1: Run full unit test suite**

Run: `cd lib/optimizer && python -m pytest tests/ -v --ignore=tests/test_integration.py`
Expected: All PASS

- [ ] **Step 2: Run integration tests (requires API key)**

Run: `cd lib/optimizer && python -m pytest tests/test_integration.py -v -m integration`
Expected: All PASS

- [ ] **Step 3: Manual CLI smoke test — bootstrap_fewshot**

Run:
```bash
cd lib/optimizer && python bin/optimize_prompt.py \
  --prompt tests/fixtures/smoke_prompt.md \
  --training-data tests/fixtures/smoke_training.csv \
  --output-fields rewritten \
  --strategy bootstrap_fewshot
```
Expected: Optimized prompt with `## Examples` section followed by `---` and metadata

- [ ] **Step 4: Manual CLI smoke test — gepa**

Run:
```bash
cd lib/optimizer && python bin/optimize_prompt.py \
  --prompt tests/fixtures/smoke_prompt.md \
  --training-data tests/fixtures/smoke_training.csv \
  --output-fields rewritten \
  --strategy gepa
```
Expected: Rewritten prompt (no Examples section) followed by `---` and metadata

- [ ] **Step 5: Final commit if any fixups needed**

```bash
git add -A && git commit -m "Fixups from smoke testing"
```
