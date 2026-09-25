# interview-me — eval record

Recorded 2026-09-18 from `iteration_10` (benchspec 0.0.4, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet, `--count 3`). Re-run with `make evals SKILL=interview-me EVAL_ARGS="--count 3"`. Activation lines (`Skill … invoked`) are scoped off baseline and excluded from these tallies.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| catch-all-pose | 8/12 (67%) | 10/12 (83%) | +16pp |
| catch-all-reopen | 6/6 (100%) | 6/6 (100%) | +0pp |
| catch-all-skip | 9/12 (75%) | 12/12 (100%) | +25pp |
| interview-ambiguous-mode | 9/12 (75%) | 12/12 (100%) | +25pp |
| interview-handoff-to-spec | 10/15 (67%) | 15/15 (100%) | +33pp |
| interview-manual-stop | 10/15 (67%) | 15/15 (100%) | +33pp |
| **All (pooled)** | 52/72 (72%) | 70/72 (97%) | +25pp |

## Routing evals — trial arm: 5/6 at 3/3, 1 at 2/3 (of the queries still in the suite)

| Query | Expected | Result |
|---|---|---|
| brainstorm-feature | interview-me not invoked | pass |
| job-interview-prep | interview-me not invoked | pass |
| grill-legacy | interview-me invoked | 2/3 |
| interview-until-to-spec | interview-me invoked | pass |
| relentless-questions | interview-me invoked | pass |
| scope-before-spec | interview-me invoked | pass |

## Notes

**Baselines run high by construction.** Five of the six scenarios are continuations: the scripted `history:` already shows an interview in progress, one question per turn with a table, so a bare agent keeps the pattern going and scores well on format. The skill's value shows up where the stop condition matters — converging on "stop", announcing the handoff without invoking `to-spec`, asking about the stop mode before any design question — which is exactly where trial reaches 100% and baseline drops a line.

**`catch-all-pose`: improved, still noisy.** 2 of 3 samples clean here, 6 of 6 across two runs of a near-identical draft; control on the prior text 1 of 3. §3 now says an answered decision is settled and grilling stops at the gate. The scenario's goal reads "help me decide": under "stress-test that one call", probing once more is arguably right, so it could not isolate catch-all timing. The failing sample opens an adjacent branch (delayed jobs, retries) instead.

**No refusals on multi-turn context.** None of the five `history:`-driven scenarios triggered the fabricated-transcript refusal benchspec's inline rendering can provoke; these recaps are dialogue the agent is asked to continue, not an approval it is asked to trust.

**Routing: description unchanged.** `grill-legacy` and `to-spec-spec-out` each missed one sample; the control also missed `to-spec-spec-out` once. Near-misses (brainstorming, prompt tightening, implementation plans, job-interview prep, interview-note summaries, `to-spec` write-ups) otherwise stay quiet with the full plugin loaded.

**Pruned 2026-09-24.** Routing sets are capped at 10 queries per skill, each needing a distinct reason to exist. Every removed positive already said "interview me" or "grill me" (goal-bounded, grill-resolve, interview-idea, interview-until-stop, keep-grilling-handoff, stress-test-design). Stop-mode selection is graded by `interview-ambiguous-mode`, not by routing. Also removed: `brainstorm-approaches` (duplicates `brainstorm-feature`), `interview-notes-summary` (same keyword trap as `job-interview-prep`), and `writing-prompts-wordsmith` (no shared vocabulary). `to-spec-spec-out`, `to-spec-writeup`, and `writing-plans-impl` duplicated `to-spec` queries. They now live as `interview-me not invoked` lines on `to-spec/triggers/spec-this-out` and `to-spec/not-triggers/impl-plan`, alongside the existing line on `to-spec/triggers/prd-migration`.
