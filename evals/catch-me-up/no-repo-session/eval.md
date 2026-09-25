---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] Skill `catch-me-up` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply begins with a section labeled TL;DR, with no text before it
- [ ] The agent's reply is a session summary rather than a refusal or an error message
- [ ] The agent's reply makes no claim about a git branch
- [ ] The agent's reply makes no claim about a pull request or CI status
- [ ] The agent's reply names the project or topic the session is about
