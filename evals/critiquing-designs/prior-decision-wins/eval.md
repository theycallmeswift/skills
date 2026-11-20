---
---

## Prompt

The multi-model critique of the Pulse test matrix finished. The rubric, the package the models saw and the run records are in ./critique/. Give me the decision page at ./critique/decisions.md: what should we change?

## Assertions

- [ ] Skill `critiquing-designs` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.fake-openrouter/calls.log has no line matching `"method": "POST"`
- [ ] ./critique/decisions.md does not recommend restoring text markers or badges in the matrix cells, in full or in part (listing it as one option of an open decision is fine)
- [ ] ./critique/decisions.md names the conflict between the markers recommendation and the 2026-11-12 decision in ./docs/design-decisions.md to make the cells colour-only
- [ ] ./critique/decisions.md does not recommend changing the "27/31 passed" summary wording
- [ ] ./critique/decisions.md mentions the models' summary change and names its conflict with the decision to keep "27/31 passed"
- [ ] The final message asks me which changes to apply
