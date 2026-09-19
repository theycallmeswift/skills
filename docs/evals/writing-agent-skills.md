# writing-agent-skills — eval record

Recorded 2026-09-18 from `iteration_06` (benchspec 0.0.4, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet, `--count 3`). Re-run with `make evals SKILL=writing-agent-skills EVAL_ARGS="--count 3"`.

Activation lines (`` Skill `…` invoked ``) are scoped off baseline and excluded from the output tallies, so these rates don't compare 1:1 with the 2026-09-04 record.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| build-commit-message-skill | 9/21 (43%) | 20/21 (95%) | +52pp |
| db-migrate-internals-trap | 4/15 (27%) | 5/15 (33%) | +7pp |
| improve-changelog-skill | 14/15 (93%) | 15/15 (100%) | +7pp |
| react-conventions-trap | 0/12 (0%) | 12/12 (100%) | +100pp |
| **All (pooled)** | 27/63 (42%) | 52/63 (82%) | +40pp |

Pooled sums assertions; `benchmark.md`'s headline averages per-eval rates.

## Routing evals — trial arm: 14/15

| Query | Expected | Result |
|---|---|---|
| bootstrap-pass-rate | writing-agent-skills invoked | pass |
| build-commit-skill | writing-agent-skills invoked | pass |
| build-recipe-format-skill | writing-agent-skills invoked | pass |
| draft-pr-review-skill-md | writing-agent-skills invoked | pass |
| expand-git-workflow-trigger | writing-agent-skills invoked | pass |
| fix-archive-description | writing-agent-skills invoked | pass |
| regression-test-ingest | writing-agent-skills invoked | pass |
| rerun-evals-haiku | writing-agent-skills invoked | pass |
| run-archive-evals | writing-agent-skills invoked | pass |
| run-trigger-evals-ingest | writing-agent-skills invoked | pass |
| scaffold-notion-sync | writing-agent-skills invoked | pass |
| setup-changelog-evals | writing-agent-skills invoked | pass |
| skill-name-choice | writing-agent-skills invoked · writing-prompts not invoked | pass |
| split-wiki-skill | writing-agent-skills invoked | pass |
| todo-list-skill-or-claude-md | writing-agent-skills invoked · writing-prompts not invoked | **fail** (0/3) |

## Notes

**`writing-prompts` holds where the skill writes a SKILL.md.** The unchanged body passes the process line 9/9 across build-commit, improve-changelog, and react-conventions-trap at n=3; consolidating the repeated mandates into one §5 step dropped it to 4/9, so the repetition stays. It is still 0/9 on `db-migrate-internals-trap` (see below).

**Skill names: noun form in 1 of 3.** `build-commit-message-skill`'s name line misses in one sample (`commit-message`). An inline verb/gerund rule in §2 had no measured effect and was not kept. Open gap.

**`db-migrate-internals-trap` often stops at clarifying questions.** Samples flag the cross-skill import but end on questions instead of a design or eval plan, missing the artifact and `writing-prompts` lines. High variance: a trial re-sample scored 7/15, a control on the prior description 8/15.

**`react-conventions-followthrough` removed.** Once the user agrees conventions aren't a skill, loading the skill would be wrong, so its activation line rewarded a mistake; bare agents already write the doc (6/6). `react-conventions-trap` still grades the pushback.

**Routing.** The description now claims deciding whether something should be a skill, and naming one; `skill-name-choice` went from 0/3 on the prior description to 3/3. "Do I need a skill for my todo list, or just CLAUDE.md?" stays 0/3 across every wording tried, with `writing-prompts` correctly quiet; recorded as a sonnet boundary.
