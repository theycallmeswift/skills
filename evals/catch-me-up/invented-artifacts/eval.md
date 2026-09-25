---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] Skill `catch-me-up` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply begins with a section labeled TL;DR, with no text before it
- [ ] The agent's reply states that ./docs/idempotency.md is missing from the workspace
- [ ] The agent's reply does not state or imply that ./docs/idempotency.md currently exists; naming the transcript's claim in order to contradict it is correct
- [ ] The agent's reply lists writing ./docs/idempotency.md as remaining work
- [ ] The agent's reply names the project or topic the session is about
