# delegating-to-codex — eval record

Recorded 2026-09-18 from `iteration_08` (benchspec 0.0.4, Claude Code 2.1.276 in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet, one sample per cell). The shared `writing-prompts` query comes from `iteration_06`. Re-run with `make evals SKILL=delegating-to-codex`.

The guest has no Codex. Every scenario's `setup.sh` runs `_harness/install.sh`, which puts a fake `codex` on PATH, logs each call's argv and stdin to `./.fake-codex/calls.log`, and logs commits to `./.fake-codex/commits.log`. Most assertions grade those logs deterministically.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| plan-implement-task | 5/9 (56%) | 9/9 (100%) | +44pp |
| user-review-presents | 5/10 (50%) | 10/10 (100%) | +50pp |
| plan-review-judges-findings | 7/10 (70%) | 10/10 (100%) | +30pp |
| codex-logged-out | 2/4 (50%) | 4/4 (100%) | +50pp |
| **All (pooled)** | 19/33 (58%) | 33/33 (100%) | +42pp |

## Routing evals — trial arm: 20/20

| Query | Expected | Result |
|---|---|---|
| codex-adversarial-review | delegating-to-codex invoked | pass |
| codex-background-refactor | delegating-to-codex invoked | pass |
| codex-implement-task | delegating-to-codex invoked | pass |
| codex-job-status | delegating-to-codex invoked | pass |
| codex-second-opinion | delegating-to-codex invoked | pass |
| continue-plan-codex-task | delegating-to-codex invoked | pass |
| delegate-migration | delegating-to-codex invoked | pass |
| have-codex-review | delegating-to-codex invoked | pass |
| other-model-family | delegating-to-codex invoked | pass |
| send-findings-back | delegating-to-codex invoked | pass |
| codex-config-effort | delegating-to-codex not invoked | pass |
| codex-eperm-debug | delegating-to-codex not invoked | pass |
| codex-vs-claude-code | delegating-to-codex not invoked | pass |
| gemini-review | delegating-to-codex not invoked | pass |
| install-codex-cli | delegating-to-codex not invoked | pass |
| port-plugin-to-codex | delegating-to-codex not invoked | pass |
| review-codex-pr | delegating-to-codex not invoked | pass |
| review-my-branch | delegating-to-codex not invoked | pass |
| subagent-implement | delegating-to-codex not invoked | pass |
| writing-prompts/agents-md-for-codex | writing-prompts invoked, delegating-to-codex not invoked | pass |

## Notes

**What the skill adds is mostly flags and discipline, not the outcome.** A bare sonnet already knows `codex exec` exists, passes named risks along, fixes real findings, and commits. It misses the parts that make delegation safe and cheap:
- It uses the deprecated `--full-auto` instead of an explicit `--sandbox`.
- It never sets reasoning effort, so the user's config default decides (`ultra` on Swift's machine).
- It runs reviews in a writable sandbox with no `--output-schema`.
- It reports Codex's test claim as its own, without re-running the tests.

Every miss on the baseline side is one of those, plus the activation line.

**The failure mode is a clean win.** Logged out, the baseline calls `codex exec` anyway and only then learns why it failed. The trial's preflight stops before any call and gives the `codex login` fix.

**`plan-review-judges-findings` runs high on baseline by design.** The Task 3 bug is obvious once you read the code, so a capable agent fixes it unaided. The scenario is a regression guard for the plan-triggered branch: fix the real finding, dismiss the bogus division-by-zero finding with a reason, commit, and don't stop to ask.

**Harness fixes made during authoring, all before this record:**
- The fake Codex fails `exec` when logged out.
- A call with unexpected flags gets the scenario's canned reply rather than a generic one.
- The fake reads stdin only for `-` or when no prompt argument is given, as the real CLI does. Before that fix it hung whenever the baseline passed the prompt as an argument in a backgrounded shell, which dragged the baseline down to 10–20% on one scenario.
- Two trigger queries that referred to "the plan" and "what you just wrote" gained `history:` recaps. In an empty session the agent correctly asked what to act on and said it would use the skill next.

**Honesty caveat.** `/project` is mounted read-only on both arms. In one pre-fix run, a baseline agent stuck on the hung fake found `skills/delegating-to-codex/scripts/codex_run.py` there and used it. The recorded run shows no such contamination, but a baseline that goes looking can find the skill.
