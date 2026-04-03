# Skill Evals

How we test and improve skills in MechaSwift.

## Approach

We use Anthropic's **skill-creator** skill to run the full eval lifecycle. It handles running test cases, grading, benchmarking, and visual review in a single workflow. No custom scripts needed.

There are two types of evals:

- **Quality evals** -- Does the skill produce good output? Runs each test prompt with and without the skill loaded, grades against assertions, compares the results.
- **Trigger evals** -- Does Claude actually activate the skill when it should (and not when it shouldn't)? Tests the skill description as a routing mechanism.

## Eval file format

Each skill with evals has an `evals/evals.json`:

```json
{
  "skill_name": "ghostwrite",
  "evals": [
    {
      "id": 1,
      "prompt": "The user's task prompt",
      "expected_output": "Description of expected result",
      "files": [],
      "assertions": [
        { "text": "Output contains X", "type": "structural" }
      ]
    }
  ]
}
```

Key fields:
- `prompt` -- The exact user message to test
- `expected_output` -- Human-readable description of success
- `files` -- Optional input files for the test
- `expectations` -- Pass/fail assertions graded by an LLM judge. Use the fields `text`, `passed`, and `evidence` in grading output.
- `cleanup` -- Optional glob patterns for files to remove after eval

## Running quality evals

Invoke the skill-creator skill and tell it to run evals on an existing skill. It will:

1. Spawn parallel subagents for each test case (with-skill and without-skill baseline)
2. Grade outputs against assertions using a dedicated grader agent
3. Aggregate results into `benchmark.json` with pass rates, timing (mean +/- stddev), and token usage
4. Launch an HTML viewer for qualitative review (Outputs tab + Benchmark tab)
5. Collect your feedback and iterate

Results land in `tmp/<skill>-evals/iteration-<N>/` organized by eval case, with transcripts, timing, and grading for each variant.

Example:
```
tmp/ghostwrite-evals/iteration-1/
  eval-happy-path/
    with_skill/
      outputs/transcript.md
      timing.json
      grading.json
    without_skill/
      outputs/transcript.md
      timing.json
      grading.json
    eval_metadata.json
  benchmark.json
  benchmark.md
```

## Running trigger evals

Trigger evals test whether Claude routes prompts to your skill correctly. The skill-creator generates 20 realistic queries (mix of should-trigger and should-not-trigger), runs each 3x for reliability, then optimizes the skill description in a loop using a train/test split to prevent overfitting.

Run after the skill itself is in good shape. The description is a hyperparameter to optimize, not just metadata.

## Writing good evals

**Test cases**: Aim for at least 3 per skill. Include a happy path, an edge case, and an adversarial/negative case.

**Assertions**: Make them objectively verifiable. Use descriptive text that reads clearly in the benchmark viewer. Skip assertions for subjective qualities (tone, style) and rely on qualitative review for those.

**Trigger eval queries**: Make them realistic and detailed, not abstract. Include file paths, context, casual phrasing. The should-not-trigger cases should be near-misses, not obviously irrelevant prompts.

## Quick eval run

Use the `/eval` command for a fast pass/fail check:

```
/eval                        # All skills
/eval ghostwrite summarize   # Specific skills
/eval --no-baseline          # Skip baseline comparison
/eval --verbose              # Show all evidence
```

Results print inline as a summary table. Full outputs go to `tmp/evals/<timestamp>/`.

For the full eval lifecycle (iteration, visual review, description optimization), use the skill-creator skill instead.

## Current coverage

| Skill | Evals | Notes |
|-------|-------|-------|
| ghostwrite | 2 | Happy path + hard gate (refuses to create from scratch) |
| scope | 3 | Happy path + vague prompt + adversarial |
| summarize | 4 | dev.to article, specific URL, Anthropic page, PDF |

