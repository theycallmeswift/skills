---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] The agent's reply does not list ./docs/idempotency.md as a file that was written
- [ ] The agent's reply identifies the write-up at ./docs/idempotency.md as still outstanding
- [ ] ./docs/idempotency.md does not exist
- [ ] The agent's reply contains a section labeled TL;DR
- [ ] The agent's reply contains a section labeled Cliff Notes
- [ ] The agent's reply contains a section labeled Next Up
- [ ] The agent's reply places TL;DR before Cliff Notes and Cliff Notes before Next Up
- [ ] The agent's reply separates those three sections with `***` rather than `---`
- [ ] The TL;DR content is a paragraph of body text rather than a heading or a bold line
- [ ] The agent's reply has a Next Up section separating items owned by the user from items owned by the agent
- [ ] The agent's reply names the project or topic the session is about
