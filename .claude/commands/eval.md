Run quality evals for skills that have test cases defined in `evals/evals.json`.

## Arguments

Parse the following for options: $ARGUMENTS

- **Skill names** (positional) -- Run only these skills. Example: `/eval ghostwrite summarize`
- **`--no-baseline`** -- Skip the without-skill baseline runs. Faster, but no comparison data.
- **`--verbose`** -- Include full grading evidence in the output, not just pass/fail.
- **No arguments** -- Run all skills that have `evals/evals.json`.

## Workflow

### 1. Discover skills

Scan `skills/*/evals/evals.json` relative to the project root. For each file found, read it and validate it has a `skill_name` and non-empty `evals` array. If skill names were passed as arguments, filter to only those.

If no skills with evals are found, tell the user and stop.

Print what you found:

```
Found evals for 3 skills: ghostwrite (2 cases), scope (3 cases), summarize (4 cases)
Running...
```

### 2. Set up workspace

Create `tmp/evals/<timestamp>/` as the working directory for this run. Under that, create a directory per skill, and under each skill a directory per eval case using the pattern `eval-<id>-<slugified-prompt>/`.

```
tmp/evals/2026-04-03T14-30-00/
  ghostwrite/
    eval-1-sponsor-email/
      with_skill/outputs/
      without_skill/outputs/    # (skipped if --no-baseline)
      eval_metadata.json
    eval-2-linkedin-refusal/
      ...
  scope/
    ...
```

Write an `eval_metadata.json` for each case containing the eval id, prompt, and assertions from the evals.json.

### 3. Spawn all runs in parallel

For each eval case, spawn subagents in the background:

**With-skill run:**
Tell the subagent:
- Read the skill at `skills/<name>/SKILL.md`
- Execute the task from the eval prompt
- Read any referenced files the skill mentions (e.g., `references/about-swift.md`)
- If the eval has `files`, provide those as input
- Save all output to `with_skill/outputs/output.md`
- After the normal skill output, append a `## Tool Trace` section listing every fetch or read tool you actually invoked, one per line, formatted as `- tool_name: brief description`. Include MCP tools (e.g. `mcp__brightdata__scrape_as_markdown`, `mcp__brightdata__scrape_batch`), built-in tools (e.g. `WebFetch`, `WebSearch`, `Read`), or write `- none` if you did not invoke any. This is a regression check; do not omit it.

**Baseline run** (unless `--no-baseline`):
Tell the subagent:
- Execute the same task prompt with NO skill file
- Do NOT read any skill files
- Save output to `without_skill/outputs/output.md`
- Append a `## Tool Trace` section using the same format as the with-skill run.

Launch ALL runs (across all skills) in a single message to maximize parallelism.

### 4. Grade outputs

Once runs complete, spawn grading subagents in parallel for each run directory.

Each grader should:
1. Read the grader instructions below
2. Read the `eval_metadata.json` for assertions
3. Read the output files in `outputs/`
4. Evaluate each assertion as PASS or FAIL with evidence
5. Save `grading.json` to the run directory (sibling to `outputs/`)

The grading.json must use this structure:
```json
{
  "expectations": [
    { "text": "assertion text", "passed": true, "evidence": "what was found" }
  ],
  "summary": { "passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67 }
}
```

#### Grader instructions

**PASS** -- Clear evidence the assertion is true. The evidence reflects genuine task completion, not surface-level compliance.

**FAIL** -- No evidence found, evidence contradicts the assertion, or evidence is superficial (e.g., correct format but wrong content).

When uncertain, fail. The burden of proof is on the assertion. Be objective, cite specific evidence, check all output files, no partial credit.

### 5. Collect and display results

Read all grading.json files. Build and print a summary table:

```
## Eval Results

| Skill       | Eval                  | With Skill | Baseline | Delta |
|-------------|-----------------------|------------|----------|-------|
| ghostwrite  | sponsor-email         | 7/7 (100%) | 3/7 (43%) | +57% |
| ghostwrite  | linkedin-refusal      | 4/4 (100%) | 0/4 (0%)  | +100%|
| scope       | webhook-design        | 7/7 (100%) | 1/7 (14%) | +86% |
| scope       | vague-notifications   | 4/4 (100%) | 1/4 (25%) | +75% |
| scope       | skip-design-request   | 4/4 (100%) | 0/4 (0%)  | +100%|
| summarize   | devto-top-article     | 10/10(100%)| 2/10(20%) | +80% |
| ...         | ...                   | ...        | ...       | ...   |

**Overall: 44/45 with-skill (98%), 8/45 baseline (18%)**
```

If `--no-baseline` was used, omit the Baseline and Delta columns.

### 6. Show failures (if any)

For any with-skill assertion that failed, print the details:

```
### Failures

**summarize > specific-devto-article > with_skill**
- FAIL: "Comment section contains a code fence with content of 20 words or fewer"
  Evidence: Comment was 21 words, exceeding limit by 1.
```

If `--verbose`, also print passing assertions with their evidence.

### 7. Print workspace path

```
Full results: tmp/evals/2026-04-03T14-30-00/
```

### 8. Clean up artifact documents

Delete any files created under `docs/` during this eval run. Skills like `scope` may produce spec documents there as part of their normal output. These are eval artifacts, not real project docs, and should not be committed.

List each deleted file so the user can see what was removed. If nothing was created in `docs/`, skip silently.
