---
---

## Prompt

write docs/runbooks/oncall.md for our SREs — how to handle a pager alert, escalate, and hand off at shift end

## Assertions

- [ ] Skill `writing-prompts` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Skill `writing-agent-skills` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
