---
---

## Prompt

Muted text on surface fails contrast in dark mode (3.9:1), and I think something else does too. Fix the Beacon design system in ./docs/design so every pairing passes, then regenerate ./docs/design/foundations/contrast.md and tokens.css.

## Assertions

- [ ] Skill `building-design-systems` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./docs/design/foundations/contrast.md has a row for each of the nine pairings listed in ./docs/design/foundations/tokens.json, with a value for both themes
- [ ] No row of ./docs/design/foundations/contrast.md is marked as failing, in either theme
- [ ] In ./docs/design/foundations/contrast.md every text pairing is at least 4.6:1 and every mark pairing at least 3.2:1, in both themes
- [ ] In ./docs/design/foundations/tokens.json the brand colours are unchanged: `night` is `#0E1424`, `flare` is `#F26B21`, `haze` is `#727A8C` and `mist` is `#FAFAF7`
- [ ] In ./docs/design/foundations/tokens.json the dark value of `muted` no longer resolves to `#727A8C`
- [ ] In ./docs/design/foundations/tokens.json the light value of `danger` is no longer `#E12A2A`, which measures 4.599:1 on white, under the 4.6:1 text target
- [ ] In ./docs/design/foundations/tokens.json the light value of `status-ok` is no longer `#22C55E`
- [ ] In ./docs/design/foundations/tokens.json, `on-accent` on `accent` no longer pairs `#FFFFFF` with `#F26B21` in either theme
- [ ] ./docs/design/foundations/tokens.css sets `--muted`, `--accent`, `--on-accent`, `--danger` and `--status-ok` to the same values that ./docs/design/foundations/tokens.json gives them in each theme
