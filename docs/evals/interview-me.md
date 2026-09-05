# interview-me — eval record

Recorded 2026-09-04 from `iteration_30`, `iteration_32` (benchspec 0.0.1, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet). Re-run with `make evals SKILL=interview-me`.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| catch-all-pose | 3/5, 3/5, 3/5 (60%) | 3/5, 3/5, 3/5 (60%) | +0pp |
| catch-all-reopen | 3/3 (100%) | 3/3 (100%) | +0pp |
| catch-all-skip | 4/5 (80%) | 5/5 (100%) | +20pp |
| interview-ambiguous-mode | 3/5 (60%) | 5/5 (100%) | +40pp |
| interview-handoff-to-spec | 5/6 (83%) | 6/6 (100%) | +17pp |
| interview-manual-stop | 5/6 (83%) | 6/6 (100%) | +17pp |
| **All (pooled)** | 29/40 (72%) | 34/40 (85%) | +13pp |

## Routing evals — trial arm: 18/18

| Query | Expected | Result |
|---|---|---|
| brainstorm-approaches | interview-me not invoked | pass |
| brainstorm-feature | interview-me not invoked | pass |
| interview-notes-summary | interview-me not invoked | pass |
| job-interview-prep | interview-me not invoked | pass |
| to-spec-spec-out | interview-me not invoked | pass |
| to-spec-writeup | interview-me not invoked | pass |
| writing-plans-impl | interview-me not invoked | pass |
| writing-prompts-wordsmith | interview-me not invoked | pass |
| goal-bounded | interview-me invoked | pass |
| grill-legacy | interview-me invoked | pass |
| grill-resolve | interview-me invoked | pass |
| interview-idea | interview-me invoked | pass |
| interview-until-stop | interview-me invoked | pass |
| interview-until-to-spec | interview-me invoked | pass |
| keep-grilling-handoff | interview-me invoked | pass |
| relentless-questions | interview-me invoked | pass |
| scope-before-spec | interview-me invoked | pass |
| stress-test-design | interview-me invoked | pass |

## Notes

**Baselines run high by construction.** Five of the six scenarios are continuations: the scripted `history:` already shows an interview in progress, one question per turn with a table, so a bare agent keeps the pattern going and scores well on format. The deltas are therefore modest, and the skill's value shows up where the stop condition matters — converging on "stop", announcing the handoff without invoking `to-spec`, asking about the stop mode before any design question — which is exactly where trial reaches 100% and baseline drops a line.

**`catch-all-pose` is the one soft spot.** Once the stated goal is resolved, the skill should pose exactly one open, prose-only "anything we haven't covered?" catch-all. The suite pass got it right (5/5); all three re-samples asked one more scoped question with an options table instead (3/5) — the §3 every-decision-gets-a-visual habit winning over the §5 carve-out, one clean sample in four. A tuning pass should make the catch-all's "open prose, no table" rule harder to miss in the body.

**No refusals on multi-turn context.** None of the five `history:`-driven scenarios triggered the fabricated-transcript refusal benchspec's inline rendering can provoke; these recaps are dialogue the agent is asked to continue, not an approval it is asked to trust.

**Routing: 18/18 of its own, and both shared queries hold.** Every "interview me / grill me / stress-test" positive fires; the near-misses — brainstorming, prompt tightening, implementation plans, job-interview prep, summarizing interview notes, the `to-spec` write-ups — all stay quiet with the full plugin loaded. Two upstream near-misses live under `to-spec` because that skill owns them ("turn this into a PRD" routes to `to-spec`, "tighten this prompt so it triggers reliably" to neither); both carry this skill's "not invoked" line and pass.
