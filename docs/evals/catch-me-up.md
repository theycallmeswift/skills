# catch-me-up — eval record

Recorded 2026-09-24. Output evals from `iteration_12`; routing from `iteration_09`. Both used benchspec 0.0.5 with Claude Code in the guest and sonnet at `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=catch-me-up EVAL_ARGS='-k "not triggers" --count 3 -n 4'` for output and `make evals SKILL=catch-me-up EVAL_ARGS='-k "triggers and trial" --count 3 -n 4'` for routing. Activation lines (`Skill … invoked`) are scoped off baseline and excluded from these tallies; the skill fired in 15 of 15 trial output cells.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| stale-state | 20/48 (42%) | 47/48 (98%) | +56pp |
| invented-artifacts | 3/12 (25%) | 11/12 (92%) | +67pp |
| empty-ownership | 9/12 (75%) | 12/12 (100%) | +25pp |
| compaction-honesty | 8/9 (89%) | 8/9 (89%) | +0pp |
| no-repo-session | 12/12 (100%) | 12/12 (100%) | +0pp |
| **Headline** (mean of per-sample rates) | **66%** | **96%** | **+30pp** (noise band ±4pp) |

## Routing evals — trial arm: 30/30

| Query | Expected | Result |
|---|---|---|
| catch-me-up-left-off | catch-me-up invoked | 3/3 |
| back-where-were-we | catch-me-up invoked | 3/3 |
| recap-session-details | catch-me-up invoked | 3/3 |
| blocking-and-on-me | catch-me-up invoked | 3/3 |
| status-branch-my-call | catch-me-up invoked | 3/3 |
| ai-news | catch-me-up not invoked | 3/3 |
| all-repos-standup | catch-me-up not invoked | 3/3 |
| file-changed-yesterday | catch-me-up not invoked | 3/3 |
| last-three-commits | catch-me-up not invoked | 3/3 |
| pr-status | catch-me-up not invoked | 3/3 |

The description has not changed since this routing run.

## Notes

**What the skill fixes.** A bare agent checks `git` but rarely asks `gh`. It found PR #48 and its failing `ty` check in 1 of 3 samples here, and that rate swung from 1 to 4 of 5 across earlier runs with nothing changed. It repeats the transcript's claim that `./docs/idempotency.md` was written without looking (0 of 3), and never uses the recap shape or splits what's yours from what's mine. With the skill, each of these holds in all or all but one sample.

**Trial misses in this run, one each.**
- `compaction-honesty`: one reply led with environment caveats ("no git repo", "python3 not installed") and never said the start of the conversation was missing.
- `invented-artifacts`: one reply caught the missing doc but put writing it behind a question to the user ("nothing queued until you weigh in on the doc") instead of listing it as remaining work.
- `stale-state`: one reply didn't name the branch.

**`compaction-honesty` depends on the TL;DR template.** The missing-context flag was unreliable (8 of 13 trial replies over three runs) until the template made it the TL;DR's opening clause. It has held in 2 of 3 samples in each run since. A bare agent also flags it some of the time (2 of 3 here, 0 to 2 of 5 earlier), which is why this scenario shows no lift.

**`empty-ownership` needed a fixture fix.** Its migration used to carry a 24h `expires_at` column the transcript never discussed. Trial agents raised it as "confirm the TTL is intentional" in the **You:** slot, dropping the scenario to 50% the run before this one. The column was removed because it contradicted the scenario's premise that nothing is waiting on the user; the scenarios whose transcripts discuss the TTL keep it. The underlying habit, turning undiscussed details into questions for the user, may still show up in real sessions.

**Narration is not graded.** Replies often open with a line about what the checks found ("Both files check out.") before the TL;DR. That is harmless and deliberately not asserted. In a session with no repository, saying there is nothing to check is fine; only invented branch, PR, or CI state fails.

**Fixtures plant exactly one discrepancy each.** Earlier runs were confounded by accidental ones — no test files behind a "214 tests" claim, a `NOT NULL` column the insert never wrote, a sweep on the wrong column. A verifying agent flagged these every time. They were removed so each scenario measures what it names.

**History is a pasted transcript.** benchspec renders `history:` as a `<transcript>` block ahead of the prompt, not as the agent's own prior turns. The scenarios therefore measure "recap a transcript you were handed", which likely makes a bare agent somewhat more skeptical than it would be of its own memory.
