---
---

## Prompt

Execute Task 2 from ./docs/plan.md. The plan assigns it to Codex, and the Codex CLI on this machine is installed and logged in. Leave the work committed when you're done.

## Assertions

- [ ] Skill `delegating-to-codex` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.fake-codex/calls.log exists
- [ ] ./.fake-codex/calls.log contains `--sandbox workspace-write`
- [ ] ./.fake-codex/calls.log contains `model_reasoning_effort=`
- [ ] ./.fake-codex/calls.log does not contain `--add-dir`
- [ ] The prompt recorded in ./.fake-codex/calls.log states the named risk that truncation must never leave a trailing hyphen
- [ ] ./.fake-codex/commits.log exists
- [ ] ./.fake-codex/commits.log lists ./slugify.py in a commit
- [ ] The final response reports a unit-test result that the agent itself observed after Codex finished, not only the result Codex reported
