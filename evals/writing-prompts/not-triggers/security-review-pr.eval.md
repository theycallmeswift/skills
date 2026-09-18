---
---

## Prompt

review this PR for security issues — looking for sql injection, xss, auth bypass

## Assertions

- [ ] Skill `writing-prompts` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Skill `writing-agent-skills` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
