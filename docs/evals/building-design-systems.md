# building-design-systems — eval record

Recorded 2026-11-20. Setup: benchspec 0.0.5, Docker sandbox, `anthropic/claude-sonnet-5.5` on OpenRouter (the `openrouter` set in `pyproject.toml`), binder on OpenRouter. The baseline arm ran bare and the trial arm loaded the plugin via `--plugin-dir`. Each output scenario's `setup.sh` installs `python3` on both arms, because the guest image ships without it. Activation lines (`Skill … invoked`) are scoped off baseline and left out of these tallies. Every output eval ran 3× per arm.

Sources: baseline and the five scenarios step 5 doesn't touch from `iteration_04`; `csp-safe-fonts` and the `editorial-keeps-every-rule` baseline from `iteration_05`; the final SKILL.md's trial runs of `editorial-keeps-every-rule` (`iteration_08`) and the two key scenarios (`iteration_09`).

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
| extracts-brand-not-invents | 5/24 (21%) | 24/24 (100%) | +79pp |
| contrast-fix-keeps-brand | 23/27 (85%) | 27/27 (100%) | +15pp |
| csp-safe-fonts | 10/18 (56%) | 17/18 (94%) | +38pp |
| doc-css-contradictions | 18/21 (86%) | 21/21 (100%) | +14pp |
| editorial-keeps-every-rule | 27/30 (90%) | 30/30 (100%) | +10pp |
| doc-css-conflict | 9/9 (100%) | 9/9 (100%) | 0 |
| earlier-decision-wins | 12/12 (100%) | 12/12 (100%) | 0 |

On the two key scenarios the trial took 19–51 s and 157k–353k tokens per sample; the baseline took 26–38 s and 119k–151k.

- **extracts-brand-not-invents:** the baseline doesn't invent colours (it reads the logo and CSS), but in all three runs it writes its own layout (`docs/design/tokens.md`, `components.md`) with no `tokens.json`, and in one run never points `AGENTS.md` at the system. The trial produces the `foundations/` layout and the pointer every time.
- **contrast-fix-keeps-brand:** neither arm changes a brand colour. The baseline in 2/3 runs leaves `danger` at 4.599:1, which passes the stale table's WCAG AA target and shows as "4.60"; the trial applies the 4.6:1 margin and fixes it.
- **csp-safe-fonts:** the baseline never writes `@font-face` or lists font files, and in 2/3 runs doesn't connect the Google Fonts import to the CSP. The trial's one miss is a judge disagreement on a file it says contains no `fonts.googleapis.com`.
- **doc-css-contradictions:** both arms find all five mismatches; the baseline doesn't ask whether the CSS should change.
- **editorial-keeps-every-rule:** the baseline restates the contrast targets across files. One trial run before the last edit changed a status colour while "fixing" contrast; step 5 now says the pass changes wording, not values, and the rerun kept all 40 values.
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
- **iteration_08–09:** final SKILL.md (step 5 keeps values unchanged); trial reruns of the editorial and the two key scenarios.
