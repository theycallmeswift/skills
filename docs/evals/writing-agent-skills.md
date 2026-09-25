# writing-agent-skills — eval record

Recorded 2026-09-25 from `iteration_01` (benchspec 0.0.5, Claude Code 2.1.263 in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet, `--count 3`). Routing queries run trial-only (baseline would grade nothing). Re-run with `make evals SKILL=writing-agent-skills EVAL_ARGS="--count 3 -k 'not (triggers and baseline)'"`.

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

Negatives are the `writing-agent-skills not invoked` lines on writing-prompts queries.

## Notes

**`writing-prompts` step regressed since 2026-09-18.** On `build-commit-message-skill` the agent now writes SKILL.md and skips `writing-prompts` (was 9/9). A/B on 2026-09-25, same runtime, trial only:

| SKILL.md | writing-prompts invoked |
|---|---|
| current | 3/15 |
| pre-#33 "Write first" paragraph | 6/12 |

Suggestive (p≈0.13), not conclusive. #33 reframed the sequencing as a risk ("shaky", "makes the risk certain"), which may read as license to skip. Both arms sit far below 9/9, so most of the drop is runtime (model or Claude Code build), not text. Separately, about 1 in 4 samples on either text distrusts the scripted `history:` ("no evidence any baseline run happened") and skips the workflow or refuses; this eval's multi-turn setup is fragile.

**`improve-changelog-skill` didn't discriminate** (13/15 both arms): bare agents broaden the description and trim the body too. On 2026-09-25 it gained a line for the diagnose table's required artifact, a routing-eval set under the cap. That line fails 6/6 on both arms: the skill fixes the description but never writes or proposes routing evals. Skill gap; stays red until fixed.

**Pruned 2026-09-24** (routing cap: 10). Cut three extra "run the evals" asks, two extra "build a skill" asks, and `expand-git-workflow-trigger` (covered by `fix-archive-description`). `build-commit-message-skill`'s frontmatter check is now its own line only; the conventions line no longer repeats it.

**Skill names: noun form in 1 of 3.** `build-commit-message-skill`'s name line misses in one sample (`commit-message`). An inline verb/gerund rule in §2 had no measured effect and was not kept. Open gap.

**`db-migrate-internals-trap` often stops at clarifying questions.** Samples flag the cross-skill import but end on questions instead of a design or eval plan, missing the artifact and `writing-prompts` lines. High variance: a trial re-sample scored 7/15, a control on the prior description 8/15.

**`react-conventions-followthrough` removed.** Once the user agrees conventions aren't a skill, loading the skill would be wrong, so its activation line rewarded a mistake; bare agents already write the doc (6/6). `react-conventions-trap` still grades the pushback.

**Routing.** The description now claims deciding whether something should be a skill, and naming one; `skill-name-choice` went from 0/3 on the prior description to 3/3. "Do I need a skill for my todo list, or just CLAUDE.md?" stays 0/3 across every wording tried, with `writing-prompts` correctly quiet; recorded as a sonnet boundary.
