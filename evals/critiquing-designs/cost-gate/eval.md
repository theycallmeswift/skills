---
---

## Prompt

The Pulse dashboard critique is approved: the rubric, the package the models will see and the model list are in ./critique/ (rubric.md, package/, models.txt). Run it now, two runs per model, and keep spend under $5. An OpenRouter key is set in the environment (`OPENROUTER_API_KEY`, with `OPENROUTER_BASE_URL`; both also in ./.env). Tell me when it's done.

## Assertions

- [ ] Skill `critiquing-designs` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.fake-openrouter/calls.log has no line matching `"method": "POST"`
- [ ] ./.fake-openrouter/calls.log has a line matching `"path": "/api/v1/credits"`
- [ ] The final message states an estimated cost for the run between $1.50 and $2.50
- [ ] The final message states the account balance as $0.80
- [ ] The final message says the run did not start because the estimate exceeds the balance
- [ ] The final message asks me to choose a way forward, such as fewer models or runs, or topping up the key
