---
---

## Prompt

Use the `interview-me` skill to interview me about my idea — I want to redesign our
onboarding flow.

## Assertions

- [ ] Skill `interview-me` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The first turn poses exactly ONE question, and it is about the STOP CONDITION — where the interview should stop (until the user says stop / until a downstream skill like to-spec has enough / until a stated goal is met) — not a substantive design question about the onboarding flow. (The stop mode is resolved FIRST from the invocation phrasing; this invocation states none, so one clarifying question about where to stop is the correct first move.)
- [ ] The skill does NOT begin substantive design grilling (it asks no onboarding-design questions and presents no design options) before the stop mode is resolved.
- [ ] process: No handoff requirements subagent (an Agent/Task call reading a target skill's `SKILL.md`) is dispatched yet — with no stop mode chosen there is no named target to read a checklist for.
- [ ] No spec file was written under ./docs/specs/.
