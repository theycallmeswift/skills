# interview-me — eval record

Recorded 2026-09-04 from `iteration_17`, `iteration_18` (harnessbench 0.0.1, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet). Re-run with `make evals SKILL=interview-me`.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| catch-all-pose | 3/5, 3/5, 3/5 (60%) | 5/5, 3/5, 3/5 (73%) | +13pp |
| catch-all-reopen | 3/3 (100%) | 3/3 (100%) | +0pp |
| catch-all-skip | 4/5 (80%) | 5/5 (100%) | +20pp |
| interview-ambiguous-mode | 4/5 (80%) | 5/5 (100%) | +20pp |
| interview-handoff-to-spec | 5/6 (83%) | 6/6 (100%) | +17pp |
| interview-manual-stop | 5/6 (83%) | 6/6 (100%) | +17pp |
| **All (pooled)** | 30/40 (75%) | 36/40 (90%) | +15pp |

## Routing evals — trial arm: 20/20

| Query | Expected | Result |
|---|---|---|
| brainstorm-approaches | not invoked | pass |
| brainstorm-feature | not invoked | pass |
| goal-bounded | invoked | pass |
| grill-legacy | invoked | pass |
| grill-resolve | invoked | pass |
| interview-idea | invoked | pass |
| interview-notes-summary | not invoked | pass |
| interview-until-stop | invoked | pass |
| interview-until-to-spec | invoked | pass |
| job-interview-prep | not invoked | pass |
| keep-grilling-handoff | invoked | pass |
| relentless-questions | invoked | pass |
| scope-before-spec | invoked | pass |
| stress-test-design | invoked | pass |
| to-spec-prd | not invoked | pass |
| to-spec-spec-out | not invoked | pass |
| to-spec-writeup | not invoked | pass |
| writing-plans-impl | not invoked | pass |
| writing-prompts-tighten | not invoked | pass |
| writing-prompts-wordsmith | not invoked | pass |

## Notes

**Baselines run high by construction.** Five of the six scenarios are continuations: the scripted `history:` already shows an interview in progress, one question per turn with a table, so a bare agent keeps the pattern going and scores well on format. The deltas are therefore small, and the skill's value shows up where the stop condition matters — converging on "stop", announcing the handoff without invoking `to-spec`, asking about the stop mode before any design question — which is exactly where trial reaches 100% and baseline drops a line.

**`catch-all-pose` is the one soft spot.** Once the stated goal is resolved, the skill should pose exactly one open, prose-only "anything we haven't covered?" catch-all. The miss is the agent asking one more scoped question with an options table instead — the §5 rule losing to the §3 every-decision-gets-a-visual habit. The 3× re-sample above shows how often. A tuning pass should make the catch-all's "open prose, no table" carve-out harder to miss in the body.

**No refusals on multi-turn context.** Unlike the `writing-agent-skills` commit-message scenario, none of the five `history:`-driven scenarios triggered the fabricated-transcript refusal harnessbench's inline rendering can provoke; the recaps here are dialogue the agent is asked to continue, not an approval it is asked to trust.

**Routing: 20/20 on sonnet.** Every "interview me / grill me / stress-test" positive fires, and the near-miss negatives — `to-spec` write-ups, brainstorming, prompt tightening, implementation plans, job-interview prep — all stay quiet with the full plugin loaded.
