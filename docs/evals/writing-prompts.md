# writing-prompts — eval record

Recorded 2026-09-04 from `iteration_11`, `iteration_12` (harnessbench 0.0.1, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet). Re-run with `make evals SKILL=writing-prompts`.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| code-review-subagent | 7/9 (77%) | 9/9 (100%) | +23pp |
| contradictory-financial-filings | 4/9 (44%) | 9/9 (100%) | +56pp |
| onboarding-context-doc | 9/9 (100%) | 9/9 (100%) | +0pp |
| vague-triage-intent | 2/9, 4/9, 2/9 (29%) | 3/9, 9/9, 2/9 (51%) | +22pp |
| **All (pooled)** | 28/54 (51%) | 41/54 (75%) | +24pp |

## Routing evals — trial arm: 9/10

| Query | Expected | Result |
|---|---|---|
| clean-slash-command | invoked | pass |
| database-schema-saas | not invoked | pass |
| draft-slack-launch | not invoked | pass |
| draft-system-prompt | invoked | pass |
| fix-typeerror | not invoked | pass |
| security-review-pr | not invoked | pass |
| tighten-prompt | invoked | pass |
| trim-claude-md | invoked | pass |
| write-agents-md | invoked | pass |
| writing-tests-doc | invoked | **fail** |

## Notes

**`vague-triage-intent` is the ask-or-draft fork.** The eval permits either scoping questions or a draft that states its assumptions, but every draft-shaped assertion (role, delimiters, output shape, editorial pass) fails when the agent takes the ask-first path. The 3× re-sample above shows how often each path is taken; the skill's own workflow says to ask when the ask is vague, so a low trial rate here is the eval penalizing behaviour the skill prescribes, not the skill regressing. Tightening the eval so the ask path is graded on its own terms is a follow-up.

**Routing: `writing-tests-doc` misses on sonnet.** "I need a docs/style/writing-tests.md for our team's pytest conventions" routes on opus and haiku but not sonnet — the upstream suite recorded the same `fails-on [sonnet]` boundary.

**Ten queries deferred to the `writing-agent-skills` PR.** The upstream suite had twenty queries: seven positives, four unrelated near-misses, and nine negatives that are really guards for `writing-agent-skills` — build/fix/scaffold-a-skill asks, eval setup, restructuring a long body, and two skill-or-CLAUDE.md advice questions. A guard for a collision is only measurable with both skills loaded. With this skill alone the outcome is situational: in an earlier install-only run two of the build asks fired `writing-prompts` and wrote a full SKILL.md through it; in the plugin-loaded run none did, because the agent stopped to ask where to put the skill, could not find the skill it was asked to fix, or scaffolded a stub with the description blank. A pass on "not invoked" here is luck, not a boundary. The nine guards, plus `draft-pr-review-skill-md` — the overlap positive both descriptions claim, which fires here alone and routes to `writing-agent-skills` once it is present — land with that skill and are recorded there. This suite keeps the six positives and four near-misses that measure this description on its own.
