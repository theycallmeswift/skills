---
---

## Prompt

The multi-model critique of the Pulse test matrix finished. The rubric, the package the models saw and the run records are in ./critique/. What should we change? Write it up in ./critique/synthesis.md. Don't call the models again.

## Assertions

- [ ] Skill `critiquing-designs` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.fake-openrouter/calls.log has no line matching `"method": "POST"`
- [ ] ./critique/synthesis.md contains `4.42`
- [ ] ./critique/synthesis.md does not recommend changing `--band` to #E0E3EC as proposed, because the note text #5E677B on #E0E3EC fails AA
- [ ] ./critique/synthesis.md does not recommend any change to the A–H and 1–8 edge labels or to the thin grey lines crossing the screenshot
- [ ] ./critique/synthesis.md names the edge-label or grey-line critique as a page artifact (the review grid, not the design)
- [ ] ./critique/synthesis.md does not recommend showing nav labels by default, and cites the settled decision to keep the nav collapsed to icons
- [ ] ./critique/synthesis.md attributes the 16px-to-24px matrix cell change to gamma/lens-large alone, not to two models
- [ ] ./critique/synthesis.md includes the per-row failure count change, drawing on delta/view-max's run 2 reply even though that reply was not valid JSON
