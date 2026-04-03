# /eval Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `/eval` slash command skill that discovers skills with evals, runs with-skill + baseline tests in parallel, grades against assertions, and prints a pass/fail summary table.

**Architecture:** Single SKILL.md that orchestrates the eval workflow using subagents. No external scripts needed -- the skill tells Claude how to discover evals, spawn test runs, grade results, and format output. Results go to `tmp/evals/` by default.

**Tech Stack:** SKILL.md (Claude skill), subagents for parallel eval runs and grading, JSON for eval data, markdown for output.

---

## File Structure

```
skills/eval/
  SKILL.md              # The skill definition and orchestration logic
  references/
    grader.md           # Grading instructions for the subagent judge
```

The grader reference is loaded by subagents when grading outputs. It stays out of the main SKILL.md context to keep the skill lean.

---

### Task 1: Create the SKILL.md skeleton

**Files:**
- Create: `skills/eval/SKILL.md`

This is the core deliverable. The skill needs YAML frontmatter for triggering, argument parsing, skill discovery, and the orchestration workflow.

- [ ] **Step 1: Create the skill directory**

```bash
mkdir -p skills/eval/references
```

- [ ] **Step 2: Write the SKILL.md with frontmatter and argument parsing**

Create `skills/eval/SKILL.md` with:

```markdown
---
name: eval
description: "Run quality evals for MechaSwift skills. Use when the user says '/eval', 'run evals', 'test the skills', 'check skill quality', or 'run the benchmarks'. Accepts optional arguments to scope which skills to test and how to run them."
---

# /eval

Run quality evals for skills that have test cases defined in `evals/evals.json`.

## Arguments

Parse the user's message after `/eval` for these options:

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

**Baseline run** (unless `--no-baseline`):
Tell the subagent:
- Execute the same task prompt with NO skill file
- Do NOT read any skill files
- Save output to `without_skill/outputs/output.md`

Launch ALL runs (across all skills) in a single message to maximize parallelism.

### 4. Grade outputs

Once runs complete, spawn grading subagents in parallel for each run directory.

Each grader should:
1. Read `references/grader.md` from this skill's directory for grading instructions
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

- [ ] **Step 3: Commit**

```bash
git add skills/eval/SKILL.md
git commit -m "feat: add /eval skill skeleton with orchestration workflow"
```

---

### Task 2: Create the grader reference

**Files:**
- Create: `skills/eval/references/grader.md`

The grader is a focused set of instructions for the subagent that evaluates outputs against assertions. Keeping it in a reference file means it only loads when grading subagents need it, not when the skill first triggers.

- [ ] **Step 1: Write the grader reference**

Create `skills/eval/references/grader.md`:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add skills/eval/references/grader.md
git commit -m "feat: add grader reference for eval subagents"
```

---

### Task 3: Update project docs

**Files:**
- Modify: `CLAUDE.md` (add eval skill to Skills list)
- Modify: `docs/evals.md` (add /eval command section)

- [ ] **Step 1: Add eval to the Skills list in CLAUDE.md**

In CLAUDE.md, find the Skills section and add:

```markdown
- **eval** -- Run quality evals for all skills (or a subset). See `skills/eval/SKILL.md`.
```

- [ ] **Step 2: Add /eval section to docs/evals.md**

Add to `docs/evals.md` before the "Current coverage" section:

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/evals.md
git commit -m "docs: add /eval command to skill list and eval docs"
```

---

### Task 4: Test the skill end-to-end

**Files:**
- No new files. This task validates the skill works.

- [ ] **Step 1: Run `/eval ghostwrite` to test single-skill scoping**

Run: `/eval ghostwrite`

Expected:
- Discovers ghostwrite with 2 eval cases
- Spawns 4 subagents (2 with-skill, 2 baseline)
- Grades all 4 runs
- Prints summary table with ghostwrite results only
- Shows workspace path in `tmp/evals/`

- [ ] **Step 2: Verify output files exist**

```bash
ls tmp/evals/*/ghostwrite/eval-*/with_skill/grading.json
ls tmp/evals/*/ghostwrite/eval-*/without_skill/grading.json
```

Expected: 2 grading.json files per variant (4 total)

- [ ] **Step 3: Run `/eval --no-baseline` to test baseline skip**

Run: `/eval ghostwrite --no-baseline`

Expected:
- Only with-skill runs, no without_skill directories created
- Summary table has no Baseline or Delta columns

- [ ] **Step 4: Run `/eval` with no arguments to test full discovery**

Run: `/eval`

Expected:
- Discovers all 3 skills (ghostwrite, scope, summarize)
- Runs all 9 eval cases (18 total with baselines)
- Prints full summary table

- [ ] **Step 5: Commit any fixes**

If any issues were found and fixed during testing:

```bash
git add skills/eval/SKILL.md skills/eval/references/grader.md
git commit -m "fix: address issues found during eval skill testing"
```
