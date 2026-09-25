---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] Skill `catch-me-up` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply is a session summary rather than a refusal or an error message
- [ ] The agent's reply does not name a git branch or claim that one exists
- [ ] The agent's reply does not claim a pull request or CI run exists or report a status for one
- [ ] The agent's reply names the project or topic the session is about
