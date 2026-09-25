# catch-me-up — eval record

Recorded 2026-09-24. Output evals from `iteration_11`; routing from `iteration_09`. Both used benchspec 0.0.5 with Claude Code in the guest and sonnet at `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=catch-me-up EVAL_ARGS='-k "not triggers" --count 3 -n 4'` for output and `make evals SKILL=catch-me-up EVAL_ARGS='-k "triggers and trial" --count 3 -n 4'` for routing. Activation lines (`Skill … invoked`) are scoped off baseline and excluded from these tallies; the skill fired in 15 of 15 trial output cells.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| stale-state | 15/48 (31%) | 48/48 (100%) | +69pp |
| invented-artifacts | 3/12 (25%) | 12/12 (100%) | +75pp |
| compaction-honesty | 6/9 (67%) | 8/9 (89%) | +22pp |
| empty-ownership | 8/12 (67%) | 6/12 (50%) | −17pp |
| no-repo-session | 12/12 (100%) | 12/12 (100%) | +0pp |
| **Headline** (mean of per-sample rates) | **58%** | **88%** | **+30pp** (noise band ±6pp) |

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

## Notes

**What the skill fixes.** A bare agent checks `git` but rarely asks `gh`: it found PR #48 and its failing `ty` check in 0 of 3 samples here, and tool use varies widely between runs, from 1 to 4 of 5 in earlier runs. The bare agent also repeats the transcript's claim that `./docs/idempotency.md` was written without looking (0 of 3), and never uses the recap shape. With the skill all three go to 3 of 3.

**`empty-ownership` is the weak spot.** In two of three trial samples the **You:** slot asked the user to "confirm the 24h `expires_at` TTL is intentional". The skill names "confirm this is intentional" questions as not belonging there, but the rule does not hold reliably: across four trial runs, **You:** came out clean in 1 to 3 samples of 3. There is a fixture contribution too: this scenario's migration carries a TTL column its transcript never mentions, so a verifying agent sees undiscussed scope.

**`compaction-honesty` depends on the TL;DR template.** The missing-context flag was unreliable (8 of 13 replies over three runs) until the template made it the TL;DR's opening clause. It now holds in 2 or 3 samples of 3. When it misses, the reply leads with environment caveats ("no git repo here") instead.

**Narration is not graded.** Replies often open with a line about what the checks found ("Both files check out.") before the TL;DR. That is harmless and deliberately not asserted. In a session with no repository, saying there is nothing to check is fine; only invented branch, PR, or CI state fails.

**Fixtures plant exactly one discrepancy each.** Earlier runs were confounded by accidental ones — no test files behind a "214 tests" claim, a `NOT NULL` column the insert never wrote, a sweep on the wrong column. A verifying agent flagged these every time. They were removed so each scenario measures what it names.

**History is a pasted transcript.** benchspec renders `history:` as a `<transcript>` block ahead of the prompt, not as the agent's own prior turns. The scenarios therefore measure "recap a transcript you were handed", which likely makes a bare agent somewhat more skeptical than it would be of its own memory.
