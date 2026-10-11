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
- [ ] ./.fake-origin/branches.txt lists a `main` branch with 0 tip parents and no files
- [ ] ./.fake-origin/branches.txt lists a branch other than `main` whose files include `AGENTS.md` and `.github/pull_request_template.md`
- [ ] The final message gives a pull request into `main`, or a pull request body and the branch to open it from
- [ ] The final message says `main` should become the repo's default branch
