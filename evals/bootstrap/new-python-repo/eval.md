---
---

## Prompt

This is a brand-new Python repo. Bootstrap it with my house setup: AGENTS.md
with CLAUDE.md symlinked to it, docs/style guides, test and lint gates, Claude
settings, cloud-agent docs, and a PR template. No interactive user: finish end
to end, then tell me what you did.

## Assertions

- [ ] Skill `bootstrap` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./.github/pull_request_template.md has a `## Decide` section
- [ ] ./.github/pull_request_template.md has a `## Ready gate` table with `Red run` and `Sibling sweep` rows
- [ ] ./docs/style/development.md says imports go at the top of the file except when a function-level import is required
- [ ] ./docs/style/testing.md says unit tests cover only pure logic, as input/output tables with no mocking
- [ ] ./docs/style/testing.md says e2e and integration tests carry most of the coverage
- [ ] ./AGENTS.md says every PR lands on `main` as one squash commit and that a branch may update by merging `main` into it
- [ ] ./.claude/settings.json sets `attribution.commit` and `attribution.pr` to empty strings
- [ ] ./.github/workflows/ci.yml runs lint and tests in its one job, named `CI passed`
- [ ] ./.github/workflows/ci.yml skips the test step when a pull request changes only files under `docs/`
- [ ] The final message says branch protection on `main` should require the `CI passed` check
