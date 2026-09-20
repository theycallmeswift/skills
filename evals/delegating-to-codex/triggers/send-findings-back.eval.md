---
history:
- role: user
  content: |
    Have Codex review the auth refactor on this branch.
- role: assistant
  content: |
    Codex finished the review (job 20260918-141200-review-a1f3). Two findings: the session
    cookie is missing SameSite, and the logout handler doesn't invalidate refresh tokens.
    Which do you want fixed?
---

## Prompt

both are real, send them back to codex to fix

## Assertions

- [ ] Skill `delegating-to-codex` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
