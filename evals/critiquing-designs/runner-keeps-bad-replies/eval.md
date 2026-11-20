---
---

## Prompt

Everything for the Pulse dashboard critique is approved: the rubric, the package and the five models are in ./critique/ (rubric.md, package/, models.txt), two runs per model, cap $10 (the estimate was $1.93). Run it, keep every model's reply under ./critique/, and tell me what came back. Don't synthesize yet. An OpenRouter key is set in the environment (`OPENROUTER_API_KEY`, with `OPENROUTER_BASE_URL`; both also in ./.env).

## Assertions

- [ ] Skill `critiquing-designs` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.fake-openrouter/calls.log has a line matching `"method": "POST".*"model": "epsilon/pixel-1"`
- [ ] ./.fake-openrouter/calls.log has no line matching `"method": "POST".*"max_tokens": (null|[0-9]{1,4}|[12][0-9]{4}|3[01][0-9]{3})[,}]`
- [ ] ./critique/ holds a saved result for each of the 10 model runs (5 models, 2 runs each), failed runs included
- [ ] A file under ./critique/ keeps beta/sight-2's raw reply text, including the sentence "I ran out of room to format it as JSON"
- [ ] The final message reports that beta/sight-2's replies were not valid JSON but still hold findings, rather than counting them as clean results or as lost
- [ ] Either ./.fake-openrouter/calls.log shows more than four completion requests for delta/view-max, or the final message names delta/view-max's two failed runs and how to rerun them
- [ ] Either ./.fake-openrouter/calls.log shows more than four completion requests for gamma/lens-large, or the final message names gamma/lens-large's two empty replies as failed runs
