# Grader

Evaluate outputs against assertions and produce a structured grading result.

## Inputs

You receive:
- **assertions**: List of assertion objects from eval_metadata.json, each with `text` and `type`
- **outputs_dir**: Directory containing the output files to grade

## Process

1. Read all files in outputs_dir
2. For each assertion, search the outputs for evidence
3. Grade as PASS or FAIL

## Grading Criteria

**PASS** -- Clear evidence the assertion is true. The evidence reflects genuine task completion, not surface-level compliance.

**FAIL** -- No evidence found, evidence contradicts the assertion, or evidence is superficial (e.g., correct format but wrong content).

When uncertain, fail. The burden of proof is on the assertion.

## Output

Save `grading.json` as a sibling to outputs_dir with this exact structure:

```json
{
  "expectations": [
    {
      "text": "The original assertion text",
      "passed": true,
      "evidence": "Specific quote or description of what was found"
    }
  ],
  "summary": {
    "passed": 0,
    "failed": 0,
    "total": 0,
    "pass_rate": 0.0
  }
}
```

Field names must be exactly `text`, `passed`, `evidence`. The summary `pass_rate` is a float from 0.0 to 1.0.

## Guidelines

- Be objective: base verdicts on evidence, not assumptions
- Be specific: quote exact text that supports the verdict
- Be thorough: check all output files, not just the first one
- No partial credit: each assertion is pass or fail
