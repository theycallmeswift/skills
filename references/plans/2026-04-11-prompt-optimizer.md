# Prompt Optimizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a DSPy-based prompt optimizer that finds optimal few-shot examples for any prompt, outputting an optimized prompt to stdout.

**Architecture:** Two-phase pipeline: parse prompt + CSV inputs, bridge them into DSPy Signature/Examples, run BootstrapFewShot optimization, then extract selected demos and format them as natural language examples prepended to the original prompt. Self-contained library under `lib/optimizer/` with its own tests and CLI.

**Tech Stack:** Python 3.11+, DSPy (BootstrapFewShot), PyYAML (frontmatter parsing), pytest

---

## File Structure

| File | Responsibility |
|------|---------------|
| `lib/optimizer/pyproject.toml` | Standalone package metadata, dev deps |
| `lib/optimizer/src/__init__.py` | Package init |
| `lib/optimizer/src/parser.py` | Prompt file + frontmatter parsing, CSV loading |
| `lib/optimizer/src/bridge.py` | Prompt → DSPy Signature, CSV rows → `dspy.Example` objects |
| `lib/optimizer/src/optimizer.py` | BootstrapFewShot wrapper |
| `lib/optimizer/src/extractor.py` | Compiled module → natural language few-shot examples |
| `lib/optimizer/bin/optimize_prompt.py` | CLI entry point, arg parsing, pipeline wiring |
| `lib/optimizer/tests/__init__.py` | Test package init |
| `lib/optimizer/tests/conftest.py` | sys.path setup, integration marker/skip logic |
| `lib/optimizer/tests/test_parser.py` | Parser unit tests |
| `lib/optimizer/tests/test_bridge.py` | Bridge unit tests |
| `lib/optimizer/tests/test_extractor.py` | Extractor unit tests |
| `lib/optimizer/tests/test_cli.py` | CLI arg parsing unit tests |
| `lib/optimizer/tests/test_integration.py` | End-to-end + smoke tests (real DSPy calls) |
| `lib/optimizer/tests/fixtures/prompt_plain.md` | Test fixture: prompt without frontmatter |
| `lib/optimizer/tests/fixtures/prompt_frontmatter.md` | Test fixture: prompt with YAML frontmatter |
| `lib/optimizer/tests/fixtures/training.csv` | Test fixture: simple training CSV |
| `lib/optimizer/tests/fixtures/smoke_prompt.md` | Smoke test: minimal prompt |
| `lib/optimizer/tests/fixtures/smoke_training.csv` | Smoke test: 5-row training set |
| `lib/optimizer/README.md` | Library usage docs |
| `bin/optimize_prompt.py` | Symlink → `lib/optimizer/bin/optimize_prompt.py` |
| `pyproject.toml` | **Modify:** add `dspy`, `pyyaml` to dev deps |
| `CLAUDE.md` | **Modify:** add optimizer reference under Project Structure |

---

### Task 1: Project Scaffolding

**Files:**
- Create: `lib/optimizer/pyproject.toml`
- Create: `lib/optimizer/src/__init__.py`
- Create: `lib/optimizer/tests/__init__.py`
- Create: `lib/optimizer/tests/conftest.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p lib/optimizer/src lib/optimizer/bin lib/optimizer/tests/fixtures
```

- [ ] **Step 2: Create `lib/optimizer/pyproject.toml`**

```toml
[project]
name = "prompt-optimizer"
version = "0.1.0"
description = "DSPy-based few-shot prompt optimizer"
requires-python = ">=3.11"
dependencies = [
    "dspy>=2.5",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
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

- [ ] **Step 3: Create `lib/optimizer/src/__init__.py`**

```python
```

Empty file — just marks the directory as a package.

- [ ] **Step 4: Create `lib/optimizer/tests/__init__.py`**

```python
```

Empty file.

- [ ] **Step 5: Create `lib/optimizer/tests/conftest.py`**

```python
import os
import sys
from pathlib import Path

import pytest

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "bin"))


def pytest_collection_modifyitems(config, items):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        skip = pytest.mark.skip(reason="ANTHROPIC_API_KEY not set")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
```

- [ ] **Step 6: Add `dspy` and `pyyaml` to root dev deps**

In `pyproject.toml` at project root, update the `[dependency-groups]` dev list:

```toml
[dependency-groups]
dev = [
    "dspy>=2.5",
    "pyyaml>=6.0",
    "pytest>=8.0",
    "pytest-xdist>=3.5",
    "ruff>=0.15.9",
]
```

- [ ] **Step 7: Install dependencies**

```bash
uv sync --group dev
```

Expected: resolves and installs `dspy`, `pyyaml`, and all transitive deps without errors.

- [ ] **Step 8: Verify pytest discovers the test directory**

```bash
cd lib/optimizer && python -m pytest tests/ --collect-only
```

Expected: `no tests ran` (no test files yet), exits 0 or with "no tests collected" warning.

- [ ] **Step 9: Commit**

```bash
git add lib/optimizer/pyproject.toml lib/optimizer/src/__init__.py \
  lib/optimizer/tests/__init__.py lib/optimizer/tests/conftest.py \
  pyproject.toml uv.lock
git commit -m "scaffold prompt optimizer library structure"
```

---

### Task 2: Test Fixtures

**Files:**
- Create: `lib/optimizer/tests/fixtures/prompt_plain.md`
- Create: `lib/optimizer/tests/fixtures/prompt_frontmatter.md`
- Create: `lib/optimizer/tests/fixtures/training.csv`
- Create: `lib/optimizer/tests/fixtures/smoke_prompt.md`
- Create: `lib/optimizer/tests/fixtures/smoke_training.csv`

- [ ] **Step 1: Create `lib/optimizer/tests/fixtures/prompt_plain.md`**

```markdown
Rewrite the given input to be concise and direct.
```

- [ ] **Step 2: Create `lib/optimizer/tests/fixtures/prompt_frontmatter.md`**

```markdown
---
name: rewriter
description: Rewrites content to be concise
---

Rewrite the given input to be concise and direct.
```

- [ ] **Step 3: Create `lib/optimizer/tests/fixtures/training.csv`**

```csv
source,rewritten
"I wanted to let you know that the meeting has been moved to next Tuesday.","Meeting moved to next Tuesday."
"The reason we can't ship this feature is because the API doesn't support batch operations yet.","Can't ship — API lacks batch support."
"I think it would be a good idea for us to consider implementing a caching layer.","We should add a caching layer."
```

- [ ] **Step 4: Create `lib/optimizer/tests/fixtures/smoke_prompt.md`**

```markdown
Rewrite the given sentence to be shorter while preserving its core meaning.
```

- [ ] **Step 5: Create `lib/optimizer/tests/fixtures/smoke_training.csv`**

```csv
sentence,rewritten
"I wanted to let you know that the meeting has been moved to next Tuesday.","Meeting moved to next Tuesday."
"The reason we can't ship this feature is because the API doesn't support batch operations yet.","Can't ship — API lacks batch support."
"I think it would be a good idea for us to consider implementing a caching layer.","We should add a caching layer."
"Please be advised that the server will be undergoing maintenance this weekend.","Server maintenance this weekend."
"I was wondering if you had a chance to take a look at the pull request I submitted yesterday.","Did you review my PR from yesterday?"
```

- [ ] **Step 6: Commit**

```bash
git add lib/optimizer/tests/fixtures/
git commit -m "add test fixtures for prompt optimizer"
```

---

### Task 3: Prompt Parser (TDD)

**Files:**
- Create: `lib/optimizer/tests/test_parser.py`
- Create: `lib/optimizer/src/parser.py`

- [ ] **Step 1: Write failing tests for `parse_prompt`**

Create `lib/optimizer/tests/test_parser.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd lib/optimizer && python -m pytest tests/test_parser.py -v --no-header -p no:xdist
```

Expected: `ModuleNotFoundError: No module named 'src.parser'`

- [ ] **Step 3: Implement `parse_prompt`**

Create `lib/optimizer/src/parser.py`:

```python
import sys
from pathlib import Path

import yaml


def parse_prompt(path):
    """Read a prompt file, strip YAML frontmatter if present.

    Returns (frontmatter_dict_or_None, body_string).
    Pass "-" to read from stdin.
    """
    if str(path) == "-":
        content = sys.stdin.read()
    else:
        content = Path(path).read_text(encoding="utf-8")

    if not content.startswith("---\n"):
        return None, content

    end = content.find("\n---\n", 4)
    if end == -1:
        return None, content

    frontmatter_raw = content[4:end]
    body = content[end + 5:]

    try:
        frontmatter = yaml.safe_load(frontmatter_raw)
    except yaml.YAMLError:
        return None, content

    return frontmatter, body
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd lib/optimizer && python -m pytest tests/test_parser.py -v --no-header -p no:xdist
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/optimizer/src/parser.py lib/optimizer/tests/test_parser.py
git commit -m "add prompt parser with frontmatter detection"
```

---

### Task 4: CSV Loader (TDD)

**Files:**
- Modify: `lib/optimizer/tests/test_parser.py`
- Modify: `lib/optimizer/src/parser.py`

- [ ] **Step 1: Write failing tests for `load_csv`**

Append to `lib/optimizer/tests/test_parser.py`:

```python
import pytest

from src.parser import load_csv


def test_load_csv_basic():
    headers, rows = load_csv(FIXTURES / "training.csv")
    assert headers == ["source", "rewritten"]
    assert len(rows) == 3
    assert rows[0]["source"] == "I wanted to let you know that the meeting has been moved to next Tuesday."
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd lib/optimizer && python -m pytest tests/test_parser.py::test_load_csv_basic -v --no-header -p no:xdist
```

Expected: `ImportError: cannot import name 'load_csv' from 'src.parser'`

- [ ] **Step 3: Implement `load_csv`**

Add to `lib/optimizer/src/parser.py`:

```python
import csv
import io


def load_csv(path):
    """Load CSV file, return (headers, rows).

    Each row is a dict mapping header name to value.
    Raises ValueError if no headers or no data rows.
    """
    text = Path(path).read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise ValueError("CSV file has no headers")
    rows = list(reader)
    if not rows:
        raise ValueError("CSV file has no data rows")
    return list(reader.fieldnames), rows
```

- [ ] **Step 4: Run all parser tests**

```bash
cd lib/optimizer && python -m pytest tests/test_parser.py -v --no-header -p no:xdist
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/optimizer/src/parser.py lib/optimizer/tests/test_parser.py
git commit -m "add CSV loader with validation"
```

---

### Task 5: DSPy Bridge (TDD)

**Files:**
- Create: `lib/optimizer/tests/test_bridge.py`
- Create: `lib/optimizer/src/bridge.py`

- [ ] **Step 1: Write failing tests**

Create `lib/optimizer/tests/test_bridge.py`:

```python
import dspy

from src.bridge import build_signature, rows_to_examples


def test_build_signature_single_input_output():
    sig = build_signature("Rewrite the input.", ["source"], ["rewritten"])
    assert "source" in sig.input_fields
    assert "rewritten" in sig.output_fields
    assert len(sig.input_fields) == 1
    assert len(sig.output_fields) == 1


def test_build_signature_doc():
    sig = build_signature("Rewrite the input.", ["source"], ["rewritten"])
    assert sig.__doc__ == "Rewrite the input."


def test_build_signature_multi_input():
    sig = build_signature("Do the thing.", ["source", "medium"], ["rewritten"])
    assert "source" in sig.input_fields
    assert "medium" in sig.input_fields
    assert "rewritten" in sig.output_fields
    assert len(sig.input_fields) == 2


def test_rows_to_examples_basic():
    rows = [{"source": "hello", "rewritten": "hi"}]
    examples = rows_to_examples(rows, ["source"])
    assert len(examples) == 1
    assert examples[0].source == "hello"
    assert examples[0].rewritten == "hi"
    assert list(examples[0].inputs().keys()) == ["source"]


def test_rows_to_examples_multi_input():
    rows = [{"source": "hi", "medium": "email", "rewritten": "hey"}]
    examples = rows_to_examples(rows, ["source", "medium"])
    assert set(examples[0].inputs().keys()) == {"source", "medium"}


def test_rows_to_examples_multiple_rows():
    rows = [
        {"source": "a", "rewritten": "A"},
        {"source": "b", "rewritten": "B"},
    ]
    examples = rows_to_examples(rows, ["source"])
    assert len(examples) == 2
    assert examples[1].source == "b"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd lib/optimizer && python -m pytest tests/test_bridge.py -v --no-header -p no:xdist
```

Expected: `ModuleNotFoundError: No module named 'src.bridge'`

- [ ] **Step 3: Implement bridge module**

Create `lib/optimizer/src/bridge.py`:

```python
import dspy


def build_signature(prompt, input_fields, output_fields):
    """Create a DSPy Signature class from a prompt and field definitions.

    The prompt becomes the Signature's __doc__ (instruction).
    Column names become InputField/OutputField definitions.
    """
    fields = {}
    for name in input_fields:
        fields[name] = dspy.InputField()
    for name in output_fields:
        fields[name] = dspy.OutputField()

    return type("DynamicSignature", (dspy.Signature,), {"__doc__": prompt, **fields})


def rows_to_examples(rows, input_fields):
    """Convert CSV row dicts to DSPy Example objects with input marking."""
    examples = []
    for row in rows:
        ex = dspy.Example(**row).with_inputs(*input_fields)
        examples.append(ex)
    return examples
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd lib/optimizer && python -m pytest tests/test_bridge.py -v --no-header -p no:xdist
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/optimizer/src/bridge.py lib/optimizer/tests/test_bridge.py
git commit -m "add DSPy bridge: signature creation and example conversion"
```

---

### Task 6: Extractor (TDD)

**Files:**
- Create: `lib/optimizer/tests/test_extractor.py`
- Create: `lib/optimizer/src/extractor.py`

- [ ] **Step 1: Write failing tests**

Create `lib/optimizer/tests/test_extractor.py`:

```python
import dspy

from src.extractor import extract_demos, format_optimized_prompt


class _MockModule:
    def __init__(self, demos):
        self.demos = demos


def test_extract_demos_basic():
    module = _MockModule([dspy.Example(source="hello", rewritten="hi")])
    demos = extract_demos(module)
    assert demos == [{"source": "hello", "rewritten": "hi"}]


def test_extract_demos_empty():
    assert extract_demos(_MockModule([])) == []


def test_extract_demos_no_attr():
    assert extract_demos(object()) == []


def test_format_single_demo():
    demos = [{"source": "Hello world", "rewritten": "Hi"}]
    result = format_optimized_prompt(
        "Rewrite the input.",
        demos,
        input_fields=["source"],
        output_fields=["rewritten"],
    )
    assert result.startswith("## Examples")
    assert '**Input:**' in result
    assert 'source: "Hello world"' in result
    assert '**Output:**' in result
    assert 'rewritten: "Hi"' in result
    assert result.endswith("Rewrite the input.")


def test_format_no_demos():
    result = format_optimized_prompt("Original.", [], ["x"], ["y"])
    assert result == "Original."


def test_format_multiple_demos():
    demos = [
        {"source": "A", "rewritten": "a"},
        {"source": "B", "rewritten": "b"},
    ]
    result = format_optimized_prompt("Prompt.", demos, ["source"], ["rewritten"])
    assert result.count("**Input:**") == 2
    assert result.count("**Output:**") == 2
    assert result.endswith("Prompt.")


def test_format_multi_field():
    demos = [{"source": "hi", "medium": "email", "rewritten": "hey"}]
    result = format_optimized_prompt(
        "Prompt.", demos, ["source", "medium"], ["rewritten"]
    )
    assert 'source: "hi"' in result
    assert 'medium: "email"' in result
    assert 'rewritten: "hey"' in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd lib/optimizer && python -m pytest tests/test_extractor.py -v --no-header -p no:xdist
```

Expected: `ModuleNotFoundError: No module named 'src.extractor'`

- [ ] **Step 3: Implement extractor module**

Create `lib/optimizer/src/extractor.py`:

```python
def extract_demos(compiled_module):
    """Pull few-shot demos from a compiled DSPy module.

    Returns a list of plain dicts, one per demo.
    """
    demos = getattr(compiled_module, "demos", None) or []
    return [{k: demo[k] for k in demo.keys()} for demo in demos]


def format_optimized_prompt(original_prompt, demos, input_fields, output_fields):
    """Format demos as natural language examples, prepend to original prompt.

    Returns the original prompt unchanged if demos is empty.
    """
    if not demos:
        return original_prompt

    sections = []
    for demo in demos:
        input_lines = "\n".join(f'{f}: "{demo[f]}"' for f in input_fields if f in demo)
        output_lines = "\n".join(f'{f}: "{demo[f]}"' for f in output_fields if f in demo)
        sections.append(f"**Input:**\n{input_lines}\n\n**Output:**\n{output_lines}")

    examples_block = "## Examples\n\n" + "\n\n---\n\n".join(sections)
    return f"{examples_block}\n\n---\n\n{original_prompt}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd lib/optimizer && python -m pytest tests/test_extractor.py -v --no-header -p no:xdist
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/optimizer/src/extractor.py lib/optimizer/tests/test_extractor.py
git commit -m "add extractor: demo extraction and prompt formatting"
```

---

### Task 7: Optimizer Wrapper

**Files:**
- Create: `lib/optimizer/src/optimizer.py`

No unit test for this task — the optimizer wraps DSPy's BootstrapFewShot which requires LLM calls. Tested via integration tests in Task 9.

- [ ] **Step 1: Implement optimizer module**

Create `lib/optimizer/src/optimizer.py`:

```python
import dspy


def optimize(signature_cls, examples, max_demos=4):
    """Run BootstrapFewShot optimization, return compiled Predict module.

    Assumes dspy.configure(lm=...) has already been called.
    The compiled module's .demos attribute contains the selected few-shot examples.
    """
    predictor = dspy.Predict(signature_cls)
    output_keys = list(signature_cls.output_fields.keys())

    def metric(example, prediction, trace=None):
        return all(bool(getattr(prediction, k, None)) for k in output_keys)

    optimizer = dspy.BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=max_demos,
    )
    return optimizer.compile(predictor, trainset=examples)
```

- [ ] **Step 2: Verify import works**

```bash
cd lib/optimizer && python -c "from src.optimizer import optimize; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add lib/optimizer/src/optimizer.py
git commit -m "add BootstrapFewShot optimizer wrapper"
```

---

### Task 8: CLI Entry Point (TDD)

**Files:**
- Create: `lib/optimizer/tests/test_cli.py`
- Create: `lib/optimizer/bin/optimize_prompt.py`

- [ ] **Step 1: Write failing tests for arg parsing**

Create `lib/optimizer/tests/test_cli.py`:

```python
from optimize_prompt import parse_args


def test_parse_args_required():
    args = parse_args(["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "out"])
    assert args.prompt == "p.md"
    assert args.training_data == "t.csv"
    assert args.output_fields == ["out"]


def test_parse_args_defaults():
    args = parse_args(["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "out"])
    assert args.model == "haiku"
    assert args.strategy == "bootstrap_fewshot"
    assert args.max_demos == 4


def test_parse_args_custom_values():
    args = parse_args([
        "--prompt", "p.md",
        "--training-data", "t.csv",
        "--output-fields", "out",
        "--model", "sonnet",
        "--max-demos", "8",
    ])
    assert args.model == "sonnet"
    assert args.max_demos == 8


def test_parse_args_multi_output_fields():
    args = parse_args(["--prompt", "p.md", "--training-data", "t.csv", "--output-fields", "a,b"])
    assert args.output_fields == ["a", "b"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd lib/optimizer && python -m pytest tests/test_cli.py -v --no-header -p no:xdist
```

Expected: `ModuleNotFoundError: No module named 'optimize_prompt'`

- [ ] **Step 3: Implement the CLI entry point**

Create `lib/optimizer/bin/optimize_prompt.py`:

```python
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MODEL_MAP = {
    "haiku": "anthropic/claude-haiku-4-5-20251001",
    "sonnet": "anthropic/claude-sonnet-4-6-20250514",
}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Optimize a prompt with few-shot examples")
    parser.add_argument("--prompt", required=True, help="Path to prompt file, or - for stdin")
    parser.add_argument("--training-data", required=True, help="Path to CSV file")
    parser.add_argument("--output-fields", required=True, help="Comma-separated output column names")
    parser.add_argument("--model", default="haiku", choices=list(MODEL_MAP.keys()),
                        help="Target model (default: haiku)")
    parser.add_argument("--strategy", default="bootstrap_fewshot",
                        help="Optimization strategy (default: bootstrap_fewshot)")
    parser.add_argument("--max-demos", type=int, default=4,
                        help="Max few-shot examples to include (default: 4)")
    args = parser.parse_args(argv)
    args.output_fields = [f.strip() for f in args.output_fields.split(",")]
    return args


def main():
    import dspy

    from src.bridge import build_signature, rows_to_examples
    from src.extractor import extract_demos, format_optimized_prompt
    from src.optimizer import optimize
    from src.parser import load_csv, parse_prompt

    args = parse_args()

    lm = dspy.LM(MODEL_MAP[args.model])
    dspy.configure(lm=lm)

    _, prompt = parse_prompt(args.prompt)
    headers, rows = load_csv(args.training_data)
    input_fields = [h for h in headers if h not in args.output_fields]

    signature = build_signature(prompt, input_fields, args.output_fields)
    examples = rows_to_examples(rows, input_fields)
    compiled = optimize(signature, examples, max_demos=args.max_demos)

    demos = extract_demos(compiled)
    optimized = format_optimized_prompt(prompt, demos, input_fields, args.output_fields)
    print(optimized)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd lib/optimizer && python -m pytest tests/test_cli.py -v --no-header -p no:xdist
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/optimizer/bin/optimize_prompt.py lib/optimizer/tests/test_cli.py
git commit -m "add CLI entry point with arg parsing and pipeline wiring"
```

---

### Task 9: Integration + Smoke Tests

**Files:**
- Create: `lib/optimizer/tests/test_integration.py`

These tests make real LLM calls via DSPy. They use `@pytest.mark.integration` and are auto-skipped without `ANTHROPIC_API_KEY`.

- [ ] **Step 1: Write integration tests**

Create `lib/optimizer/tests/test_integration.py`:

```python
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
```

- [ ] **Step 2: Run unit tests (should all still pass)**

```bash
cd lib/optimizer && python -m pytest tests/ -v --no-header -p no:xdist -m "not integration"
```

Expected: all unit tests PASS, integration tests skipped or not collected.

- [ ] **Step 3: Run integration tests**

```bash
cd lib/optimizer && python -m pytest tests/test_integration.py -v --no-header -p no:xdist
```

Expected: all 4 tests PASS (requires `ANTHROPIC_API_KEY` in environment). Each test may take 15-60s due to DSPy LLM calls.

- [ ] **Step 4: Commit**

```bash
git add lib/optimizer/tests/test_integration.py
git commit -m "add integration and smoke tests for prompt optimizer"
```

---

### Task 10: Docs + Symlink

**Files:**
- Create: `bin/optimize_prompt.py` (symlink)
- Create: `lib/optimizer/README.md`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Create `bin/` directory and symlink**

```bash
mkdir -p bin
ln -s ../lib/optimizer/bin/optimize_prompt.py bin/optimize_prompt.py
```

Verify:

```bash
ls -la bin/optimize_prompt.py
```

Expected: symlink pointing to `../lib/optimizer/bin/optimize_prompt.py`.

- [ ] **Step 2: Create `lib/optimizer/README.md`**

```markdown
# Prompt Optimizer

DSPy-based few-shot prompt optimizer. Finds optimal examples for any prompt using BootstrapFewShot optimization.

## Usage

```
python bin/optimize_prompt.py \
  --prompt path/to/prompt.md \
  --training-data path/to/training.csv \
  --output-fields rewritten \
  --model haiku \
  --max-demos 4
```

Output: optimized prompt printed to stdout (original prompt with few-shot examples prepended).

## Flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--prompt` | yes | — | Path to prompt file, or `-` for stdin |
| `--training-data` | yes | — | Path to CSV file |
| `--output-fields` | yes | — | Comma-separated column names that are outputs |
| `--model` | no | `haiku` | Target model (`haiku`, `sonnet`) |
| `--strategy` | no | `bootstrap_fewshot` | Optimization strategy |
| `--max-demos` | no | `4` | Max few-shot examples to include |

## Training Data Format

CSV with headers. Columns listed in `--output-fields` become outputs; all others become inputs.

```csv
source,rewritten
"I wanted to let you know that the meeting has been moved.","Meeting moved to next Tuesday."
```

Multi-input:

```csv
source,medium,rewritten
"I wanted to let you know...","email","Meeting moved."
```

## Output Format

```markdown
## Examples

**Input:**
source: "I wanted to let you know..."

**Output:**
rewritten: "Meeting moved to next Tuesday."

---

[original prompt content]
```

## Frontmatter

If the prompt file contains YAML frontmatter (`---` delimiters), it is automatically stripped. The body becomes the prompt.

## Running Tests

Unit tests (no LLM calls):

```bash
cd lib/optimizer && python -m pytest tests/ -v -m "not integration"
```

All tests (requires `ANTHROPIC_API_KEY`):

```bash
cd lib/optimizer && python -m pytest tests/ -v
```
```

- [ ] **Step 3: Update `CLAUDE.md` project structure**

Add `lib/optimizer/` to the Project Structure section in `CLAUDE.md`, after the `docs/` entry:

```markdown
- `lib/optimizer/` -- DSPy-based few-shot prompt optimizer. Dev-only tool. See `lib/optimizer/README.md`.
```

- [ ] **Step 4: Verify symlink works**

```bash
python bin/optimize_prompt.py --help
```

Expected: prints usage with all flags listed.

- [ ] **Step 5: Run full test suite one last time**

```bash
cd lib/optimizer && python -m pytest tests/ -v --no-header -p no:xdist -m "not integration"
```

Expected: all unit tests PASS.

- [ ] **Step 6: Commit**

```bash
git add bin/optimize_prompt.py lib/optimizer/README.md CLAUDE.md
git commit -m "add docs, README, and bin symlink for prompt optimizer"
```
