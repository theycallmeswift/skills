---
---

## Prompt

draft a Slack message to my team announcing the launch

## Assertions

- [ ] Skill `writing-prompts` not invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] Skill `writing-agent-skills` not invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
