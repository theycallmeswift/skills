# building-design-systems — eval record

Recorded 2026-11-20. Setup: benchspec 0.0.5, Docker sandbox, `anthropic/claude-sonnet-5.5` on OpenRouter (the `openrouter` set in `pyproject.toml`), binder on OpenRouter. The baseline arm ran bare and the trial arm loaded the plugin via `--plugin-dir`. Each output scenario's `setup.sh` installs `python3` on both arms, because the guest image ships without it. Activation lines (`Skill … invoked`) are scoped off baseline and left out of these tallies. Every output eval ran 3× per arm.

Source: `iteration_10`, all seven scenarios at the head of the PR after review round 1 (the wider `check_refs.py`, the workspace-root section, and the stricter `extracts-brand-not-invents` checks).

Re-run:

```bash
uv run --group evals benchspec run --set openrouter --binder-provider openrouter --eval-paths evals/building-design-systems -- -k 'not triggers' --count 3 -n 8
```

```bash
uv run --group evals benchspec run --set openrouter --binder-provider openrouter --eval-paths evals/building-design-systems,evals/critiquing-designs -- -k 'trial and triggers' -n 8
```

## Output evals — baseline vs trial (3 samples each)

| Eval | baseline | trial | Δ |
|---|---|---|---|
| extracts-brand-not-invents | 4/24 (17%) | 24/24 (100%) | +83pp |
| contrast-fix-keeps-brand | 23/27 (85%) | 27/27 (100%) | +15pp |
| csp-safe-fonts | 12/18 (67%) | 15/18 (83%) | +17pp |
| doc-css-contradictions | 18/21 (86%) | 21/21 (100%) | +14pp |
| editorial-keeps-every-rule | 27/30 (90%) | 30/30 (100%) | +10pp |
| doc-css-conflict | 9/9 (100%) | 9/9 (100%) | 0 |
| earlier-decision-wins | 12/12 (100%) | 12/12 (100%) | 0 |

On the two key scenarios the trial took 20–45 s and 187k–273k tokens per sample; the baseline took 27–32 s and 111k–141k.

- **extracts-brand-not-invents:** the baseline doesn't invent colours (it reads the logo and CSS), but in all three runs it writes its own layout (`docs/design/tokens.md`, `components.md`) with no `tokens.json`, and it doesn't always point `AGENTS.md` at the system. The trial produces the `foundations/` layout, the logo colours under `brand`, and the pointer every time.
- **contrast-fix-keeps-brand:** neither arm changes a brand colour. The baseline in 2/3 runs leaves `danger` at 4.599:1, which passes the stale table's WCAG AA target and shows as "4.60"; the trial applies the 4.6:1 margin and fixes it.
- **contrast.md regenerated, not hand-edited:** benchspec has no post-run hook, so this is checked offline from each run's `session.jsonl`. In all three trial runs the last write to `contrast.md` is `contrast_table.py`, with no later edit. Two baseline runs wrote it from a one-off script of their own.
- **csp-safe-fonts:** the baseline never writes `@font-face` or lists font files. All three trial misses are judge disagreements: twice the judge's own evidence says no file contains `fonts.googleapis.com` but marks the check failed, and once it counts a `Don't: style=""` prose rule as example markup.
- **doc-css-contradictions:** both arms find all five mismatches; the baseline doesn't ask whether the CSS should change. `check_refs.py` itself reports all five on this fixture; a pytest pins that (`test_eval_fixture_reports_all_five_planted_mismatches`).
- **editorial-keeps-every-rule:** the baseline restates the contrast targets across files. The trial keeps all 40 values, each in one place.
- **doc-css-conflict** and **earlier-decision-wins** don't discriminate on Sonnet 5.5: the bare agent already resolves toward the CSS and keeps the user's earlier decision.

## Routing evals — trial arm (1 sample)

| Query | Expected | Result |
|---|---|---|
| turn our brand assets into a design system agents can use | fires (not `critiquing-designs`) | pass |
| make our design docs machine-readable for coding agents | fires | pass |
| set up docs/design with tokens and component specs | fires (not `bootstrap`) | pass |
| build a design system for this repo | fires (not `critiquing-designs`, `bootstrap`) | pass |
| build the settings page with our tokens | doesn't fire | pass |
| design me a new logo | doesn't fire | pass |
| critique our design system with a few models | `critiquing-designs`, not this skill | pass |
| run a design-system critique across models | `critiquing-designs`, not this skill | pass |

The other four `critiquing-designs` routing queries also still pass with this skill loaded.

## Iteration history

- **iteration_02 (baseline only):** `contrast-fix-keeps-brand` scored 100% on baseline. The fixture was too easy: the stale table already showed every failure.
- **iteration_03 (baseline only):** a harder fixture (a role that references a logo colour, more pairings, a stale table) still scored 100%. The baseline noted the guest had no `python3`, so the skill's scripts couldn't have run either.
- **iteration_04:** each scenario installs `python3`; the stale table states plain WCAG AA targets, so the 4.6:1 margin is what's tested. Baseline 77% → trial 92%.
- **iteration_05:** `editorial-keeps-every-rule` stopped counting generated files (`tokens.css`, `contrast.md`) as restated values, and `check_refs.py` counts hex values in `tokens.json` as documented.
- **iteration_08–09:** step 5 keeps values unchanged; trial reruns of the editorial and the two key scenarios.
- **iteration_10 (review round 1):** `check_refs.py` compares per-theme values, documented states, fixed versus minimum heights and preview-only rules; SKILL.md gains a workspace-root section; `extracts-brand-not-invents` checks the logo colours sit under `brand`. All seven scenarios rerun 3× per arm.
