---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

### Scored

- [ ] The agent's reply states that no work is waiting on the user, in those words or equivalent ones such as no open threads, no TODOs, or nothing blocked
- [ ] The agent's reply does not present a project decision as needing the user's input
- [ ] The agent's reply separates what the user owns from what the agent owns, and shows the user's side as empty

### Output contract gate

- [ ] The agent's reply names the project or topic the session is about
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply contains a section labeled TL;DR
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply contains a section labeled Cliff Notes
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply contains a section labeled Next Up
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply places TL;DR before Cliff Notes and Cliff Notes before Next Up
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply separates those three sections with `***` rather than `---`
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The TL;DR content is a paragraph of body text rather than a heading or a bold line
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply has a Next Up section separating items owned by the user from items owned by the agent
  - if: {BENCHSPEC_ARM} != "baseline"
