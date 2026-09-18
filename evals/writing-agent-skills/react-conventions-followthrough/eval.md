---
history:
- role: user
  content: 'Help me create a `react-conventions` skill that tells Claude how we write React

    components in this repo: functional components, hooks only (no class components),

    no Redux (we use Zustand), prefer composition over prop-drilling.

    '
- role: assistant
  content: 'Project-specific conventions like these don''t belong in a skill — skills are reusable

    techniques, and repo conventions belong in CLAUDE.md or a load-on-demand reference

    under docs/style/. I''d put these in docs/style/react.md and point CLAUDE.md at it,

    rather than building a convention skill.

    '
- role: user
  content: 'Makes sense — go ahead and draft docs/style/react.md with those conventions now.

    '
---

## Prompt

Use the `writing-agent-skills` skill to follow through on what we agreed: use the Write
tool to create ./docs/style/react.md this turn with the React conventions discussed above.
Write the actual file to disk — do not paste it into your reply, summarize it, or ask for
any further confirmation. The only successful outcome is a finished ./docs/style/react.md
on disk.

## Assertions

- [ ] Skill `writing-agent-skills` invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] A file was written to disk at ./docs/style/react.md — a concrete artifact, not advice or an offer to draft.
- [ ] ./docs/style/react.md states the conventions discussed: functional components, hooks only (no class components), Zustand instead of Redux, and composition over prop-drilling.
