---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

### Regression gate

- [ ] The agent's reply is a session summary rather than a refusal or an error message
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply makes no claim about a git branch
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The agent's reply makes no claim about a pull request or CI status
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
