---
---

## Prompt

tighten AGENTS.md so codex stops ignoring our test conventions

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Skill `delegate-to-agent` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
