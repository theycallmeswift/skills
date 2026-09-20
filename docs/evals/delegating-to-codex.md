# delegating-to-codex — eval record

Recorded 2026-09-18 from `iteration_13` (benchspec 0.0.4, Claude Code 2.1.277, sonnet, `--count 3`; baseline bare, trial with the plugin via `--plugin-dir`). The shared `writing-prompts` query comes from `iteration_09`. Re-run with `make evals SKILL=delegating-to-codex EVAL_ARGS="--count 3"`.

The VM has no Codex, so each scenario ships a scripted fake `codex` (shared helpers in `evals/support/fake-codex/`). Assertions grade what the fake logged: the flags passed, the prompt sent, and the commits made. Real-CLI drift is covered by `make test:e2e`.

## Output evals (activation lines excluded)

| Eval | baseline | trial | Δ |
|---|---|---|---|
| plan-implement-task | 16/24 (67%) | 24/24 (100%) | +33pp |
| user-review-presents | 16/27 (59%) | 26/27 (96%) | +37pp |
| plan-review-judges-findings | 18/27 (67%) | 26/27 (96%) | +29pp |
| codex-logged-out | 6/9 (67%) | 9/9 (100%) | +33pp |
| **All** | 56/87 (64%) | 85/87 (98%) | **+34pp** |

Both trial misses are one-sample wording slips in the final message (asked "apply these?" rather than "which?"; explained the dismissed finding only earlier in the turn). Trial costs about 37s and 436k tokens per sample, against 23s and 198k for the baseline.

## Routing (trial, 3/3 each)

| Query | Boundary | Expected |
|---|---|---|
| have-codex-review | user names Codex | invoked |
| continue-plan-codex-task | plan assigns Codex; the ask doesn't name it | invoked |
| send-findings-back | follow-up into an existing Codex job | invoked |
| codex-job-status | checking a running job | invoked |
| review-my-branch | same ask, Codex not named | not invoked |
| review-codex-pr | Codex wrote it; review it yourself | not invoked |
| codex-eperm-debug | debugging Codex itself | not invoked |
| gemini-review | a different model | not invoked |
| writing-prompts/agents-md-for-codex | editing context Codex reads | writing-prompts invoked, this skill not |

## What the baseline misses

A bare agent gets the outcome mostly right: it calls Codex, passes the named risks, fixes real findings, and commits. What it skips is what makes delegation safe and cheap:
- It uses deprecated `--full-auto` instead of `--sandbox` (6 of 12 baseline runs).
- It sets no reasoning effort, so the user's default decides.
- It runs reviews writable and without `--output-schema`.
- It repeats Codex's test claim without re-running the tests.
- When logged out, it calls `codex exec` anyway.

No baseline run found or used the skill's script from the read-only `/project` mount.
