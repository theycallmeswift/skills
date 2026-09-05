# writing-prompts — eval record

Recorded 2026-09-04 from `iteration_23`, `iteration_24` (benchspec 0.0.1, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet). Re-run with `make evals SKILL=writing-prompts`.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| code-review-subagent | 8/9 (88%) | 9/9 (100%) | +12pp |
| contradictory-financial-filings | 8/9 (88%) | 9/9 (100%) | +12pp |
| onboarding-context-doc | 2/9 (22%) | 9/9 (100%) | +78pp |
| vague-triage-intent | 2/9, 2/9, 2/9 (22%) | 8/9, 3/9, 3/9 (51%) | +29pp |
| **All (pooled)** | 24/54 (44%) | 41/54 (75%) | +31pp |

## Routing evals — trial arm: 9/10

| Query | Expected | Result |
|---|---|---|
| clean-slash-command | writing-prompts invoked | pass |
| database-schema-saas | writing-prompts not invoked | pass |
| draft-slack-launch | writing-prompts not invoked | pass |
| draft-system-prompt | writing-prompts invoked | pass |
| fix-typeerror | writing-prompts not invoked | pass |
| security-review-pr | writing-prompts not invoked | pass |
| tighten-prompt | writing-prompts invoked | pass |
| trim-claude-md | writing-prompts invoked | pass |
| write-agents-md | writing-prompts invoked | pass |
| writing-tests-doc | writing-prompts invoked | **fail** |

## Notes

**`vague-triage-intent` is the ask-or-draft fork.** The eval permits either scoping questions or a draft that states its assumptions, but every draft-shaped assertion (role, delimiters, output shape, editorial pass) fails when the agent takes the ask-first path. The 3× re-sample above shows how often each path is taken; the skill's own workflow says to ask when the ask is vague, so a low trial rate here is the eval penalizing behaviour the skill prescribes, not the skill regressing. Tightening the eval so the ask path is graded on its own terms is a follow-up.

**Routing: `writing-tests-doc` misses on sonnet.** "I need a docs/style/writing-tests.md for our team's pytest conventions" routes on opus and haiku but not sonnet — the upstream suite recorded the same `fails-on [sonnet]` boundary.

**Ten upstream queries live under `writing-agent-skills`.** The upstream suite listed nine build/fix/scaffold/eval/restructure/advice asks as negatives here and one overlap positive ("draft the SKILL.md for a `pr-review` skill"). All ten are asks that should route to `writing-agent-skills`, and a routing query lives once, under the skill it should reach, so they sit in `evals/writing-agent-skills/triggers/` and are measured there with both skills loaded. With this skill alone their outcome is situational (in one run two of the build asks fired `writing-prompts`; in another none did, for reasons unrelated to the boundary), which is why they are not recorded here.
