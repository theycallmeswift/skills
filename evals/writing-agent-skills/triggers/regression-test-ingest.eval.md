---
---

## Prompt

regression-test the ingest skill — both arms, default model

## Assertions

- [ ] Skill `writing-agent-skills` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
