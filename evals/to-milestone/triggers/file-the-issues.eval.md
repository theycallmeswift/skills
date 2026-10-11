---
---

## Prompt

the spec PR merged, go ahead and file the issues with their dependency links so the orchestrator can pick them up

## Assertions

- [ ] Skill `to-milestone` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Skill `claude-cloud-orchestrator` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
