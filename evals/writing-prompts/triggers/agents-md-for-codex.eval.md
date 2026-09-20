---
---

## Prompt

tighten AGENTS.md so codex stops ignoring our test conventions

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Skill `delegating-to-codex` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
