---
history:
- role: user
  content: |
    Help me compare two ways to explain skill routing to new contributors. I put rough observations in ./research-notes.md.
- role: assistant
  content: |
    I read ./research-notes.md. The two options are a rule-first explanation and an example-first walkthrough; the notes favor examples for first-time readers.
- role: user
  content: |
    What tradeoff would we make by leading with the example?
- role: assistant
  content: |
    It lowers the initial learning curve but can hide the general boundary between output behavior and routing behavior. A short rule summary after the example would restore that model.
- role: user
  content: |
    Record that as the working direction in ./decision-log.md, but leave the final choice open.
- role: assistant
  content: |
    ./decision-log.md now records example-first as the working direction and notes that the final structure remains open pending a contributor review.
- role: user
  content: |
    Add the strongest argument for rule-first so the comparison is fair.
- role: assistant
  content: |
    I added that rule-first makes the trigger/output distinction explicit before readers see exceptions, which may reduce overgeneralization from one example.
- role: user
  content: |
    That's enough research for today. Don't turn it into implementation work.
- role: assistant
  content: |
    Stopped at research and planning. The two notes contain the evidence, current leaning, counterargument, and the still-open review step.
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] The recap produces a summary rather than declining or reporting an error
- [ ] The recap makes no claim about a git branch
- [ ] The recap makes no claim about a pull request or CI status
