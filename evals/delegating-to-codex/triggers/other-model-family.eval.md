---
history:
- role: user
  content: |
    Add rate limiting to the /login endpoint: 5 attempts per IP per minute, 429 after that.
- role: assistant
  content: |
    Done. I added a sliding-window limiter in middleware/rate_limit.py, wired it into the
    /login route, and added tests for the 5th and 6th attempts. All tests pass.
---

## Prompt

I want a different model family to review what you just wrote. use codex for that

## Assertions

- [ ] Skill `delegating-to-codex` invoked
