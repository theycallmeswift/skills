# DSPy Training Data Format Research

## 1. dspy.Example: The Core Data Primitive

### Construction

`dspy.Example` is a dict-like object that holds a single training/test datapoint. It accepts arbitrary keyword arguments as fields:

```python
qa_pair = dspy.Example(question="This is a question?", answer="This is an answer.")
```

- Fields can have **any keys** and **any value types**, though values are usually strings.
- Access fields via dot notation: `qa_pair.question`, `qa_pair.answer`
- Supports dict-like iteration: `keys()`, `values()`, `items()`
- Update values via dot assignment: `qa_pair.question = "new question"`

### Input Keys (Critical Concept)

The `with_inputs()` method marks which fields are **inputs** vs **labels/metadata**. This is how DSPy distinguishes what gets passed to the model vs what's used for evaluation:

```python
# Mark 'question' as input; 'answer' is the label
example = dspy.Example(question="Why?", answer="Because.").with_inputs("question")

# Multiple inputs
example = dspy.Example(context="...", question="...", answer="...").with_inputs("context", "question")
```

- `example.inputs()` returns a new Example with only input fields
- `example.labels()` returns a new Example with only non-input fields
- `example.without("field1", "field2")` excludes specific fields
- `with_inputs()` returns a copy; the original is unchanged

### Prediction (Example subclass)

`dspy.Prediction` is a subclass of `Example`. DSPy modules return `Prediction` objects. This means metrics/evaluators receive both the `Example` (ground truth) and `Prediction` (model output) in the same format.

### How Optimizers Consume Examples

Optimizers expect a **list of Example objects** as `trainset`:

```python
trainset = [dspy.Example(**d).with_inputs('question') for d in data]

optimizer = dspy.BootstrapFewShot(metric=quality_metric, max_bootstrapped_demos=3)
optimized = optimizer.compile(module, trainset=trainset)
```

Key points:
- **Training set**: Typically 30-300 examples. Optimizers learn from these directly.
- **Validation set**: Also 30-300 examples. Optimizers check progress against these.
- **MIPROv2** auto-splits trainset into 20% training / 80% validation if you don't pass a separate valset.
- For prompt optimizers, more validation than training is often better.
- You can use DSPy effectively with **zero labels** (just inputs), but you need at least a few example inputs.

## 2. Standard File Format for Persisting Examples

DSPy has **no canonical on-disk format**. The recommended approach is "the Pythonic way" -- load from whatever source and construct Example objects in code. That said, the conventions observed across DSPy tutorials and ecosystem projects:

### JSONL (Most Common in Official Tutorials)

The RAG tutorial loads from JSONL:

```python
with open("ragqa_arena_tech_examples.jsonl") as f:
    data = [orjson.loads(line) for line in f]

# Each line is a JSON object like:
# {"question": "why igp is used in mpls?", "response": "An IGP exchanges...", "gold_doc_ids": [2822, 2823]}

trainset = [dspy.Example(**d).with_inputs('question') for d in data]
```

### CSV (Documented in Loading Custom Data)

```python
df = pd.read_csv("sample.csv")
dataset = []
for context, question, answer in df.values:
    dataset.append(dspy.Example(context=context, question=question, answer=answer).with_inputs("context", "question"))
```

### JSON Array (Used by Skill Optimizer Projects)

Both skill-optimizer projects use plain JSON:

```json
[
  {
    "input": {"code": "...", "language": "python"},
    "expected_output": {"critical_issues": "...", "high_issues": "..."},
    "reasoning": "Optional chain-of-thought"
  }
]
```

### HuggingFace Datasets

DSPy has built-in dataset loaders (e.g., `dspy.HotPotQA`) that wrap HuggingFace datasets.

### Dataset Class (Advanced)

DSPy provides a `Dataset` base class. Subclass it and populate `_train`, `_dev`, `_test` as lists of dicts:

```python
class CSVDataset(Dataset):
    def __init__(self, file_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        df = pd.read_csv(file_path)
        self._train = df.iloc[0:700].to_dict(orient='records')
        self._dev = df.iloc[700:].to_dict(orient='records')
```

### Summary of Format Conventions

| Format | When to Use | Pattern |
|--------|-------------|---------|
| JSONL  | Large datasets, streaming | One JSON object per line, `with_inputs()` in code |
| JSON   | Small datasets, skill training | Array of objects with `input`/`expected_output` |
| CSV    | Tabular data | Load via pandas, construct Examples in code |
| HuggingFace | Standard benchmarks | Use built-in loaders |

**The universal pattern**: Store raw data in whatever format is natural. Convert to `list[dspy.Example]` in Python. Call `.with_inputs()` to mark input fields.

## 3. Skill-Optimizer Projects: Training Data Structure

### Ash-Blanc/skill-optimizer

**Repo structure** (master branch):
```
skill-optimizer/
  app/
    models/
      skill.py       # Pydantic models for Skill, Example, SkillMetrics
    pipeline/
      parsers.py     # MarkdownSkillParser
  skills/            # Skill definitions (YAML or Markdown)
  examples/          # Example skills
  knowledge/         # Reference knowledge
  prompts/           # Prompt templates
  prompts.json
```

**Data models** (from `app/models/skill.py`):

```python
class Example(BaseModel):
    """A training/few-shot example for skill optimization."""
    input: dict[str, Any]           # Input data for this example
    expected_output: dict[str, Any] # Expected output
    reasoning: Optional[str]        # Optional chain-of-thought reasoning

class Skill(BaseModel):
    name: str
    description: str
    instructions: str              # Core prompt
    input_schema: dict[str, Any]   # JSON Schema for inputs
    output_schema: dict[str, Any]  # JSON Schema for outputs
    examples: list[Example]        # Training/few-shot examples
    metrics: Optional[SkillMetrics]
    version: str = "1.0.0"
    optimized_for: list[str]       # Model IDs optimized for
    tags: list[str]
    author: Optional[str]
```

**Training data loading**: The `Skill.load()` method looks for sidecar training files:
1. `TRAINING.json` in the skill directory
2. `{name}_training.json` as fallback
3. Normalizes `input`/`expected_output` dicts automatically

**Proposed skill directory structure**:
```
my-skill/
  SKILL.md          # or SKILL.yaml
  TRAINING.json     # Sidecar training data
```

**TRAINING.json format**:
```json
[
  {
    "input": {"code": "def foo(): ...", "language": "python"},
    "expected_output": {"issues": ["SQL injection"], "severity": "Critical"},
    "reasoning": "The function uses string concatenation..."
  }
]
```

### instavm/skill-optimization

**Repo structure**:
```
skill-optimization/
  data/
    training_data.json  # 10 training cases
  examples/             # Actual code files to review
  scripts/
    optimize_qwen.py    # BootstrapFewShot on local Qwen
    run_azure_optimization.py
  skills/               # SKILL.md files
  src/
    optimizer.py         # DSPy pipeline
  results/
  docs/
    blog_post.md
```

**Training data format** (`data/training_data.json`):
```json
{
  "training_cases": [
    {
      "id": "train_001",
      "file_path": "examples/example_1.py",
      "language": "python",
      "description": "Authentication system with SQL injection and weak hashing",
      "expected_issues": [
        {
          "title": "SQL Injection Vulnerability",
          "severity": "Critical",
          "locations": ["authenticate_user:10"],
          "category": "security",
          "description": "String concatenation used to build SQL queries",
          "impact": "Attackers can bypass authentication..."
        }
      ],
      "severity_distribution": {"Critical": 3, "High": 3, "Medium": 1, "Low": 0},
      "expected_fixes": [
        {
          "issue": "SQL Injection Vulnerability",
          "fix_approach": "Use parameterized queries",
          "code_example": "cursor.execute('SELECT * FROM users WHERE username = ?', (username,))"
        }
      ],
      "overall_quality": "Poor - Multiple critical security vulnerabilities",
      "should_block_deployment": true
    }
  ],
  "metadata": {
    "version": "1.0",
    "created": "2025-12-21",
    "total_cases": 10,
    "purpose": "Training data for code review skill optimization"
  }
}
```

**Key difference from Ash-Blanc**: instavm uses a richer, domain-specific schema with `expected_issues`, `severity_distribution`, `expected_fixes`, and metadata. The training cases are then converted to `dspy.Example` objects in the optimizer script:

```python
trainset = [dspy.Example(**ex).with_inputs('input_field') for ex in training_data]
```

**DSPy Signature used**:
```python
class CodeReview(dspy.Signature):
    """Find security vulnerabilities and bugs in code."""
    code = dspy.InputField()
    language = dspy.InputField()
    critical_issues = dspy.OutputField()
    high_issues = dspy.OutputField()
```

### Key Findings from Both Projects

1. **DSPy doesn't parse SKILL.md**. You manually convert Skill -> DSPy Signature.
2. **DSPy doesn't generate training data**. You create 5-10 examples manually (or use LLM + manual verification).
3. **DSPy doesn't output a new SKILL.md**. You manually extract improvements from the optimized module.
4. **BootstrapFewShot** showed +12.5% improvement on local models (Qwen), 0% on frontier models (GPT-4o) -- frontier models already handle well-written skills well.
5. **The optimization loop**: Define Signature -> Create training examples -> Write metric function -> Run optimizer -> Extract best examples/instructions -> Update SKILL.md.

## 4. Practical Recommendations for MechaSwift

Based on the research, the recommended training data format for MechaSwift skill optimization:

### File Convention
- Store training data as `TRAINING.json` alongside each skill's `SKILL.md`
- Use JSON array format (not JSONL) since skill training sets are small (5-30 examples)

### Schema
```json
[
  {
    "input": {
      "field1": "value1",
      "field2": "value2"
    },
    "expected_output": {
      "field1": "value1"
    },
    "reasoning": "Optional chain-of-thought explaining why this output is correct"
  }
]
```

### Conversion to DSPy
```python
import json
import dspy

with open("skills/my-skill/TRAINING.json") as f:
    data = json.load(f)

trainset = []
for ex in data:
    flat = {**ex["input"], **ex["expected_output"]}
    if ex.get("reasoning"):
        flat["reasoning"] = ex["reasoning"]
    trainset.append(
        dspy.Example(**flat).with_inputs(*ex["input"].keys())
    )
```

### Sizing Guidelines
- **Minimum**: 5 examples (enough for BootstrapFewShot)
- **Recommended**: 10-20 examples for prompt optimization
- **For MIPROv2**: 30+ examples (auto-splits 20/80 train/val)
- Include both positive and negative/edge cases
