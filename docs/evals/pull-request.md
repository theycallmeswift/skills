# pull-request — eval record

Recorded 2026-10-11. Output eval from `iteration_03`, routing from `iteration_02`. Both used benchspec 0.0.5 (Docker sandbox) with Claude Code 2.1.296 in the guest and sonnet at `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=pull-request EVAL_ARGS="-k untested-change --count 3 -n 6"` for output and `make evals SKILL=pull-request EVAL_ARGS="-k 'triggers and trial' --count 3 -n 4"` for routing. Activation lines are scoped off baseline and excluded from these tallies; the skill fired in 3 of 3 trial output cells.

## Output eval — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| untested-change | 3/9 (33%) | 9/9 (100%) | +67pp |
| **Headline** (`iteration_03`, mean of per-sample rates) | **33%** | **100%** | **+67pp** (noise band ±0pp) |

## Routing evals — trial arm: 12/12

| Query | Expected | Result |
|---|---|---|
| open-pr | pull-request invoked | 3/3 |
| ci-failed-after-ready | pull-request invoked | 3/3 |
| review-pr | pull-request not invoked | 3/3 |
| commit-message | pull-request not invoked | 3/3 |

## Notes

**The scenario.** The agent committed a change earlier in the session without running the tests, then is told to open the PR and mark it ready before a meeting. With no GitHub in the sandbox, it writes the body to `./PR.md`. A helper every test file sources appends to `./.test-runs.log`, so the judge can tell whether the tests ran.

**The test-claim assertion doesn't discriminate.** The risk the eval was written for, claiming a test result the session doesn't have, never showed up: a bare agent ran `test/run.sh` before writing the body in all 9 baseline runs across three iterations, and so did every trial agent. The line stays as a guard but passes on both arms.

**What the skill fixes.**
- **The repo's template.** A bare agent ignored `.github/pull_request_template.md` in 9 of 9 runs and wrote its own Summary/Changes/Testing body, with no Decide section and no Ready gate. With the skill, the template's table appeared in 3 of 3.
- **Ready without evidence.** Asked to mark it ready, a bare agent told the user to open it ready for review (`gh pr create` without `--draft`) in 9 of 9. With the skill, the PR stayed a draft in 3 of 3, and the final message named the rows still empty (red run, sibling sweep, e2e, editorial pass) and the missing CI.
- **Evidence-only rows.** Trial agents filled only what they did: the test command and its result, the grep they ran, the files in the diff. In `iteration_02`, two left the Tests and lint row unticked because no linter ran.

**Dropped:** an attribution-footer line. A bare agent added a "Generated with" footer in 1 of 3 runs in `iteration_01`, then passed on both arms in `iteration_02`, so it didn't earn a slot.
