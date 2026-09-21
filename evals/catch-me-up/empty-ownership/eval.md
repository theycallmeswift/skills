---
history:
- role: user
  content: |
    Finish the not-trigger coverage for catch-me-up. The last choice is whether direct PR-status requests belong here.
- role: assistant
  content: |
    A direct PR-status lookup is narrower than session reorientation, so I recommend keeping it as a near miss. Should I use "what's the status of PR #35?" verbatim?
- role: user
  content: |
    Yes. Use that exact wording, and keep the activation assertion arm-gated.
- role: assistant
  content: |
    Added ./evals/catch-me-up/not-triggers/pr-status.eval.md with the exact prompt, empty frontmatter, and the required baseline exclusion.
- role: user
  content: |
    Check the rest of the routing files for the same frontmatter and assertion shape.
- role: assistant
  content: |
    All 20 routing files have both frontmatter delimiters. Every activation line uses the exact skill name and includes the arm clause.
- role: user
  content: |
    Run the two acceptance commands. If they pass, this task is done.
- role: assistant
  content: |
    The collect-only command reports exactly 25 cases with no collection errors. The eval linter reports no findings for catch-me-up.
- role: user
  content: |
    Then we're settled. No follow-up decisions from me.
- role: assistant
  content: |
    Finished and verified. The requested eval suite is complete, and there are no remaining questions or blocked items.
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] The recap states that nothing is currently blocked on the user
- [ ] The recap does not ask the user to make a decision
