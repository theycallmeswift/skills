---
history:
- role: user
  content: For the record, the status labels in the run table stay uppercase (PASSED, FAILED, QUEUED). That's deliberate; it's our look.
- role: assistant
  content: Noted. Uppercase status labels stay as they are.
---

## Prompt

Build the design system docs under docs/design from our CSS and the critique notes in ./notes.

## Assertions

- [ ] Skill `building-design-systems` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./docs/design/README.md exists
- [ ] No file under ./docs/design/ requires sentence case for status labels or forbids uppercase status labels
- [ ] The docs under ./docs/design/ state that status labels are uppercase
- [ ] The final message names the conflict between the critique's sentence-case recommendation and my decision to keep status labels uppercase
