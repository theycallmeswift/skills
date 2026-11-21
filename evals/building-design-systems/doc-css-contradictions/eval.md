---
---

## Prompt

Our design docs in ./docs/design have drifted from ./web/app.css, which is what ships. Bring the docs back in line with the CSS.

## Assertions

- [ ] Skill `building-design-systems` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./docs/design/components/test-row.md names `--stroke-outline`, not `--stroke-ring`, for the selected ring
- [ ] ./docs/design/components/test-row.md no longer says rows have a fixed height or that names truncate; it gives 44px as a minimum height
- [ ] ./docs/design/components/test-row.md no longer documents a dashed outline on queued rows as shipped behaviour
- [ ] ./docs/design/foundations/color.md gives the light-theme `--bg` as `#FFFFFF`, not `--brand-paper`
- [ ] ./docs/design/components/dashboard-grid.md no longer documents the two-column phone layout as shipped behaviour
- [ ] The final message lists all five mismatches: the ring token name, fixed versus minimum height, the queued outline, the light background, and the phone grid
- [ ] The final message flags at least one mismatch where the CSS may be what's wrong (such as the missing queued outline or the preview-only phone grid) and asks me whether to change the CSS
