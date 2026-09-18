---
---

## Prompt

ok my team's CLAUDE.md is up to 380 lines, claude is starting to drift on basic stuff. trim it

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] Skill `writing-agent-skills` not invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
