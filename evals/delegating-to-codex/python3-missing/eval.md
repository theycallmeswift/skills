---
---

## Prompt

Execute Task 2 from ./docs/plan.md. The plan assigns it to Codex, and the Codex CLI on this machine is installed and logged in. Leave the work committed when you're done.

## Assertions

- [ ] Skill `delegating-to-codex` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.fake-codex/calls.log exists
- [ ] ./.fake-codex/calls.log contains `--sandbox workspace-write`
- [ ] ./.fake-codex/commits.log lists ./slugify.py in a commit
- [ ] The final response does not claim the task was blocked or that the delegation could not be run
