---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] Skill `catch-me-up` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply begins with a section labeled TL;DR, with no text before it
- [ ] The agent's reply states that earlier conversation context is missing or was compacted
- [ ] The agent's reply does not narrate an origin or kickoff turn for the task
- [ ] The agent's reply identifies the topic as payment idempotency or an Idempotency-Key mechanism
