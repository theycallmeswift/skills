---
---

## Prompt

This is a brand-new TypeScript repo. Bootstrap it with my house setup:
AGENTS.md with CLAUDE.md symlinked to it, docs/style guides, test and lint
gates, Claude settings, cloud-agent docs, and a PR template. No interactive
user: finish end to end, then tell me what you did.

## Assertions

- [ ] Skill `bootstrap` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./AGENTS.md does not say that lint runs markdownlint through `npx`
- [ ] ./docs/cloud-agents.md does not contain the phrase "the language's package hosts"
- [ ] ./docs/cloud-agents.md has no uv bullet and no uv install block
- [ ] ./tsconfig.json excludes `tmp`
- [ ] ./.node-version contains `26`
- [ ] Every Set up Node step in ./.github/workflows/ci.yml reads `node-version-file: .node-version`
- [ ] ./.claude/settings.json enables the `core@mechaswift` plugin
- [ ] ./.claude/settings.json allows `npm test` and `npm run lint`
- [ ] ./.env.example sets `SIFT_WEBHOOK_URL` to an empty value under a comment saying what it's for
- [ ] ./.github/workflows/ci.yml runs lint and tests in its one job, named `CI passed`
- [ ] The final message reports that ./README.md got no CI badge because the repo has no GitHub remote
- [ ] The final message reports `npm test` and `npm run lint` as passed
