---
history:
- role: user
  content: 'Here are the new Pulse dashboard mockups: ./mockups/dashboard-dark.png and
    ./mockups/incidents-empty.png.'
- role: assistant
  content: Got them. What would you like to do with them?
---

## Prompt

have a few models critique these mockups

## Assertions

- [ ] Skill `critiquing-designs` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
