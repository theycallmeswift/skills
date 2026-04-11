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
