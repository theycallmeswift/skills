---
history: ./session.jsonl
---

## Prompt

catch me up on where we left off

## Assertions

### Scored

- [ ] The agent's reply states the working tree has uncommitted changes
- [ ] The agent's reply does not claim the working tree is clean
- [ ] The agent's reply names the branch it is on
- [ ] The agent's reply identifies an open pull request numbered 48
- [ ] The agent's reply does not claim that no pull request exists
- [ ] The agent's reply states that the pull request's checks are failing
- [ ] ./.fake-gh/calls.log contains `pr view`
- [ ] The agent's reply does not claim the pull request is ready for review

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
