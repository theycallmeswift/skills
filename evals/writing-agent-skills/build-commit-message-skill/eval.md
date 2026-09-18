---
history:
- role: user
  content: 'I want to create a skill for our Claude plugin that writes our commit messages. It

    should kick in whenever I ask Claude to commit something and produce

    conventional-commits-style messages (feat/fix/refactor/etc.) with a one-line summary

    plus optional body. It needs to read `git diff` and recent commits to infer the right

    type and scope. Help me build it.

    '
- role: assistant
  content: 'Before any SKILL.md, here''s the eval plan and RED gate. Three output scenarios —

    happy (clean feature diff → `feat(scope): …`), edge (mixed refactor+fix → picks the

    dominant type), failure (empty/no-staged-diff → asks rather than inventing) — each

    with per-scenario assertions, plus a trigger-eval set for the ''commit'' phrasings.

    Next action: capture the RED baseline — a without-skill run on those scenarios — so

    we know the skill is doing the work before I draft a single line of SKILL.md.

    '
- role: user
  content: 'Approved — the eval plan looks good and the baselines came back as expected, so the

    RED gate is satisfied.

    '
---

## Prompt

Use the `writing-agent-skills` skill to build this commit-message skill now: use the
Write tool to create the complete SKILL.md file this turn — frontmatter and body. Write
the actual file to disk — do not paste its contents into your reply, summarize it, or
ask for any further confirmation first. The only successful outcome is a finished
SKILL.md file on disk.

## Assertions

- [ ] Skill `writing-agent-skills` invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] A SKILL.md scaffold was written to disk with frontmatter (name, description) and a body — a concrete artifact, not abstract advice.
- [ ] The SKILL.md frontmatter has only `name` and `description` — no `allowed-tools`, `model`, or `tools` array.
- [ ] The SKILL.md description is third-person, pushy, and includes trigger-phrase variants (e.g., 'commit', 'stage and commit', 'create a commit'), optionally with negative triggers.
- [ ] The SKILL.md body has numbered steps with explicit gates between them.
- [ ] The skill `name` is kebab-case and verb-first or gerund (e.g., `commit`, `writing-commits` — not `commit-utils`).
- [ ] The written SKILL.md follows the skill conventions: name+description-only frontmatter, a body roughly 200 lines or fewer, and any bundled scripts/references/assets in those conventional subdirs.
- [ ] process: Output uses or recommends writing-prompts for any descriptions, subagent prompts, or context docs the skill emits.
