# catch-me-up — eval record

Recorded 2026-09-24. Output evals from `iteration_13`; routing from `iteration_09`. Both used benchspec 0.0.5 with Claude Code in the guest and sonnet at `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=catch-me-up EVAL_ARGS='-k "not triggers" --count 3 -n 4'` for output and `make evals SKILL=catch-me-up EVAL_ARGS='-k "triggers and trial" --count 3 -n 4'` for routing. Activation lines (`Skill … invoked`) are scoped off baseline and excluded from these tallies; the skill fired in 15 of 15 trial output cells.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| stale-state | 15/48 (31%) | 48/48 (100%) | +69pp |
| invented-artifacts | 3/12 (25%) | 12/12 (100%) | +75pp |
| compaction-honesty | 6/9 (67%) | 9/9 (100%) | +33pp |
| empty-ownership | 8/12 (67%) | 9/12 (75%) | +8pp |
| no-repo-session | 12/12 (100%) | 12/12 (100%) | +0pp |
| **Headline** (mean of per-sample rates) | **58%** | **95%** | **+37pp** (noise band ±5pp) |

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

**What the skill fixes.**
- **PR and CI state.** A bare agent checks `git` but rarely asks `gh`. Here it never did (0 of 3), so it never found PR #48 or its failing `ty` check, or named the branch. Across earlier runs its `gh` use swung from 1 to 4 of 5 with nothing changed.
- **Claimed files.** It repeats the transcript's claim that `./docs/idempotency.md` was written, without looking (0 of 3).
- **Truncated context.** It never says the conversation it was handed starts partway through (0 of 3).
- **Recap shape.** It never uses the recap shape.

With the skill, every one of these holds in 3 of 3.

**`empty-ownership` is still the weak spot.** Two trial replies say plainly that nothing is waiting on the user. The third puts "run the suite yourself" in **You:** because it couldn't re-run the tests. The skill says unverified claims are not tasks for the user, and the rule usually holds, but not always.

This scenario also needed a fixture fix. Its migration used to carry a 24h `expires_at` column the transcript never discussed, and trial agents raised it as "confirm the TTL is intentional". The column contradicted the scenario's premise that nothing is waiting on the user, so it was removed. The scenarios whose transcripts discuss the TTL keep it.

**Grades were audited.** A separate agent re-graded every assertion in the previous recorded run against the replies. It confirmed all routing, activation and `gh` checks. It found two wrong grades, both baseline passes on the missing-context assertion, where the reply only said the agent had no memory of its own. The assertion now names that as not counting, which is why `compaction-honesty` shows lift here where the previous run showed none.

**`compaction-honesty` depends on the TL;DR template.** The missing-context flag was unreliable until the template made it the TL;DR's opening clause ("Earlier context is missing — this picks up at …").

**Narration is not graded.** Replies often open with a line about what the checks found ("Both files check out.") before the TL;DR. That is harmless and deliberately not asserted. In a session with no repository, saying there is nothing to check is fine; only invented branch, PR, or CI state fails.

**Fixtures plant exactly one discrepancy each.** Earlier runs were confounded by accidental ones — no test files behind a "214 tests" claim, a `NOT NULL` column the insert never wrote, a sweep on the wrong column, an undiscussed TTL. A verifying agent flagged these every time. They were removed so each scenario measures what it names.

**History is a pasted transcript.** benchspec renders `history:` as a `<transcript>` block ahead of the prompt, not as the agent's own prior turns. The scenarios therefore measure "recap a transcript you were handed", which likely makes a bare agent somewhat more skeptical than it would be of its own memory.
