---
history:
- role: user
  content: |
    Plan for the billing cleanup: Task 1 rename the invoice fields (Implementer: Claude),
    Task 2 extract the tax calculator into its own module (Implementer: Codex), Task 3 update
    the API docs (Implementer: Claude).
- role: assistant
  content: |
    Plan noted. Task 1 is done and committed; Task 2 is next and is assigned to Codex.
---

## Prompt

ok, continue with the next task

## Assertions

- [ ] Skill `delegate-to-agent` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
