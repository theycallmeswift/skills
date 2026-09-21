---
name: delegate-to-agent
description: Use when work should be handed to a delegate CLI — today the Codex CLI — as a background job: the user names Codex for a task ("have codex review my branch", "let codex implement task 3", "get a second opinion from codex", "send those findings back to codex", "is the codex job done?"), or a plan assigns a step to Codex as implementer or reviewer. Covers dispatching implementation and review jobs, checking on them, gating what comes back, and feeding fixes into the same thread. Do NOT use to pick a delegate unprompted for ordinary reviews or implementation, for your own review of code the delegate already wrote, to install or configure Codex, to debug Codex itself, to port skills or plugins to Codex, or for other models (Gemini, a Claude subagent).
---

# Delegate to an agent

Hand a task to a delegate CLI as a background job. Dispatch is already subagent-shaped: a detached worker, a bounded return, and the delegate's reasoning never entering this context. Re-doing its work afterwards spends exactly what delegation saves — gate the claims instead. Codex is the only delegate this skill drives today.

## Workspace root

Paths are relative to the workspace root:

- Interactive session: the current project directory.
- Eval or scripted invocation: the root the prompt names; honor `PROJECT_ROOT` in the env for any script invocation.

Every call goes through `python3 skills/delegate-to-agent/scripts/agent_run.py`. Don't hand-roll `codex exec`: the script sets the sandbox, forces an explicit effort, rejects mistyped config, runs preflight, records the job so it can be resumed, and runs the gate. If `python3` is missing, use whatever Python 3 the machine does have (`python`, `python3.13`); if there is none, say so and stop rather than hand-roll `codex exec`.

Never dispatch from inside a subagent: the subagent's exit kills the still-running child CLI.

## The job commands

```bash
S=skills/delegate-to-agent/scripts/agent_run.py
python3 $S start --template implement --effort high --brief brief.md --gate 'make test' [--context ctx.md] [--risks risks.md]
python3 $S start --template review --effort low --sandbox read-only --schema --base main --brief brief.md [--report report.md] [--risks risks.md]
python3 $S start --effort high --resume <job-id> --brief fixes.md --gate 'make test'
python3 $S status            # this worktree's jobs
python3 $S result [job-id]   # final message, usage, gate verdict; defaults to the newest job
python3 $S cancel <job-id>   # stops the job; any edits stay in the worktree
```

Prose picks the template; every flag is independent of it. `--sandbox read-only|workspace-write` (default writable), `--schema [FILE]` (bare means the review schema), `--diff` or `--base REF`, `--network`, `--resume JOB_ID`, `--gate CMD`.

`result` exits 4 while the job runs, 0 once it finished, and 5 when the gate failed.

## Collecting the result

`start` prints a job id and leaves the worker running. Two ways back to it:

- `--wait` runs the job in the foreground and prints the result when the worker exits. A harness that backgrounds the call wakes the session then.
- Fire and poll: keep working, then `status` and `result` on a later turn. The only option where a harness can't background a blocking call.

Write briefs, risks, and reports to a scratch directory outside the repo (or a git-ignored one) so they never land in a commit.

## Settings, per call

- `--effort` (required): `high` for implementation, `low` for reviewing a small or clear diff, one step higher for risky or tangled changes.
- `--model`: omit unless the task needs a specific one; the delegate then uses the user's configured model.
- `--network`: only when the task truly needs to fetch. Network is off in the sandbox, so tests pass offline only if dependencies are already installed.
- `--resume <job-id>`: continues that job's thread, for a fix round or a re-review. Start fresh only when the first attempt went badly off course. A resumed job ignores `--template` and `--diff`; the thread already has them.
- Everything else (attribution, `AGENTS.md`, MCP servers, auth) comes from the user's delegate config. Don't touch it.

A writable sandbox refuses a dirty worktree: commit first, and the delegate's edits stay reviewable on their own. A read-only job can't write at all, which is what makes a review safe to dispatch.

If preflight fails (the CLI is missing, logged out, or this session is already running inside it), stop and give the user the one-line fix the script printed. Don't do the delegated work yourself: they asked for the delegate.

## The gate

`--gate 'make test'` runs after the delegate exits, in the worktree, and `result` prints one line: passed, failed with the log path, skipped because the job itself failed, or error. A delegate reporting that its tests pass is a claim; the gate is the check, run by something that is not the delegate. Gate every job that writes, and report its verdict as the test result instead of re-running the suite yourself.

## The bounded return

`result` caps the final message and points at the full text on disk when it spills. Never read the stderr sidecar, and stderr must never masquerade as the answer.

## Implement

1. **Write the brief to a file.** The task, acceptance criteria, how to run the tests, and the **named risks**: the specific ways this change could go wrong. Name risks at dispatch, because fixing them at review time costs far more. If a risk depends on code the delegate won't edit, paste that function's full text into the risks file.
2. **Start the job** with `--gate` set to the project's test command.
3. **Read the result**: the delegate's `STATUS` summary plus the gate line. Open the diff only for a decision you have to make, not to re-derive what the gate proved.
4. **Commit it yourself.** The delegate only edits files and never runs `git add`/`commit`; commit once the gate has passed.
5. **Fix rounds resume the thread.** Put only the findings to fix in a new brief; rerun with `--resume <job-id>` and the same gate.

## Review

Read [references/review.md](references/review.md) before dispatching a review or acting on what comes back.

Give the reviewer everything: the brief, the implementer's report (`--report`), the named risks (`--risks`), and the full text of any function the diff doesn't show. A review with only the brief and the diff rubber-stamps. The script attaches the diff itself — `--base` for a branch review, `--diff` for uncommitted changes. Findings come back as JSON: `verdict`, `summary`, `findings` (each with `severity`, `file`, `line_start`, `confidence`, `recommendation`), and `next_steps`.
