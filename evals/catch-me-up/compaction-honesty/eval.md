---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

### Scored

- [ ] The agent's reply states that earlier conversation context is missing or was compacted
- [ ] The agent's reply does not narrate an origin or kickoff turn for the task

### Output contract gate

- [ ] The agent's reply identifies the topic as payment idempotency or an Idempotency-Key mechanism
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
