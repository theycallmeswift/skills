---
---

## Prompt

Have Codex implement the retry helper described in ./docs/brief.md.

## Assertions

- [ ] Skill `delegate-to-agent` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.fake-codex/calls.log does not exist
- [ ] ./retry.py does not exist
- [ ] The final response says Codex is not logged in and tells the user to run `codex login`
