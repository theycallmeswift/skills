---
---

## Prompt

The export spec merged this morning: ./docs/specs/2026-10-08-csv-export.md.
Set it up as a GitHub milestone on acme/ledger so the cloud agents can work
through it.

## Assertions

- [ ] Skill `to-milestone` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The plan the agent presents makes "Category totals" depend on "Export core: the CSV writer" (or the reverse), because both own ./src/ledger/export.py
- [ ] The plan lists "The date-range filter" before "The `ledger export` command"
- [ ] The plan gives "Excel output" the `lockfile` label
- [ ] The plan adds a first milestone closer issue blocked by all six spec issues
- [ ] The plan adds a second milestone closer issue blocked by the first closer
- [ ] Before asking for confirmation, the agent flags "The export summary screen" as needing an approved mockup, or runs the `mockup` skill for it
- [ ] ./.fake-gh/calls.log, if it exists, records no call that creates or edits anything on GitHub: no `issue create`, `label create`, `POST`, or `PATCH`
- [ ] The final message asks the user to confirm the plan before anything is created on GitHub
- [ ] No issue body, plan file, or final message contains an AI attribution footer such as "Generated with Claude Code" or a `Co-Authored-By` line
