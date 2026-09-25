# writing-prompts — eval record

Recorded 2026-09-18 from `iteration_05` (benchspec 0.0.4, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet, `--count 3`). Re-run with `make evals SKILL=writing-prompts EVAL_ARGS="--count 3"`.

## Output evals — baseline vs trial

Tallies exclude skill-activation lines (scoped off baseline since 0.0.4), so they don't compare 1:1 with earlier records.

| Eval | baseline | trial | Δ |
|---|---|---|---|
| code-review-subagent | 20/24 (83%) | 24/24 (100%) | +17pp |
| contradictory-financial-filings | 18/24 (75%) | 24/24 (100%) | +25pp |
| vague-triage-answered | 4/21 (19%) | 21/21 (100%) | +81pp |
| vague-triage-intent | 4/6 (67%) | 6/6 (100%) | +33pp |
| **All (pooled)** | 46/75 (61%) | 75/75 (100%) | +39pp |

## Routing evals — trial arm: 20/21 (of the queries still in the suite)

| Query | Expected | Result |
|---|---|---|
| clean-slash-command | writing-prompts invoked | 3/3 |
| draft-slack-launch | writing-prompts not invoked | 3/3 |
| draft-system-prompt | writing-prompts invoked | 3/3 |
| oncall-runbook | writing-prompts not invoked | 3/3 |
| tighten-prompt | writing-prompts invoked | 3/3 |
| trim-claude-md | writing-prompts invoked | 3/3 |
| writing-tests-doc | writing-prompts invoked | **2/3** |

`writing-agent-skills` not invoked held on every query.

## Notes

**`vague-triage-intent` needed a body fix.** Before it, 1 of 3 trial samples drafted on the vague ask with assumed defaults. Workflow step 1 now says to ask and end the turn when input, output shape, or consumer is undefined, and step 6's closing artifact applies only once a draft exists.

**Routing: `writing-tests-doc` is a sonnet model-tier boundary.** Every miss skipped skills entirely and wrote the file directly; the same description scored 0/3 and 2/3 across runs, so treat it as sonnet variance. General reference-doc wording in the description scored 0/3 and was reverted.

**Pruned 2026-09-24.** Routing sets are capped at 10 queries per skill, each needing a distinct reason to exist. Removed `onboarding-context-doc`, which scored 24/24 on both arms and so couldn't catch a regression. Removed `write-agents-md`, which is covered by `agents-md-for-codex` and `trim-claude-md`. Removed three negatives with no shared vocabulary (`database-schema-saas`, `fix-typeerror`, `security-review-pr`). `draft-slack-launch` keeps its `writing-prompts` line but loses the `writing-agent-skills` one, which had nothing to test.
