---
---

## Prompt

Use the `writing-prompts` skill for the request below.

We're getting flooded with support tickets and I want an LLM to help triage them. Can you
write me a prompt for that?

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent asks at least one scoping question (e.g. ticket source, priority taxonomy, what 'triage' means, who consumes the output).
- [ ] Output contains no drafted prompt (no system prompt, template, or fenced prompt text) and the turn ends waiting on the user's answers.
