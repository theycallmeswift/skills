# critiquing-designs — eval record

Recorded 2026-11-20 from `iteration_06` (the two key scenarios, `--count 3`) and `iteration_07` (the rest, 1 sample). Setup: benchspec 0.0.5, Docker sandbox, Claude Code 2.1.329 in the guest, `anthropic/claude-sonnet-5.5` on OpenRouter (the `openrouter` set in `pyproject.toml`), binder on OpenRouter. The baseline arm ran bare and the trial arm loaded the plugin via `--plugin-dir`. Every OpenRouter call the skill's runner made went to `evals/support/fake-openrouter`. Activation lines (`Skill … invoked`) are scoped off baseline and left out of these tallies.

Re-run:

```bash
uv run --group evals benchspec run --set openrouter --binder-provider openrouter --eval-paths evals/critiquing-designs -- -k 'synthesis-verifies-claims or prior-decision-wins' --count 3 -n 6
```

```bash
uv run --group evals benchspec run --set openrouter --binder-provider openrouter --eval-paths evals/critiquing-designs -- -k 'not (synthesis-verifies-claims or prior-decision-wins)' -n 6
```

The 12 key cells cost about $1.65 in OpenRouter usage, binder included.

## Output evals — baseline vs trial

| Eval | Samples | baseline | trial | Δ |
|---|---|---|---|---|
| prior-decision-wins | 3 | 3/18 (17%) | 18/18 (100%) | +83pp |
| synthesis-verifies-claims | 3 | 23/24 (96%) | 24/24 (100%) | +4pp |
| cost-gate | 1 | 0/6 (0%) | 6/6 (100%) | +100pp |
| rubric-before-spend | 1 | 0/5 (0%) | 5/5 (100%) | +100pp |
| runner-keeps-bad-replies | 1 | 6/7 (86%) | 7/7 (100%) | +14pp |

Per sample on the key scenarios, the trial took 58 s and 292k tokens; the baseline took 58 s and 220k tokens.

- **prior-decision-wins:** in all three runs the baseline recommends reversing the colour-only matrix cells and rewording the summary, and never reads `docs/design-decisions.md`. The trial cites the 2026-11-12 decision, puts the markers in a neutral Decide row, and doesn't recommend the summary change.
- **synthesis-verifies-claims:** the baseline is already strong, so the margin is small (+4pp): the baseline missed one of 24 checks.

## Routing evals — trial arm (1 sample)

| Query | Expected | Result |
|---|---|---|
| have a few models critique these mockups | fires | pass |
| run a design-system critique across models | fires | pass |
| aesthetic pass on the dashboard against reference sites | fires | pass |
| review this React component | doesn't fire | pass |
| build a design system for this repo | doesn't fire (nor `bootstrap`) | pass |
| what do you think of this screenshot? | doesn't fire | pass |

## Iteration history

- **iteration_03:** key scenarios were 70% → 68%. `synthesis-verifies-claims` leaked the method in its prompt, and `prior-decision-wins` graded checks that neither arm reached.
- **iteration_05:** both evals were rewritten as realistic asks, and `prior-decision-wins` was 17% → 17%. The realistic ask ("the critique finished, what should we change?") never activated the skill, so both arms were in effect baseline.
- **iteration_06:** the description now covers turning a finished multi-model critique into changes, and step 7 searches the repo for decision logs. The skill fired on 6/6 trial runs.
