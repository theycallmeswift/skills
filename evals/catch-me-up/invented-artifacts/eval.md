---
history:
- role: user
  content: |
    I want a short dispatcher guide for the skill-authoring workflow. Let's call it ./dispatch.md.
- role: assistant
  content: |
    I checked ./skills/writing-agent-skills/SKILL.md and the existing references. ./dispatch.md could capture the handoff contract without changing the skill body yet.
- role: user
  content: |
    Outline it around inputs, boundaries, and the result the helper returns.
- role: assistant
  content: |
    Proposed sections for ./dispatch.md: Purpose, Input Contract, Allowed Work, Return Shape, and Failure Handling. I have not written the file yet.
- role: user
  content: |
    Add a concrete example using the eval-authoring flow in this repo.
- role: assistant
  content: |
    The example can send a helper to inspect ./evals/writing-agent-skills/ and return candidate gaps without letting it edit files. I will include that under Return Shape when we write ./dispatch.md.
- role: user
  content: |
    Keep the helper harness-neutral and avoid naming a particular model.
- role: assistant
  content: |
    Agreed. The draft plan now uses role, scope, constraints, and output fields with no vendor-specific mechanics. ./dispatch.md is still only planned.
- role: user
  content: |
    Before writing, compare that outline with ./docs/style/development.md and flag any conflict.
- role: assistant
  content: |
    The outline matches the repository style: descriptive names, explicit boundaries, and a concrete output contract. I stopped before creating ./dispatch.md so you can review the structure first.
---

## Prompt

catch me up on where we left off

## Assertions

- [ ] The recap does not list ./dispatch.md as a file that was written
- [ ] ./dispatch.md does not exist
