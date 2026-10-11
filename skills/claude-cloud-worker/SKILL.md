---
name: claude-cloud-worker
description: How a Claude Code cloud session works on a task handed to it by an orchestrator session - opening a PR, addressing review feedback, and reporting back. Use when your prompt says you are a claude-cloud-worker. Not for sessions a human drives directly.
---

# Claude Code cloud worker

An orchestrator session gave you a task and will review your PR. No human
watches you live: when you're stuck, report `blocked` and end your turn. The
orchestrator side is the `claude-cloud-orchestrator` skill.

Report to the orchestrator session your prompt names, or a newer one a later
message names; it's never your own ID. If your prompt names none, use
`parent_session_id` from `get_session` with no `session_id`.

## Do the task

Follow the repository's agent instructions, plus:

- Open the PR as a draft and leave its draft state to the orchestrator, even
  if the repository says to mark PRs ready. Never merge.
- Address each review request with new commits. When asked to bring in the
  base, follow the repository's rules for updating branches. Push only to
  your own branch. Read base files with `git show origin/<base>:<path>`.
- Before every push, run the test and lint commands the repository names.
- Keep the PR description accurate; reviewers and the user read it, not your
  commits. Flag in it, and in your report, any choice the task didn't settle.
- After pushing, reply on the PR in a line or two saying what changed.

Never wait for input or guess. Report `blocked` when you have a question
(including about an ambiguous review request), when checks fail and you
can't fix them within the task (include the output), or when the repository
requires a human's confirmation for a step. If a permission check denies a
command, report `blocked` naming it; another route to the same result counts
as a bypass and gets more denied.

## Report to the orchestrator

Report once per round (after opening the PR, after each review round, or
when blocked), after your last push, including self-review fixes. Then don't
push until woken. You can't message the orchestrator directly, so fire a
Routine into its session:

1. Call `create_trigger` with
   `persistent_session_id: <orchestrator session ID>`,
   `initiation: "own_followup"`, no schedule,
   name `Report: PR #<number> <status>`, and this prompt:

   ```text
   [claude-cloud-worker report]
   session: <your session ID, from get_session with no session_id>
   pr: <owner>/<repo>#<number>, or none
   head: <full SHA of the commit you pushed>, or none
   status: opened | updated | blocked
   addressed: <comment URL, or "initial">
   checks: <each check command> <pass|fail>
   note: <one line; for blocked, the question or the failure>
   ```

2. Call `fire_trigger` on it, and don't delete it: the orchestrator does,
   since deleting it right away can drop the delivery. If `fire_trigger`
   isn't available, set `run_once_at` two minutes out instead.

If the report can't be sent, leave it as a PR comment. Then end your turn;
don't schedule check-ins or poll the PR. The orchestrator wakes you with a
Routine linking the comment to address: address it and any other unresolved
PR comments, then report again.
