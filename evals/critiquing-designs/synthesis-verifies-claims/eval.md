---
---

## Prompt

The multi-model critique of the Pulse test matrix has finished. Everything is in ./critique/: the approved rubric (rubric.md), the package the models saw (package/: the gridded screenshot, manifest.json, tokens.md), one record per model run in records/ (4 models, 2 runs each) and run_stats.json. Synthesize the records into ./critique/synthesis.md: what should we change? Don't call any models again.

## Assertions

- [ ] Skill `critiquing-designs` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.fake-openrouter/calls.log has no line matching `"method": "POST"`
- [ ] ./critique/synthesis.md contains `4.42`
- [ ] ./critique/synthesis.md does not recommend changing `--band` to #E0E3EC as the models proposed; it rejects that fix because the note text #5E677B fails AA on it
- [ ] ./critique/synthesis.md does not recommend any change to the A–H and 1–8 edge labels or to the thin grey lines crossing the screenshot
- [ ] ./critique/synthesis.md names the edge-label or grey-line critique as a page artifact (the review grid, not the design)
- [ ] ./critique/synthesis.md does not recommend showing nav labels by default, and cites the settled decision to keep the nav collapsed to icons
- [ ] ./critique/synthesis.md credits the 16px-to-24px matrix cell change to one model (gamma/lens-large, 1 of 4), not two
- [ ] ./critique/synthesis.md includes the per-row failure count change and credits delta/view-max for it, whose run 2 reply was not valid JSON
