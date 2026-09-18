# writing-prompts — eval record

Recorded 2026-09-18 from `iteration_05` (benchspec 0.0.4, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet, `--count 3`). Re-run with `make evals SKILL=writing-prompts EVAL_ARGS="--count 3"`.

## Output evals — baseline vs trial

Tallies exclude skill-activation lines (scoped off baseline since 0.0.4), so they don't compare 1:1 with earlier records.

| Eval | baseline | trial | Δ |
|---|---|---|---|
| code-review-subagent | 20/24 (83%) | 24/24 (100%) | +17pp |
| contradictory-financial-filings | 18/24 (75%) | 24/24 (100%) | +25pp |
| onboarding-context-doc | 24/24 (100%) | 24/24 (100%) | +0pp |
| vague-triage-answered | 4/21 (19%) | 21/21 (100%) | +81pp |
| vague-triage-intent | 4/6 (67%) | 6/6 (100%) | +33pp |
| **All (pooled)** | 70/99 (71%) | 99/99 (100%) | +29pp |

## Routing evals — trial arm: 32/33

| Query | Expected | Result |
|---|---|---|
| clean-slash-command | writing-prompts invoked | 3/3 |
| database-schema-saas | writing-prompts not invoked | 3/3 |
| draft-slack-launch | writing-prompts not invoked | 3/3 |
| draft-system-prompt | writing-prompts invoked | 3/3 |
| fix-typeerror | writing-prompts not invoked | 3/3 |
| oncall-runbook | writing-prompts not invoked | 3/3 |
| security-review-pr | writing-prompts not invoked | 3/3 |
| tighten-prompt | writing-prompts invoked | 3/3 |
| trim-claude-md | writing-prompts invoked | 3/3 |
| write-agents-md | writing-prompts invoked | 3/3 |
| writing-tests-doc | writing-prompts invoked | **2/3** |

`writing-agent-skills` not invoked held on every query.

## Notes

**`vague-triage-intent` needed a body fix.** Before it, 1 of 3 trial samples drafted on the vague ask with assumed defaults. Workflow step 1 now says to ask and end the turn when input, output shape, or consumer is undefined, and step 6's closing artifact applies only once a draft exists.

**Routing: `writing-tests-doc` is a sonnet model-tier boundary.** Every miss skipped skills entirely and wrote the file directly; the same description scored 0/3 and 2/3 across runs, so treat it as sonnet variance. General reference-doc wording in the description scored 0/3 and was reverted.
