---
name: to-milestone
description: Use whenever a settled design spec should become a GitHub milestone of issues for agents or an orchestrator to work through. Fires on "turn this spec into a milestone", "set up the milestone for the spec", "file the issues for docs/specs/…", "break the spec into GitHub issues", "create the issues with their dependency links", "the spec merged, make the milestone", INCLUDING asks that name no skill. Do NOT use to write or revise the spec itself (to-spec), to work through, dispatch, or check on an existing milestone's issues (the repo's orchestrator), or to file a single issue or bug.
---

# to-milestone

Turn a settled spec into a GitHub milestone: one issue per worker PR, each blocked by the issues whose output it uses, plus closers that tidy and ship it. A milestone orchestrator consumes the result as-is: an issue's body is the worker's whole spec, its blockers set dispatch order, and its labels set limits (one `lockfile` PR open at a time).

**Requires:** `python3` for `scripts/milestone.py` (stdlib only; run it from this file's directory), and `gh` with access to the repo for steps 3, 5, and 6. The dry run needs no `gh`. Without `gh`, stop at a confirmed plan and hand over the calls the script prints. Never create issues by hand-rolled loops: a half-made milestone with wrong links is worse than none.

## Precondition: a settled, merged spec

Scope is settled (an interview or an audit) and written as a spec in the repo's own shape: copy the structure of the newest spec in its spec folder, not a generic template. The spec ends with an issue table, `| # | Title | Scope | Owns | Depends on |`, where `#` is a position until the issues exist, and a dependency graph. If no such spec exists, stop and say so; nothing is created until the spec's PR has merged.

## Steps

1. **Break down.** Read the spec's issue table; if it has none, draft one into the spec. Check every row:
   - One row per worker PR. **Owns** lists the paths it changes; **Depends on** lists the positions (or `#n` outside the milestone) whose output it uses.
   - Two rows that own the same path get a dependency between them, the later one on the earlier, so every issue's **Collides with** is "Nothing".
   - A forward reference (row 2 depends on row 4) is fine in the table: the script creates issues in dependency order.
   - Labels: `lockfile` for any issue that adds or changes a dependency (it touches the lockfile, so only one runs at a time); `spike` for a time-boxed investigation; `needs-human` for one that waits on something only a person can provide.
   - Closers: copy the count and scope of the repo's last milestone's `milestone-closer` issues; with no precedent, use two (`assets/closer-1.md`, `assets/closer-2.md`). Closer 1 is blocked by every other issue; each later closer by the one before it.

   Rows or links the table lacks (a shared-path dependency, the closers) go into the plan now and into the spec in step 6.

2. **Mockup gate.** An issue is user-facing when a person sees its output: a screen, prompt, page, message, or command output. Each one needs an approved mockup before step 4: run the `mockup` skill for it and link the approved version from that issue's Acceptance. If `mockup` can't run here, list the issue as waiting on a mockup and create nothing until it is approved. Nothing user-facing: skip this step.

3. **Write the plan.** Find the exemplar: the newest milestone's first issue (`gh api 'repos/<owner>/<repo>/milestones?state=all&sort=created&direction=desc&per_page=1'`, then its issues). Copy that body's shape exactly. With no prior milestone, use `assets/issue-template.md`, and `assets/spike-template.md` for spikes. Then, in a scratch directory outside the repo's tracked files, write `plan.json` shaped like `assets/plan-example.json` and one `<key>.md` body per issue:
   - Keys are the table positions. `blocked_by` holds keys, or `#n` for an issue outside the milestone.
   - In a body, name another planned issue as `{#<key>}`; the script swaps in the real number. Leave `#n` for existing issues as written.
   - The milestone description is one sentence on what ships, then `Spec: <path>`.
   - No AI attribution anywhere: no "Generated with" footer, no `Co-Authored-By`. The work reads as the user's; the script rejects a body that has one.

4. **Confirm.** Run `python3 scripts/milestone.py create <plan.json> --dry-run` and fix every error it reports. Show the user the milestone title and description, the issues in the order it printed (creation order, which becomes issue-number order; not the table's order) with labels and blockers, the closers, any shared-path dependency you added, and any issue still waiting on a mockup. Ask for a yes. Creating issues notifies watchers and is tedious to undo, so nothing is created until the user approves this plan.

5. **Create.** Run `python3 scripts/milestone.py create <plan.json> --result <result.json>`. It creates the milestone, any missing labels, and every issue with a stub body; then writes the real bodies (so a forward reference resolves); then adds each blocked-by link by the blocker's REST id; then reads every issue's blockers back.
   - Exit 0: report the milestone URL and the issue numbers.
   - Exit 1: report each `MISMATCH` or error verbatim. `<result.json>` records what exists; fix the gaps one call at a time rather than re-running (a second run refuses an existing milestone).
   - Exit 3: `gh` can't reach the repo and nothing was created. Give the user the printed calls.

6. **Back-fill.** First add to the spec's table and graph, by position, the rows and links from step 1 it lacked. Then run `python3 scripts/milestone.py backfill <spec> --result <result.json>`. It rewrites only the issue table's `#` and **Depends on** cells, the graph's node labels, and the spec's `Milestone:` line; prose is untouched, so update any sentence that says `#` is a position by hand. Open the docs PR with the `pull-request` skill.

## Done

The milestone exists, every issue's blockers read back as planned, and the back-fill PR is open. Report the milestone URL, the issues in dependency order, and anything waiting on the user: a mockup approval or a `needs-human` issue.
