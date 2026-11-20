# writing-mlh-reports — eval record

Recorded 2026-11-03 from `iteration_06` through `iteration_08`: benchspec 0.0.5, Docker sandbox, Claude Code 2.1.301 in the guest, sonnet. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=writing-mlh-reports EVAL_ARGS='--count 3 -n 6'` (output and routing together, 18 cells per sample).

The skill was also tested end to end on live MLH data before these evals existed. Four reports (a Snowflake partner report, a 2026 community impact report, an investor growth update and a coding-harness trend report) ran through scope, gather, reconcile, gate, draft and review, and their logs shaped the current text. The offline happy path below checks only the behavior that doesn't need MLH's connectors.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ | note |
|---|---|---|---|---|
| partner-report-gate (`iteration_08`, `--count 3`) | 80% | 93% | +13pp | after a ~30% brevity trim and the live-test fixes (existing-report premise, program year, participants' data) |
| partner-report-gate (`iteration_07`, `--count 3`) | 80% | 87% | +7pp | after the scope step stopped asking a round of questions and the gate ended on one question |
| partner-report-gate (`iteration_06`, `--count 1`) | 80% | 60% | −20pp | the scope step asked "in one round"; single sample |

The baseline already recomputes on attention-check passers and catches the stale figure most of the time, so this eval's headroom is small. The skill's larger gains (the premise check, reconciling across sources, picking the lead before drafting, partner-safe content) show up on live data, which these offline evals can't reach.

## Routing evals (trial arm)

All 8 pass in both `iteration_06` and `iteration_08` (after the trim): the five triggers (partner developer report, fellowship outcomes, B-Corp impact, investor update, coding-agents trend) invoke the skill, and the three near-misses (a quick count, a one-line doc fix, a non-MLH research report) don't.
