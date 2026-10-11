Part of the <Milestone> milestone, closer 2 of 2 in [<spec file>](<spec URL on main>). **Depends on:** {#<closer-1-key>} (closer 1). Carries the `milestone-closer` label.

## Goal
The milestone is live, its spec records that, and the milestone is closed.

## Scope
- **Check "Done when".** After the last PR lands, check every line of the spec's "Done when" for real and record the evidence on this issue.
- **Mark the spec shipped.** Its status becomes shipped with the date, plus a short "Shipped" section: what landed, what was deferred and where, and anything the check found.
- **Close the milestone**, after moving any deferred issue out of it with a comment naming where it went.

## Out
- Anything the check finds broken: that is a bug issue in this milestone, and this closer waits on it.

## Acceptance
- [ ] Every "Done when" line is checked, with evidence on this issue.
- [ ] The spec's status and "Shipped" section are updated in one docs PR.
- [ ] The milestone is closed with no open issue.

## Working rules
- Read `AGENTS.md` and the style docs it names first. The spec is `<spec path>`.
- Put `Closes #<this issue>` in the docs PR's body.
