---
---

## Prompt

Have Codex implement the retry helper described in ./docs/brief.md.

## Assertions

- [ ] Skill `delegating-to-codex` invoked
- [ ] ./.fake-codex/calls.log does not exist
- [ ] ./retry.py does not exist
- [ ] The final response says Codex is not logged in and tells the user to run `codex login`
