---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] Skill `catch-me-up` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply begins with a section labeled TL;DR, with no text before it
- [ ] The agent's reply states that no work is waiting on the user, in those words or equivalent ones such as no open threads, no TODOs, or nothing blocked
- [ ] The agent's reply does not present a project decision as needing the user's input
- [ ] The agent's reply separates what the user owns from what the agent owns, and shows the user's side as empty
- [ ] The agent's reply names the project or topic the session is about
