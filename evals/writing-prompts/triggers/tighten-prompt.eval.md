---
---

## Prompt

rewrite this prompt to be tighter — 'You are a helpful assistant that summarizes texts. Please make sure to capture the main points...'

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] Skill `writing-agent-skills` not invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
