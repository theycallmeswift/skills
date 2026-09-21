---
history:
- role: user
  content: |
    Build the baseline eval suite described in ./docs/specs/2026-09-21-catch-me-up.md. Keep the work under ./evals/catch-me-up/ and do not create the skill yet.
- role: assistant
  content: |
    I read the spec and ./skills/writing-agent-skills/references/evaluating-skills.md. I am on branch feature/catch-me-up and will start with the routing cases.
- role: user
  content: |
    Preserve the prompt wording exactly. The trigger cases are sensitive to capitalization and punctuation.
- role: assistant
  content: |
    The 10 trigger and 10 near-miss files are in place with empty frontmatter and arm-gated activation assertions. I am moving on to the five output scenarios.
- role: user
  content: |
    Make the stale-state case prove that current repository state wins over anything remembered from this thread.
- role: assistant
  content: |
    I added the stale-state fixture with two tracked files and checked that its starting tree reports both as modified. The other scenario histories now cover missing artifacts, compacted context, empty ownership, and a folder without git metadata.
- role: user
  content: |
    Run the collection and lint checks before you wrap up.
- role: assistant
  content: |
    The tests pass. Collection found exactly 25 cases, and eval lint reported no findings. I pushed branch feature/catch-me-up and opened PR #48.
- role: user
  content: |
    Great. Is there anything left locally?
- role: assistant
  content: |
    No. The working tree is clean, the branch is pushed, and the pull request is ready for review.
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] The recap states the working tree has uncommitted changes
- [ ] The recap does not claim the working tree is clean
- [ ] The recap names the branch it is on
- [ ] The recap states that the pull request's checks are failing
- [ ] The recap does not claim the pull request is ready for review
- [ ] The recap contains a section labeled TL;DR
- [ ] The recap contains a section labeled Cliff Notes
- [ ] The recap contains a section labeled Next Up
- [ ] The Next Up section separates items owned by the user from items owned by the agent
- [ ] The recap names the project or topic the session is about
