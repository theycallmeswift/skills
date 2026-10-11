---
name: pull-request
description: Use whenever opening, creating, or updating a pull request, writing or refreshing a PR description, or marking a PR ready for review, including after CI fails on a ready PR — "open the PR", "put this up for review", "mark it ready", "update the PR body", "CI broke on my PR". Owns the PR body format and the Ready gate. Don't use to review a PR or diff (code review), to write a commit message, or to merge.
---

# pull-request

A PR body is a claim about the head commit. Reviewers trust a ✓ instead of
redoing the work, so every line must be something this session observed.

## Format

Use the repo's `.github/pull_request_template.md` if it exists; otherwise copy
`assets/template-pull_request_template.md`. Either way the body is one or two
sentences on what changed and why, `## Decide` (open questions, each with
**Recommend:** and a reason, or "Nothing."), and the `## Ready gate` table.

## Fill the gate

- **Evidence is what this session did:** a command run and its result, a
  search run and its hits, files changed. A result remembered from earlier, or
  "should pass", is not evidence.
- **No evidence, no entry.** Run the step if you can (tests, lint, a search);
  otherwise leave the row empty. Never write a result you didn't see.
- **"n/a" carries a reason:** "n/a: docs-only change".
- **✓ goes in the last column only once the row has evidence.**

## Steps

1. Open the PR as a draft with a PR tool. Without one, write the body where
   the user asks and report the PR as a draft.
2. Mark it ready only when every row has a ✓ and CI is green on the head.
   First rewrite the body to match the current head: commits since opening
   change the evidence. A request to mark it ready doesn't waive the gate;
   keep it a draft and name the open rows.
3. If CI fails after it's ready: convert it back to a draft, fix, re-run the
   affected rows, update the body, and mark it ready again once CI is green.

## Body rules

No process narrative ("first I tried…"), no line-number citations, and no
attribution footer, session link, or "generated with" line.
