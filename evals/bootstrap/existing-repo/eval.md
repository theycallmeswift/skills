---
---

## Prompt

Bring this repo up to my house setup: AGENTS.md with CLAUDE.md symlinked to
it, docs/style guides, test and lint gates, Claude settings, cloud-agent docs,
and a PR template. Some of it is already here. No interactive user: finish end
to end, then tell me what you did.

## Assertions

- [ ] Skill `bootstrap` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./AGENTS.md is byte-identical to the seeded workspace file
- [ ] ./CLAUDE.md is byte-identical to the seeded workspace file
- [ ] ./docs/style/testing.md is byte-identical to the seeded workspace file
- [ ] ./Makefile is byte-identical to the seeded workspace file
- [ ] ./docs/style/python.md exists
- [ ] ./.github/pull_request_template.md contains a `## Ready gate` table with a `Red run` row
- [ ] The final message reports that ./AGENTS.md has no Landing changes section
- [ ] The final message reports that ./CLAUDE.md is a regular file, not a symlink to ./AGENTS.md
- [ ] The final message reports that ./Makefile has no `format` target
