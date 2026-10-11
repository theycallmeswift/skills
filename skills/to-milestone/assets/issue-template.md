Part of the <Milestone> milestone, issue <N> of <M> in [<spec file>](<spec URL on main>). **Depends on:** {#<key>} (<what it uses from that issue>).

## Goal
<One or two sentences: what is true once this lands, in the user's or maintainer's terms.>

## Scope
- <What the PR builds, concrete enough to start without asking.>
- <The tests it adds.>

## Out
- <Nearby work that belongs to another issue or a later milestone, and where it goes.>

## Owns
- `<path/>`, `<path>`

## Collides with
Nothing.

## Acceptance
- [ ] <A check a reviewer can run or observe.>
- [ ] `make test` and `make lint` pass.

## Working rules
- Read `AGENTS.md` and the style docs it names first. The spec is `<spec path>`; this issue overrides it where they differ, and docs change in the same PR.
- No issue, PR, or requirement IDs in code, comments, test names, or undated docs.
- Put `Closes #<this issue>` in the PR body.
