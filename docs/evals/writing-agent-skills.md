# writing-agent-skills — eval record

Recorded 2026-09-25 from `iteration_01` (benchspec 0.0.5, Claude Code 2.1.263 in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet, `--count 3`). Routing queries run on trial only: their activation lines are scoped off baseline, so a baseline run grades nothing. Re-run with `make evals SKILL=writing-agent-skills EVAL_ARGS="--count 3 -k 'not (triggers and baseline)'"`.

Activation lines (`` Skill `…` invoked ``) are excluded from the output tallies.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| build-commit-message-skill | 0/18 (0%) | 13/18 (72%) | +72pp |
| db-migrate-internals-trap | 0/15 (0%) | 6/15 (40%) | +40pp |
| improve-changelog-skill | 13/15 (87%) | 13/15 (87%) | +0pp |
| react-conventions-trap | 3/12 (25%) | 12/12 (100%) | +75pp |
| **All (pooled)** | 16/60 (27%) | 44/60 (73%) | +46pp |

## Routing evals — trial arm: 8/9 at 3/3

| Query | Expected | Result |
|---|---|---|
| bootstrap-pass-rate | writing-agent-skills invoked | pass |
| build-commit-skill | writing-agent-skills invoked | pass |
| draft-pr-review-skill-md | writing-agent-skills invoked | pass |
| fix-archive-description | writing-agent-skills invoked | pass |
| rerun-evals-haiku | writing-agent-skills invoked | pass |
| setup-changelog-evals | writing-agent-skills invoked | pass |
| skill-name-choice | writing-agent-skills invoked · writing-prompts not invoked | pass |
| split-wiki-skill | writing-agent-skills invoked | pass |
| todo-list-skill-or-claude-md | writing-agent-skills invoked · writing-prompts not invoked | **fail** (0/3 invoked; writing-prompts quiet 3/3) |

Negatives for this skill are the `writing-agent-skills not invoked` lines on `writing-prompts` queries (see that record).

## Notes

**`writing-prompts` step regressed since 2026-09-18.** The `process:` line on `build-commit-message-skill` is 0/3 (it was 9/9 across three evals); every miss wrote the SKILL.md and never called `writing-prompts`. A control on `main`'s unedited SKILL.md with the same eval file scored 1/3, so the drop predates the routing-eval guidance change; its cause is unknown (n=3 on each side can't separate the two rates). Open gap, and the main cause of trial misses here. A first control attempt refused 3/3, calling the scripted `history:` an unverifiable approval — a fragility of this eval's multi-turn setup worth watching.

**`improve-changelog-skill` doesn't discriminate.** Bare agents write the broadened description, trim the body, and keep conventions (13/15 on both arms; 14/15 vs 15/15 last record). Only the `writing-prompts` line separates the arms.

**Pruned 2026-09-24.** Routing capped at 10 queries per skill. Removed rewordings of intents already covered: `run-archive-evals`, `regression-test-ingest`, `run-trigger-evals-ingest` (running evals; `bootstrap-pass-rate` and `rerun-evals-haiku` stay), `build-recipe-format-skill`, `scaffold-notion-sync` (building a skill; `build-commit-skill` and `draft-pr-review-skill-md` stay), `expand-git-workflow-trigger` (description debugging; `fix-archive-description` stays). `build-commit-message-skill` dropped its standalone frontmatter line, which the conventions line already grades.

**Skill names: noun form in 1 of 3.** `build-commit-message-skill`'s name line misses in one sample (`commit-message`). An inline verb/gerund rule in §2 had no measured effect and was not kept. Open gap.

**`db-migrate-internals-trap` often stops at clarifying questions.** Samples flag the cross-skill import but end on questions instead of a design or eval plan, missing the artifact and `writing-prompts` lines. High variance: a trial re-sample scored 7/15, a control on the prior description 8/15.

**`react-conventions-followthrough` removed.** Once the user agrees conventions aren't a skill, loading the skill would be wrong, so its activation line rewarded a mistake; bare agents already write the doc (6/6). `react-conventions-trap` still grades the pushback.

**Routing.** The description now claims deciding whether something should be a skill, and naming one; `skill-name-choice` went from 0/3 on the prior description to 3/3. "Do I need a skill for my todo list, or just CLAUDE.md?" stays 0/3 across every wording tried, with `writing-prompts` correctly quiet; recorded as a sonnet boundary.
