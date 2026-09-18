---
---

## Prompt

writing the system prompt for our internal support triage LLM — accepts ticket JSON, returns category + priority + suggested action. draft it

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Skill `writing-agent-skills` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
