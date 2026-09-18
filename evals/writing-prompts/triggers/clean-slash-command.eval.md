---
---

## Prompt

draft the body for `/clean` slash command — finds stale branches, asks for confirmation, deletes

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Skill `writing-agent-skills` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
