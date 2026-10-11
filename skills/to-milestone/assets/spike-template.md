Part of the <Milestone> milestone, issue <N> of <M> in [<spec file>](<spec URL on main>). **Depends on:** nothing. Carries the `spike` label: its output is a dated results doc with a go or no-go per gate, not a feature.

## Goal
<The open question, why the issues after this one need the answer, and what the spike proves before they start.>

## Gates, in order
1. **<Gate>** (<time box, e.g. half a day>). <What to try.> Go: <the observable result that passes it>.
2. **<Gate>** (<time box>). <What to try.> Go: <the observable result>.

## Output
- `docs/research/<YYYY-MM-DD>-<slug>.md` (or the date it runs): one row per gate with its result and evidence, and what the downstream issues should do differently.

## Out
- <Building the feature itself: the issue that depends on this spike.>

## Owns
- `docs/research/` (the results doc).

## Collides with
Nothing.

## Acceptance
- [ ] Every gate is recorded go or no-go, with evidence.
- [ ] `make lint` passes on the results doc.

## Working rules
- Read `AGENTS.md` and the style docs it names first. The spec is `<spec path>`; this issue overrides it where they differ, and docs change in the same PR.
- No issue, PR, or requirement IDs in code, comments, test names, or undated docs.
- Put `Closes #<this issue>` in the PR body.
