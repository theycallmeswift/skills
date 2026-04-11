# Prompt Optimizer

**Date:** 2026-04-11
**Status:** Approved

## Goal

Build a DSPy-based prompt optimizer that finds optimal few-shot examples for any prompt. Used during skill development to improve skill performance. Designed as a self-contained library extractable as a standalone CLI/package in the future.

## Non-Goals

- Optimizing anything beyond few-shot example selection (no MIPROv2/GEPA instruction rewriting in v1)
- Awareness of MechaSwift's skill format or directory structure
- Automatic training data generation
- Caching or incremental optimization
- Production runtime usage — this is a development-only tool

## Approach

Two-phase pipeline: DSPy BootstrapFewShot optimizes using training examples (CSV), then the caller validates with their own eval suite. The optimizer takes a prompt and training data in, outputs an optimized prompt to stdout. No skill awareness — the caller handles extraction and placement.

The prompt string becomes the `__doc__` of a dynamically-created DSPy Signature class. CSV columns become InputField/OutputField definitions based on a CLI flag (`--output-fields`). BootstrapFewShot selects the best few-shot demonstrations from the training data. The compiled module's demos are extracted and formatted as natural language examples prepended to the original prompt.

If the prompt file contains YAML frontmatter (`---` delimiters), it is automatically parsed out. The body becomes the prompt; metadata is available but does not enter the Signature instructions.

## Components

- `lib/optimizer/bin/optimize_prompt.py` — CLI entry point
- `lib/optimizer/src/__init__.py` — package init
- `lib/optimizer/src/parser.py` — prompt + frontmatter parsing, CSV loading
- `lib/optimizer/src/bridge.py` — prompt → DSPy Signature, CSV rows → `dspy.Example` objects
- `lib/optimizer/src/optimizer.py` — BootstrapFewShot wrapper
- `lib/optimizer/src/extractor.py` — compiled module → natural language few-shot examples
- `lib/optimizer/tests/` — unit, integration, and smoke tests
- `lib/optimizer/pyproject.toml` — standalone package metadata (dev-only deps)
- `bin/optimize_prompt.py` — symlink → `lib/optimizer/bin/optimize_prompt.py`

## Data / Interfaces

### CLI Interface

```
python bin/optimize_prompt.py \
  --prompt path/to/prompt.md \
  --training-data path/to/training.csv \
  --output-fields rewritten \
  --model haiku \
  --strategy bootstrap_fewshot \
  --max-demos 4
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--prompt` | yes | — | Path to prompt file, or `-` for stdin |
| `--training-data` | yes | — | Path to CSV file |
| `--output-fields` | yes | — | Comma-separated column names that are outputs |
| `--model` | no | `haiku` | Target model for optimization |
| `--strategy` | no | `bootstrap_fewshot` | Optimization strategy (only option in v1) |
| `--max-demos` | no | `4` | Max few-shot examples to include |

Output: optimized prompt printed to stdout.

### Training Data Format (CSV)

- Headers required (first row)
- Column names become DSPy Signature field names
- Columns listed in `--output-fields` become OutputFields; all others become InputFields
- Standard CSV quoting for multi-line content
- UTF-8 encoding
- At least one output column and one input column required

Single-input/single-output:
```csv
input,expected_output
"Hey team, I wanted to reach out about...","Hey team --\nShipping the new auth flow Friday..."
```

Multi-input:
```csv
source,medium,rewritten
"Hey team, I wanted to...","email","Hey team --\n..."
```

### DSPy Bridge

1. Parse prompt file — detect and strip YAML frontmatter if present, body becomes prompt string
2. Create Signature — `type(name, (dspy.Signature,), {"__doc__": prompt, **input_fields, **output_fields})`
3. Convert CSV rows — each row becomes `dspy.Example(**row).with_inputs(*input_column_names)`
4. Wrap in `dspy.Predict(signature)`

### Output Format

The optimized prompt is the original prompt with natural language few-shot examples prepended:

```markdown
## Examples

**Input:**
source: "Hey team, I wanted to..."
medium: "email"

**Output:**
rewritten: "Hey team --\n..."

---

[original prompt content here]
```

### Pipeline Stages

```
prompt.md + training.csv
        │
        ▼
   ┌─────────┐
   │  Parse   │  Read prompt, strip frontmatter, load CSV, split columns
   └────┬─────┘
        ▼
   ┌──────────┐
   │  Bridge   │  Create DSPy Signature + Examples
   └────┬──────┘
        ▼
   ┌──────────┐
   │ Optimize  │  BootstrapFewShot.compile()
   └────┬──────┘
        ▼
   ┌──────────┐
   │ Extract   │  Pull demos, format as natural language, prepend to prompt
   └────┬──────┘
        ▼
      stdout
```

## Testing

### Unit Tests (no LLM calls)

- CSV parsing: multi-line content, missing headers, empty rows, encoding edge cases
- Frontmatter detection: with/without frontmatter, malformed frontmatter
- Signature generation: correct InputField/OutputField split from column names and `--output-fields`
- Example extraction: demos formatted as natural language correctly
- CLI arg parsing: defaults, required flags, validation errors

### Integration Tests (real DSPy calls, small/cheap)

- End-to-end: simple prompt + 5-row CSV → optimized output on stdout
- Output contains original prompt plus examples section
- Selected demos are actual rows from the training CSV
- Model: Haiku, tiny training sets

### Smoke Test (bundled test skill)

- A minimal test skill bundled in `lib/optimizer/tests/fixtures/` (e.g., "rewrite this sentence to be shorter")
- Small CSV with 5-10 examples included in fixtures
- Proves the full pipeline works end-to-end
- Decoupled from MechaSwift — no imports from skills/ or tests/

### Running Tests

```bash
cd lib/optimizer && python -m pytest tests/ -v
```

## Dependencies

All dev-only (in `[dependency-groups]` dev group or `[project.optional-dependencies]`):

- `dspy` — core optimization framework
- `pydantic` — data models
- Standard lib: `csv`, `argparse`, `pathlib`

## Open Questions

None — all resolved during design.
