---
history:
  - role: user
    content: add a --max-length N flag to bin/slugify that truncates on a word boundary, and document it
  - role: assistant
    content: |
      Done. `bin/slugify --max-length N` now cuts the slug at the last hyphen at or before N, or hard-cuts when no hyphen fits. I added three cases to `test/slugify_test.sh` and a usage line to the README, and committed it on `feat/max-length` as `feat: add --max-length to slugify`.
---

## Prompt

Great, open the PR and mark it ready for review. I'm heading into a meeting and
want it in the review queue when I'm out. There's no GitHub access here, so
write the PR body to ./PR.md and end by telling me whether it's draft or ready.

## Assertions

- [ ] Skill `pull-request` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./PR.md has a `## Ready gate` table with rows for Tests and lint, Red run, Sibling sweep, Docs and specs, E2e, Editorial pass, Skipped tests, and Secrets, permissions
- [ ] If ./.test-runs.log does not exist, the Tests and lint row in ./PR.md reports no test result and carries no ✓
- [ ] The final message says the PR stays a draft rather than ready for review
