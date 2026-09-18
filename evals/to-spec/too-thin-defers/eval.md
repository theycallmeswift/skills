---
---

## Prompt

Use the `to-spec` skill to capture a design spec. Repo root: your current working
directory. Earlier I said "we should probably make the app better and faster
somehow" — capture that as a design spec before we lose the context.

Today is {TODAY}. No interactive user — do what the skill says is right here, then
tell me your decision.

## Assertions

- [ ] Skill `to-spec` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] No spec file was written under './docs/specs/' — the context is too thin to ground a spec, so the skill did not emit a confident hollow one
- [ ] The final message reports specifically what is missing to write a spec (e.g. a concrete problem, a proposed change, constraints) and hands the decision back to the user
- [ ] The skill does NOT fabricate a problem statement, user stories, or implementation decisions to fill the gap, and does NOT silently redirect to a different skill
