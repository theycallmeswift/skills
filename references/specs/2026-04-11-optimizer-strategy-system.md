# Optimizer Strategy System

Add a pluggable strategy architecture to the prompt optimizer and implement GEPA as the second optimization strategy.

## Goals

- Make the `--strategy` flag functional with a common interface
- Add GEPA (instruction rewriting) alongside BootstrapFewShot (few-shot example selection)
- Design for extraction as a standalone tool
- Strategy-specific config via JSON file

## Architecture

### File Structure

```
lib/optimizer/src/
├── strategy.py            # Protocol, Result dataclass, registry, get_strategy()
├── optimizers/
│   ├── __init__.py        # Imports modules to trigger registration
│   ├── bootstrap_fewshot.py
│   └── gepa.py
├── bridge.py
├── parser.py
└── extractor.py
```

`src/optimizer.py` is removed. Its logic migrates to `optimizers/bootstrap_fewshot.py`.

### Strategy Protocol

```python
from dataclasses import dataclass
from typing import Protocol

@dataclass
class OptimizationResult:
    prompt: str       # Final optimized prompt, ready for stdout
    metadata: dict    # Strategy-specific info (demos, iterations, scores, etc.)

class Strategy(Protocol):
    name: str

    def optimize(self, signature_cls, examples, config: dict) -> OptimizationResult:
        ...
```

### Registry

```python
STRATEGIES: dict[str, type[Strategy]] = {}

def register(name: str):
    """Decorator to register a strategy."""
    def decorator(cls):
        STRATEGIES[name] = cls
        return cls
    return decorator

def get_strategy(name: str) -> type[Strategy]:
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name]
```

Each strategy file uses `@register("name")`. The `optimizers/__init__.py` imports all strategy modules to trigger registration.

## CLI Interface

### Universal flags

- `--strategy` (default: `bootstrap_fewshot`) — strategy name for registry lookup
- `--prompt` (required) — file path or `-` for stdin
- `--training-data` (required) — CSV file
- `--output-fields` (required) — comma-separated output column names
- `--model` (default: `anthropic/claude-haiku-4-5-20251001`)
- `--config` (optional) — path to JSON file with strategy-specific params

### Output format

Optimized prompt to stdout, followed by metadata:

```
<optimized prompt>

---
strategy: gepa
generations: 12
score_improvement: 0.15
```

Metadata is always printed after a `---` separator as YAML-style `key: value` pairs, one per line.

## Strategy Implementations

### BootstrapFewShot

Migrated from current `src/optimizer.py`. Behavior unchanged.

**Config options:**
- `max_demos` (default: 4) — maximum few-shot examples to select

**Output:** Original prompt with `## Examples` section appended (current format via `extractor.py`).

### GEPA

Instruction-only optimizer using reflective mutation + genetic evolution.

**Config options:**
- `auto` (default: `"light"`) — budget preset (light/medium/heavy)
- `reflection_minibatch_size` (default: 3) — examples per reflection step
- `use_merge` (default: true) — merge successful variants
- `max_merge_invocations` (default: 5) — cap on merge attempts

**Output:** Rewritten prompt returned by the optimizer directly.

**Metric:** `GEPAFeedbackMetric` implementation that:
1. Checks all output fields are non-empty (pass/fail)
2. Uses a short LLM call to generate natural language feedback for GEPA's reflection

**Dependency:** Requires `dspy>=3.x`.

## Configuration

Strategy-specific params live in a JSON file passed via `--config`. If omitted, each strategy uses its defaults. Unknown keys for a given strategy raise an error.

Example for GEPA:
```json
{
  "auto": "light",
  "reflection_minibatch_size": 5
}
```

Example for BootstrapFewShot:
```json
{
  "max_demos": 6
}
```

## Testing

### Unit tests (no LLM calls)

- `strategy.py`: registry lookup, unknown strategy error, protocol enforcement
- `optimizers/bootstrap_fewshot.py`: same coverage as current tests, relocated
- `optimizers/gepa.py`: config validation, result formatting
- CLI: `--config` parsing, `--strategy` dispatch, metadata output formatting

### Integration tests (real DSPy calls)

- GEPA end-to-end with small training set (existing fixtures)
- Verify output is rewritten prompt (not original + examples)
- Verify metadata prints after `---` separator
- Gated on `dspy>=3.x` availability

## Migration

1. Create `src/strategy.py`
2. Create `src/optimizers/` with `__init__.py`, `bootstrap_fewshot.py`, `gepa.py`
3. Move logic from `src/optimizer.py` → `src/optimizers/bootstrap_fewshot.py`
4. Delete `src/optimizer.py`
5. Update `bin/optimize_prompt.py`: registry dispatch, config loading, metadata output
6. Update existing tests for new import paths
7. Add new tests for GEPA, registry, config

Existing behavior preserved: `--strategy bootstrap_fewshot` without `--config` works identically to current behavior.

## Dependencies

- `dspy>=3.x` (bump from current `>=2.5` — separate PR)
- No new dependencies beyond DSPy version bump

## Non-goals (this phase)

- Strategy composition/chaining
- Custom metric functions (beyond the built-in non-empty + feedback)
- Caching or incremental optimization
- MIPROv2 or BootstrapRS (future strategies, same interface)
