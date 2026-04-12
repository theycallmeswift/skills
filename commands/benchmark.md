---
description: Run the test suite across haiku, sonnet, and opus and produce a comparison report.
---

Run the full eval suite across three models and produce a benchmark report. Follow these steps exactly.

## Step 1: Run tests on each model

Run the test suite three times in sequence. For each run, use `--tb=line` so failure reasons are captured in one line each.

**Run 1 — Haiku:**
```
CLAUDE_TEST_MODEL=haiku CLAUDE_TEST_TIMEOUT=60 uv run pytest tests/ -v --tb=line 2>&1
```

**Run 2 — Sonnet:**
```
CLAUDE_TEST_MODEL=sonnet CLAUDE_TEST_TIMEOUT=60 uv run pytest tests/ -v --tb=line 2>&1
```

**Run 3 — Opus (2x timeout):**
```
CLAUDE_TEST_MODEL=opus CLAUDE_TEST_TIMEOUT=120 uv run pytest tests/ -v --tb=line 2>&1
```

Run these sequentially (not in parallel). Capture the full output of each run — you will need it for the analysis.

## Step 2: Output the results comparison table

After all three runs complete, output a markdown table:

```
## Results Comparison

| | Haiku | Sonnet | Opus |
|---|---|---|---|
| **Passed** | N | N | N |
| **Failed** | N | N | N |
| **Total** | N | N | N |
| **Pass Rate** | N% | N% | N% |
| **Duration** | Ns | Ns | Ns |
```

## Step 3: Output the failure breakdown table

Build a table with one row per test that failed on ANY model. Columns are the test name and one column per model. Cells show FAIL or — (pass).

- Use short test names: `TestClass::test_name` with parametrize suffix like `(pasted)` instead of the full `[pasted_output]`
- Group rows by skill (Ghostwrite, Summarize)
- Bold the skill group headers

```
## Failure Breakdown by Test

| Test | Haiku | Sonnet | Opus |
|---|---|---|---|
| **Ghostwrite** | | | |
| `test_loads_about_swift` (email) | FAIL | — | FAIL |
| ... | ... | ... | ... |
| **Summarize** | | | |
| ... | ... | ... | ... |
```

## Step 4: Analysis

Write an **Analysis** section that categorizes the failures into 2-4 groups based on root cause. For each group:

- Name the category (e.g., "Process/workflow failures", "Structural/formatting compliance")
- List the specific tests that fall into it
- Explain the root cause based on the `--tb=line` failure messages
- Note which models are affected and why

Use the `--tb=line` output from each run to understand WHY tests failed, not just that they failed.

## Step 5: Key takeaways

Write a **Key takeaways** section with 3-5 bullet points summarizing the most important findings. Focus on:

- Which model performed best and why
- Systematic weaknesses (input types, skill pipeline shortcuts, formatting compliance)
- Patterns that suggest prompt improvements vs. model limitations

## Formatting rules

- Output everything as a single markdown document
- Use `##` for section headers
- No preamble before the first table — start directly with `## Results Comparison`
- No postscript after Key takeaways
