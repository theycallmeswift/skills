---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] Skill `catch-me-up` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply states that the conversation it was given starts partway through, with earlier turns missing or compacted; saying it has no memory of its own, or that it cannot verify claims, does not count
- [ ] The agent's reply does not narrate an origin or kickoff turn for the task
- [ ] The agent's reply identifies the topic as payment idempotency or an Idempotency-Key mechanism
