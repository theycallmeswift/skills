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

**Pruned 2026-09-24** (routing cap: 10). Cut `onboarding-context-doc` (24/24 on both arms), `write-agents-md` (covered by `agents-md-for-codex` and `trim-claude-md`), and three unrelated negatives (`database-schema-saas`, `fix-typeerror`, `security-review-pr`). `draft-slack-launch` dropped its `writing-agent-skills` line, which tested nothing.

**Description cut under 1024 chars, 2026-09-30.** The description was 1118 chars; claude.ai's marketplace sync truncates at 1024, dropping the exclusions. Trimmed to 1013 by cutting the editorial-pass sentence and tightening the exclusions tail; the front half is unchanged. A first cut to 960 that also compressed the front half ("API system prompts", "SKILL.md description and body text", dropped "phrases like") routed `writing-tests-doc` 1/9 against 4/5 for the old text, so it was reverted. Same-day, same-harness A/B on `writing-tests-doc` (trial arm, sonnet): old 11/15, final 7/13. Every other routing query held 3/3; `agents-md-for-codex` (3/3) now counts too, and `writing-agent-skills`' `skill-name-choice` and `todo-list-skill-or-claude-md` held 3/3 with writing-prompts not invoked. Treat the front half of this description as load-bearing for the `docs/*.md` boundary.
