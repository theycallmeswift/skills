# mockup — eval record

Recorded 2026-10-11. Baseline and routing from `iteration_02`, trial output from `iteration_03` (after swapping the template's example for an unrelated screen). Both used benchspec 0.0.5 (Docker sandbox) with Claude Code 2.1.296 in the guest and sonnet at `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=mockup EVAL_ARGS="-k leave-confirmation --count 3 -n 6"` for output and `make evals SKILL=mockup EVAL_ARGS="-k 'triggers and trial' --count 3 -n 4"` for routing. Activation lines are scoped off baseline and excluded from these tallies; the skill fired in 3 of 3 trial output cells.

## Output eval — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| leave-confirmation | 6/15 (40%) | 15/15 (100%) | +60pp |
| **Headline** (mean of per-sample rates) | **40%** | **100%** | **+60pp** (noise band ±0pp) |

## Routing evals — trial arm: 15/15

| Query | Expected | Result |
|---|---|---|
| phone-layouts-before-spec | mockup invoked; to-spec, interview-me not invoked | 9/9 |
| clickable-flow-demo | mockup invoked | 3/3 |
| build-settings-screen | mockup not invoked | 3/3 |
| chart-signups | mockup not invoked | 3/3 |

## Notes

**The scenario.** "mock up the leave-confirmation dialog for the challenge screen" in a workspace whose README describes an 80×24 keyboard-only terminal app, plus a stub `src/screens/challenge.ts`.

**What the skill fixes.**
- **One design.** A bare agent drew a single dialog in 6 of 6 runs across `iteration_01` and `iteration_02`, with a list of "design choices" instead of alternatives. With the skill, 3 lettered options in 6 of 6 trial runs.
- **No versioned file.** A bare agent saved nothing (3 of 6) or one flat file such as `docs/leave-dialog-mockup.txt` that the next round would overwrite. With the skill, `docs/mockups/<slug>/mockups/v1/` in 6 of 6.
- **Ends on implementation.** A bare agent closed by offering to implement the dialog once it had the UI library, not by asking for a pick, in 6 of 6. With the skill, every trial run ended by asking which option, or what's wrong or missing. In `iteration_02`, two of three tacked on a second question; the "fold other open points into the options" line fixed that in `iteration_03`.

**Guards that don't discriminate.** The bare agent never touched `challenge.ts` or wrote a spec or issues, so those two lines pass on both arms. The feared failure, barrelling into implementation, showed up only as the closing offer.

**Publishing.** The sandbox has no hosted-page tool and the workspace isn't a git repo; every trial run said so and gave the file path, and none started a local server.

**Template contamination, fixed.** `iteration_02`'s template example was a leave dialog, and trial option A copied it. The example is now a queue screen; `iteration_03` still scored 100% with options drawn from the workspace's README.

**Example run.** [`mockup-example/`](mockup-example/transcript.md) holds one real run's transcript, the v1 page it produced, and phone screenshots in light and dark.
