# delegate-to-agent — eval record

Recorded 2026-09-21 from `iteration_05` (benchspec 0.0.4, Claude Code 2.1.278, sonnet, `--count 3`; baseline bare, trial with the plugin via `--plugin-dir`). Re-run with `make evals SKILL=delegate-to-agent EVAL_ARGS="--count 3"` and replace this file.

The VM has no Codex, so each scenario ships a scripted fake `codex` (shared helpers in `evals/support/fake-codex/`). Assertions grade what the fake logged: the flags passed, the prompt sent, and the commits made. Real-CLI drift is covered by `make test:e2e`.

**baseline 67% → trial 99% (+33pp)** across 84 cells, noise band ±1pp.

## Output evals (activation lines excluded)

| Eval | baseline | trial |
|---|---|---|
| codex-logged-out | 67% | 100% |
| gate-catches-false-green | 86% | 100% |
| plan-implement-task | 67% | 100% |
| plan-review-judges-findings | 67% | 96% |
| python3-missing | 60% | 100% |
| user-review-presents | 56% | 100% |
| **All** | **67%** | **99%** |

`plan-review-judges-findings`'s 96% is one judged assertion in one sample, where the agent decided the plan's only task was already complete and did no work. Task comprehension, not delegation behaviour.

## Routing (trial, 3/3 each)

All fourteen activation lines pass: four `triggers/`, four `not-triggers/`, and the six output evals' own invocation lines. `not-triggers/review-codex-pr` ("codex wrote this PR, can you review it yourself?") is the one to watch — the description's negative clause names Codex verbatim for it, and generalizing that clause to "the delegate" broke it in an earlier draft.

## What the baseline misses

A bare agent gets the outcome mostly right: it calls Codex, passes the named risks, fixes real findings, and commits. What it skips is what makes delegation safe and cheap:

- It uses deprecated `--full-auto` instead of `--sandbox`.
- It sets no reasoning effort, so the user's default decides.
- It runs reviews writable and without `--output-schema`.
- It repeats the delegate's test claim rather than reporting an independent check.
- When logged out, it calls `codex exec` anyway.

No baseline run found or used the skill's script from the read-only `/project` mount.

## Two limits worth knowing

- **`gate-catches-false-green` grades the outcome, not the mechanism.** Its 86% baseline is high because a bare agent runs the tests itself, finds the failure, and also declines to commit. Discriminating on the mechanism would need the gate to leave a trace inside the workspace, which is a `scripts/` change.
- **Every `The final response …` assertion is judge-backed by construction.** benchspec's checkers (`file_exists`, `regex` over file content, `skill_invoked`, …) are all file- or skill-scoped; none can see the agent's final message. `plan-implement-task` works around this by having the fake claim `pytest` while the project runs `python3 -m unittest -q`, so reporting the gate and parroting the delegate are textually separable.
