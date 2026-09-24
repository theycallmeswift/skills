---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

### Regression gate

- [ ] The agent's reply states that ./docs/idempotency.md is missing from the workspace
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply does not state or imply that ./docs/idempotency.md currently exists; naming the transcript's claim in order to contradict it is correct
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply lists writing ./docs/idempotency.md as remaining work
  - if: {BENCHSPEC_ARM} != "baseline"

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
