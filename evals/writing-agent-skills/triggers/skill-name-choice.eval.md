---
---

## Prompt

what's the right name for a skill that runs `make test` and analyzes failures? `test-runner` or `running-tests`?

## Assertions

- [ ] Skill `writing-agent-skills` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Skill `writing-prompts` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
