---
---

## Prompt

Have a few models critique these mockups: ./mockups/dashboard-dark.png and ./mockups/incidents-empty.png. They're for Pulse, our internal deploy dashboard. The design tokens are in ./design/tokens.md and my design notes in ./design/notes.md. An OpenRouter key is set in the environment (`OPENROUTER_API_KEY`, with `OPENROUTER_BASE_URL`; both also in ./.env).

## Assertions

- [ ] Skill `critiquing-designs` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.fake-openrouter/calls.log has no line matching `"method": "POST"`
- [ ] A rubric file written under ./ lists, as decisions the models must not argue, the dark-theme-only and icon-only-nav decisions from ./design/notes.md
- [ ] The rubric file written under ./ tells the models to reply in JSON and spells out the reply's fields, including a list of issues
- [ ] The final message asks me to approve or change the rubric before any model is called
- [ ] The final message presents no critique findings as coming from other models
