---
---

## Prompt

do I need a skill for managing my todo list, or just put it in CLAUDE.md?

## Assertions

- [ ] Skill `writing-agent-skills` invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] Skill `writing-prompts` not invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
