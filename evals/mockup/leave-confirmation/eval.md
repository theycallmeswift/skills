---
---

## Prompt

mock up the leave-confirmation dialog for the challenge screen

## Assertions

- [ ] Skill `mockup` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The final message offers at least two distinct designs for the dialog, each labeled with a letter (A, B, …)
- [ ] A file exists under a `./**/mockups/v1/` directory
- [ ] ./src/screens/challenge.ts still contains `station.goTo("attract")` directly inside the escape branch, with no dialog code added
- [ ] The final message ends by asking the user to pick a design or approve one
- [ ] No spec, issue list, or implementation plan file was written to the workspace
