# to-milestone — eval record

Recorded 2026-10-11 from `iteration_06`: benchspec 0.0.5 (Docker sandbox), Claude Code 2.1.296 in the guest, sonnet, `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=to-milestone EVAL_ARGS="--count 3 -n 6"`. Activation lines are scoped off baseline and excluded from these tallies; the skill fired in 3 of 3 trial output cells.

## Output eval — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| csv-export | 13/27 (48%) | 27/27 (100%) | +52pp |
| **Headline** (`iteration_06`, mean of per-sample rates) | **48%** | **100%** | **+52pp** (noise band ±4pp) |

## Routing evals — trial arm: 12/12

| Query | Expected | Result |
|---|---|---|
| spec-to-milestone | to-milestone invoked, to-spec not | 3/3 |
| file-the-issues | to-milestone invoked, claude-cloud-orchestrator not | 3/3 |
| spec-for-milestone | to-milestone not invoked | 3/3 |
| work-through-milestone | to-milestone not invoked | 3/3 |

## Notes

**The scenario.** A merged six-issue spec for a CLI export feature: issue 2 depends on issue 4 (a forward reference), issues 1 and 5 own the same file with no link between them, issue 3 adds `openpyxl`, and issue 6 is a screen. The sandbox has `python3` but no GitHub: `gh` logs every call to `./.fake-gh/calls.log` and fails the way it does offline.

**What the skill fixes.**
- **Closers.** No bare agent added any, in 15 runs across five baseline iterations. With the skill, both closers appeared with the right blockers in 3 of 3.
- **The `lockfile` label.** Never given by a bare agent (0 of 15), even though issue 3 owns `uv.lock`. With the skill, 3 of 3.
- **The mockup gate.** Once the spec stopped saying "approved design" (`iteration_01` leaked it, and a bare agent flagged the missing design from that phrase alone), a bare agent never flagged the screen (0 of 12). With the skill, 3 of 3 held creation until a mockup is approved.
- **A plan to confirm.** A bare agent stopped at "GitHub is unreachable" and asked about the network, listing the issues in dependency order in 1 of 3. Trial agents wrote the plan and bodies, ran the script's dry run, showed its creation order, and asked for a yes.

**Guards that don't discriminate.** A bare agent also noticed the shared file (3 of 3), made no create calls (3 of 3), and added no attribution footer (3 of 3). The lines stay: they are the failures the skill's script exists to prevent once GitHub is reachable.

**Fixed during the run.** In `iteration_04`, one trial agent listed the issues in the table's order instead of the dry run's; the confirm step now says the printed order is creation order, and `iteration_05` and `iteration_06` scored 3 of 3. The live path (stubs, bodies, links by REST id, read-back, back-fill) is covered by the script's unit tests against a fake `gh`, not by this eval.
