---
---

## Prompt

turn docs/specs/2026-10-06-search.md into a GitHub milestone, one issue per row of its table

## Assertions

- [ ] Skill `to-milestone` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Skill `to-spec` not invoked
  - if: {BENCHSPEC_ARM} != "baseline"
