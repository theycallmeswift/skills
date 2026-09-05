---
---

## Prompt

My `changelog` skill at `.claude/skills/changelog/SKILL.md` only fires when I literally
say "changelog" — not when I ask in natural ways like "summarize what changed since the
last release", "release notes", or "what changed since the last tag". The body is also
far too long. Use the `writing-agent-skills` skill to fix it now and write the updated
SKILL.md to disk.

## Assertions

- [ ] Skill `writing-agent-skills` invoked
- [ ] A SKILL.md was written to disk at ./.claude/skills/changelog/SKILL.md — a concrete artifact, not abstract advice.
- [ ] The written SKILL.md description is broadened past 'Generates changelogs.' to the user's natural-language triggers (release notes, what changed since the last release/tag) and avoids first/second person.
- [ ] The written SKILL.md body is shorter than the original 200 lines.
- [ ] The written SKILL.md follows the skill conventions: name+description-only frontmatter, a body roughly 200 lines or fewer, and any bundled scripts/references/assets in those conventional subdirs.
- [ ] process: Output uses or recommends writing-prompts for any descriptions, subagent prompts, or context docs the skill emits.
