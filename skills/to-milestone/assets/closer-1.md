Part of the <Milestone> milestone, closer 1 of 2 in [<spec file>](<spec URL on main>). **Depends on:** every other issue in the milestone ({#<key>}, {#<key>}, ...). Carries the `milestone-closer` label.

## Goal
The milestone's code and docs are left simpler and tidier than its PRs left them, before it ships.

## Scope
- **Simplify, ranked then batched.** Review the code the milestone added and rank the simplifications: duplicated logic, helpers with one caller, tests that check the same thing twice, config that could be a default. Post the ranked list on this issue; the owner approves batches; each batch is one PR with `make test` and `make lint` green.
- **Editorial pass on the docs the milestone touched.** Brevity, accuracy against the code as it now is, and organization.
- **The ID check.** Search code, comments, test names, and undated docs for issue, PR, and requirement IDs, and remove them.

## Out
- New behavior, or any change a reviewer would call a feature.
- Shipping and closing the milestone (closer 2).

## Acceptance
- [ ] The ranked list is on this issue with the owner's approvals, and every approved batch is merged.
- [ ] The docs the milestone touched describe the code as it is on `main`.
- [ ] The ID check is clean; `make test` and `make lint` pass on `main`.

## Working rules
- Read `AGENTS.md` and the style docs it names first. The spec is `<spec path>`.
- Simple over clever: prefer deleting a concept to moving it.
- Put `Closes #<this issue>` in the last batch's PR body.
