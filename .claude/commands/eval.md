Run quality evals for skills (`skills/*/evals/evals.json`) and project-level rule checks (`evals/*.json`).

## Arguments

Parse the following for options: $ARGUMENTS

- **Names** (positional) -- Run only these. Matches a `skill_name` (skill eval) or `eval_name` (project eval). Example: `/eval ghostwrite no-ai-attribution`
- **`--no-baseline`** -- Skip the without-skill baseline runs for skill evals. Faster, but no comparison data. (Project evals never have a baseline.)
- **`--verbose`** -- Include full grading evidence in the output, not just pass/fail.
- **No arguments** -- Run every skill eval and every project eval.

## Eval types

There are two kinds of eval files. The workflow handles each differently.

| Type | Location | Identifier field | Baseline? | Loads a skill? |
|---|---|---|---|---|
| Skill eval | `skills/<name>/evals/evals.json` | `skill_name` | yes (unless `--no-baseline`) | yes, the named skill |
| Project eval | `evals/<name>.json` | `eval_name` | no | no |

Project evals test global rules from AGENTS.md / CLAUDE.md (e.g. `no-ai-attribution`). They run the prompt once with the host's normal context and grade against assertions.

## Workflow

### 1. Discover evals

Scan two locations:
- `skills/*/evals/evals.json` -- skill evals. Validate each has a `skill_name` and non-empty `evals` array.
- `evals/*.json` -- project evals. Validate each has an `eval_name` and non-empty `evals` array.

If positional names were passed, filter to evals whose `skill_name` or `eval_name` matches.

If nothing is found, tell the user and stop.

Print what you found:

```
Found 3 skill evals: ghostwrite (2 cases), scope (3 cases), summarize (4 cases)
Found 1 project eval: no-ai-attribution (2 cases)
Running...
```

### 2. Set up workspace

Create `tmp/evals/<timestamp>/` as the working directory. Skill evals nest under their skill name. Project evals nest under `_project/<eval_name>/`. Each case gets `eval-<id>-<slugified-prompt>/`.

```
tmp/evals/2026-04-03T14-30-00/
  ghostwrite/
    eval-1-sponsor-email/
      with_skill/outputs/
      without_skill/outputs/    # (skipped if --no-baseline)
      eval_metadata.json
  scope/
    ...
  _project/
    no-ai-attribution/
      eval-1-throwaway-commit/
        run/outputs/             # single run, no baseline
        eval_metadata.json
      eval-2-pr-draft/
        ...
```

Write an `eval_metadata.json` for each case with the id, prompt, and assertions.

### 3. Spawn all runs in parallel

For each eval case, spawn subagents in the background.

**Skill eval — with-skill run:**
Tell the subagent:
- Read the skill at `skills/<name>/SKILL.md`
- Execute the task from the eval prompt
- Read any referenced files the skill mentions (e.g., `docs/about-swift.md`)
- If the eval has `files`, provide those as input
- Save all output to `with_skill/outputs/output.md`
- After the normal skill output, append a `## Tool Trace` section listing every fetch or read tool you actually invoked, one per line, formatted as `- tool_name: brief description`. Include MCP tools (e.g. `mcp__brightdata__scrape_as_markdown`, `mcp__brightdata__scrape_batch`), built-in tools (e.g. `WebFetch`, `WebSearch`, `Read`), or write `- none` if you did not invoke any. This is a regression check; do not omit it.

**Skill eval — baseline run** (unless `--no-baseline`):
Tell the subagent:
- Execute the same task prompt with NO skill file
- Do NOT read any skill files
- Save output to `without_skill/outputs/output.md`
- Append a `## Tool Trace` section using the same format as the with-skill run.

**Project eval — single run** (no baseline, no skill loaded):
Tell the subagent:
- Execute the task from the eval prompt with the host's normal context (AGENTS.md, CLAUDE.md, etc. apply as usual)
- Do NOT read any skill files
- Honor any safety guards in the prompt itself (e.g. "do not push", "do not run gh"). Project evals exist to test global rules, so the subagent must behave exactly as it would in a normal session.
- Save all output to `run/outputs/output.md`
- Append a `## Tool Trace` section in the same format as skill runs. For commit-related evals, also append a `## Git Log` section showing the relevant `git log` output the assertions need to grade against.

Launch ALL runs across all evals in a single message to maximize parallelism.

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

Read all grading.json files. Print two tables: one for skill evals, one for project evals (omit either if empty).

**Skill evals:**
```
## Skill Eval Results

| Skill       | Eval                  | With Skill | Baseline | Delta |
|-------------|-----------------------|------------|----------|-------|
| ghostwrite  | sponsor-email         | 7/7 (100%) | 3/7 (43%) | +57% |
| scope       | webhook-design        | 7/7 (100%) | 1/7 (14%) | +86% |
| ...         | ...                   | ...        | ...       | ...   |

**Overall: 44/45 with-skill (98%), 8/45 baseline (18%)**
```

If `--no-baseline` was used, omit the Baseline and Delta columns.

**Project evals:**
```
## Project Eval Results

| Eval               | Case                  | Result      |
|--------------------|-----------------------|-------------|
| no-ai-attribution  | throwaway-commit      | 6/6 (100%)  |
| no-ai-attribution  | pr-draft              | 7/7 (100%)  |

**Overall: 13/13 (100%)**
```

### 6. Show failures (if any)

For any failed assertion (with-skill runs and project eval runs), print the details. Skip baseline failures unless `--verbose`.

```
### Failures

**summarize > specific-devto-article > with_skill**
- FAIL: "Comment section contains a code fence with content of 20 words or fewer"
  Evidence: Comment was 21 words, exceeding limit by 1.

**no-ai-attribution > throwaway-commit**
- FAIL: "Commit message has no `Co-Authored-By:` trailer"
  Evidence: Commit ended with `Co-Authored-By: Claude <noreply@anthropic.com>`.
```

If `--verbose`, also print passing assertions with their evidence.

### 7. Print workspace path

```
Full results: tmp/evals/2026-04-03T14-30-00/
```

### 8. Clean up artifact documents

Delete any files created under `docs/` during this eval run. Skills like `scope` may produce spec documents there as part of their normal output. These are eval artifacts, not real project docs, and should not be committed.

Also honor the `cleanup` glob field on each eval case (skill or project) and delete any matching files. Project evals like `no-ai-attribution` use this to remove throwaway repos under `tmp/*-fake-repo`.

List each deleted file so the user can see what was removed. If nothing matched, skip silently.
