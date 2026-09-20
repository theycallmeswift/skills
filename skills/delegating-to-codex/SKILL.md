---
name: delegating-to-codex
description: Use when work should be handed to the Codex CLI — the user names Codex for a task ("have codex review my branch", "let codex implement task 3", "get a second opinion from codex", "send those findings back to codex", "is the codex job done?"), or a plan assigns a step to Codex as implementer or reviewer. Covers implementation and code review as background Codex jobs, checking on them, and feeding fixes back. Do NOT use to pick Codex unprompted for ordinary reviews or implementation, for your own review of code Codex already wrote, to install or configure Codex, to debug Codex itself, to port skills or plugins to Codex, or for other models (Gemini, a Claude subagent).
---

# Delegating to Codex

Hand a task to the Codex CLI as a background job, then verify what comes back. A second model family catches what the first misses, but only if the handoff carries the right inputs and the orchestrator (you) checks the result instead of trusting it.

## Workspace root

Paths are relative to the workspace root:

- Interactive session: the current project directory.
- Eval or scripted invocation: the root the prompt names; honor `PROJECT_ROOT` in the env for any script invocation.

Every Codex call goes through `python3 skills/delegating-to-codex/scripts/codex_run.py`. Don't hand-roll `codex exec`: the script sets the sandbox, forces an explicit effort, rejects mistyped config, runs preflight checks, and records the job so it can be resumed.

## The job commands

```bash
S=skills/delegating-to-codex/scripts/codex_run.py
python3 $S start implement --effort high --brief brief.md [--context ctx.md] [--risks risks.md]
python3 $S start review --effort low --brief brief.md [--report report.md] [--risks risks.md] [--base main]
python3 $S start implement --resume <job-id> --effort high --brief fixes.md   # same Codex thread
python3 $S status            # this worktree's jobs
python3 $S result <job-id>   # final message + token usage; exits 4 while still running
python3 $S cancel <job-id>   # stops the job; any edits stay in the worktree
```

`start` returns a job id immediately. Keep working; check back with `result`. When there is nothing else to do, use `--wait` instead. Don't end your turn while a job runs: nothing brings you back to report it. Write briefs, risks, and reports to a scratch directory outside the repo (or a git-ignored one) so they never land in a commit.

**Choose settings per task, every call:**

- `--effort` (required): `high` for implementation, `low` for reviewing a small or clear diff, one step higher for risky or tangled changes.
- `--model`: omit unless the task needs a specific one; Codex then uses the user's configured model.
- `--network`: only when the task truly needs to fetch. Network is off in the sandbox, so tests pass offline only if dependencies are already installed.
- Everything else (attribution, `AGENTS.md`, MCP servers, auth) comes from the user's Codex config. Don't touch it.

If preflight fails (Codex missing, not logged in, or already running inside Codex), stop and give the user the one-line fix the script printed. Don't do the delegated work yourself: they asked for Codex.

## Implement

1. **Write the brief to a file.** Include the task, acceptance criteria, how to run the tests, and the **named risks**: the specific ways this change could go wrong. Name risks at dispatch, because fixing them at review time costs far more. If a risk depends on code Codex won't edit, paste that function's full text into the risks file.
2. **Start the job** from a clean worktree (`start implement` refuses a dirty one).
3. **Verify, don't trust.** When `result` shows `STATUS: DONE`, read the diff and `git status`, then run the test gate yourself. Codex's test summary is a claim, not evidence. Report what you observed.
4. **Commit it yourself.** Codex only edits files and never runs `git add`/`commit`; commit after the gate passes.
5. **Fix rounds resume the thread.** Write only the findings to fix into a new brief, run `start implement --resume <job-id> ...`, and verify again. Start fresh (no `--resume`) only when the first attempt went badly off course.

## Review

1. **Order by model family.** The family that wrote the code never reviews first. Codex implemented it: review it yourself first, then send it to Codex. You or another Claude agent wrote it: Codex can go first.
2. **Give the reviewer everything.** A review with only the brief and the diff rubber-stamps. Pass the brief, the implementer's report (`--report`), and the named risks (`--risks`), with the full text of any function the diff doesn't show. The script adds the diff: `--base` for a branch review, or uncommitted changes when the tree is dirty.
3. **Read the findings from `result`.** JSON: `verdict`, `summary`, `findings` (each with `severity`, `file`, `line_start`, `confidence`, `recommendation`), and `next_steps`.
4. **Judge every finding against the code before acting.** Some findings don't hold up. Open the cited lines and decide whether each is real. Always ask of the tests: does this test fail against the implementation it is meant to rule out? Tests that could never fail are the most common real finding.
5. **Then act by who asked:**
   - **User asked for the review directly:** present each finding with its file:line and your verdict, then stop and ask which to fix (some, all, or none). Change nothing yet.
   - **A plan step triggered it:** fix the real findings (yourself, or by resuming the Codex implement job), re-run the test gate, and commit. Don't block waiting for the user. Your final report names every finding: fixed, or dismissed with the reason. A dismissed finding left out of the report looks like one you never checked.

## Mutation checks

Proving a test guards a risk means breaking the code on purpose. Codex's review sandbox is read-only, so it can only reason about mutations; running them is your job. In the worktree, for each named risk the tests claim to cover:

1. Change one thing.
2. Run one test; confirm it fails.
3. Undo with an inverse edit. Never `git checkout`, `restore`, or `stash`: they can discard other work.

End with `git status` and confirm the tree matches its prior state. An implementer's failing run can be real and still prove the wrong claim.

## Before accepting a result as done

- [ ] You ran the test gate yourself after the last Codex edit.
- [ ] Every finding was verified or dismissed with a reason.
- [ ] `git status` shows only the intended changes, and the commit is yours.
