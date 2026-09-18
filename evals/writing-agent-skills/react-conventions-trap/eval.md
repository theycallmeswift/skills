---
---

## Prompt

Use the `writing-agent-skills` skill to help me create a skill called `react-conventions`
that tells Claude how we write React components in this repo: functional components, hooks
only (no class components), no Redux (we use Zustand), prefer composition over
prop-drilling. Help me build it.

## Assertions

- [ ] Skill `writing-agent-skills` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Output flags that project-specific conventions don't belong in a skill (skills are reusable techniques/patterns; project conventions belong in CLAUDE.md or docs/style/).
- [ ] Output proposes a specific alternative home — CLAUDE.md for high-level conventions, or a load-on-demand reference doc under `docs/style/`, or both — rather than building the convention skill as asked.
- [ ] If the output drafts a skill anyway as a fallback, it names the tradeoff and recommends the alternative first.
- [ ] process: Output uses or recommends writing-prompts for any descriptions, subagent prompts, or context docs the skill emits.
