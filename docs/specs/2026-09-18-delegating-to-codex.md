**TL;DR** — A harness-neutral `delegating-to-codex` skill hands implementation and review to `codex exec` through one job-manager script; the orchestrator verifies and commits.

## Problem

- **Symptom:** Delegating to Codex means a hand-copied shell recipe: raw flags, `cat` prompt assembly, `--add-dir` hacks so Codex can commit in linked worktrees.
- **Exposed by:** The recipe's process rules worked (a brief+diff-only review caught 0 of 10 findings; a full-input one caught them), but its mechanics inherit the user's effort default (`ultra`) and make `.git` writable, which lets Codex plant hooks that run unsandboxed.
- **Why not `openai/codex-plugin-cc`:** Claude Code-only (commands, Node broker, hooks); no network in write mode; worktree commits still broken (#273).
- **Constraint:** Harness-neutral `SKILL.md`; frontmatter `name` + `description`; the eval VM has no `codex`.

## Solution

```bash
S=skills/delegating-to-codex/scripts/codex_run.py
python3 $S start implement --effort high --brief b.md --risks r.md     # → job id
python3 $S start review --effort low --brief b.md --report rep.md --base main
python3 $S start implement --resume <job-id> --effort high --brief fixes.md
python3 $S status | result <job-id> | cancel <job-id>
```

Codex edits; the orchestrator re-runs tests and commits. `SKILL.md` carries the recipe's process rules.

## User Stories

1. As an orchestrator, I want **a plan step assigned to Codex to run as a background job**, so I keep working.
2. As an orchestrator, I want **fix rounds to resume the same Codex thread**, so context isn't re-paid.
3. As an orchestrator, I want **review findings as schema JSON**, so I can check each file:line.
4. As Swift, I want **"have codex review this" to show findings and stop**, so I pick the fixes.
5. As Swift, I want **effort set per task while my Codex config keeps attribution and auth**.
6. As a Hermes user, I want **the same skill with no Claude-only dependencies**.

## Implementation Decisions

```
SKILL.md ─► codex_run.py preflight (codex on PATH, `codex login status`, CODEX_THREAD_ID unset)
  ─► state_root(): CLAUDE_PLUGIN_DATA → HERMES_HOME/mechaswift → XDG_STATE_HOME/mechaswift → ~/.local/state/mechaswift
       └─ codex-jobs/<repo>-<sha256(worktree)[:16]>/<job>/ {prompt.md, events.jsonl, last.md, meta.json}
  ─► build_prompt() ─► build_argv() ─► detached worker ─► meta: status, thread_id, usage
```

- **Argv per mode.** Always `--json --strict-config -c model_reasoning_effort=E -o last.md -`; never `--add-dir` or `--ignore-user-config`.
  - implement: `--sandbox workspace-write --cd WT`; `--network` opts in.
  - resume: `exec resume <thread_id> -c sandbox_mode="workspace-write"` (resume has no `--sandbox`).
  - review: `--sandbox read-only --ephemeral --output-schema assets/review-output.schema.json`.
- **Settings.** `--effort` required; `--model` optional (config fallback, no model names in the skill); user policy (attribution, `AGENTS.md`, MCP, auth) inherited.
- **Codex never commits.** Implement requires a clean worktree (ignoring the job's own input files); the orchestrator commits.
- **Review.** Schema and adversarial prompt from `openai/codex-plugin-cc@db52e28` (Apache-2.0). Diff inlined at ≤2 files and ≤256 KB, else Codex gets the `git diff` command. Named risks and test-strength checks live in the prompt.
- **Findings.** User asked: present and stop. Plan asked: fix real ones, report dismissed ones with reasons.
- **Jobs.** Newest 50 per worktree kept; `status` filters by `CLAUDE_CODE_SESSION_ID` when set.
- **Evals.** Each scenario ships a scripted fake `codex`; shared helpers in `evals/support/fake-codex/`.

## Testing Plan

### Logic
- **Argv** matches the table above for every mode and flag; missing `--effort` or input file exits before spawning.
- **State root** follows the lookup order; job dirs are stable per worktree.
- **Usage** comes from the last `turn.completed`; a truncated stream reports "unavailable".

### Behavior
- **Lifecycle** start → status → result → cancel works against a fake; cancel leaves edits.
- **Guards** (missing, logged out, inside Codex, dirty worktree) exit non-zero with the fix.
- **Real CLI** round trip (implement → resume → review) passes in an opt-in e2e test.

### Interface
- **Routing:** fires when Codex is named or plan-assigned; silent for unnamed reviews, reviewing Codex's work yourself, debugging Codex, other models.

## Documentation Plan

- **`skill-conventions.md`**: persistent state, wrapping external CLIs, faking them in evals.
- **`docs/development.md`**: `make test:e2e`.
- **`evals/support/fake-codex/README.md`**: fake layout.
- **`AGENTS.md`, `README.md`, `skills.sh.json`**: add the skill; README notes Codex must be signed in.
- **`docs/evals/delegating-to-codex.md`**: recorded run.

## Out of Scope

- The official plugin, its app-server broker, and its review-gate hook.
- Codex committing or pushing.
- Picking Codex unprompted.
- `codex exec review`: its fixed prompt can't carry brief, report, and risks.

## References

- `openai/codex-plugin-cc@db52e28`: `scripts/lib/state.mjs`, `scripts/lib/git.mjs`, `schemas/review-output.schema.json`, `prompts/adversarial-review.md`.
- openai/codex #7071, #5034; codex-plugin-cc #273, #304 — worktree EPERM, network off.
- Verified on `codex-cli 0.144.1`: exec forces `approval: never`; network off under `workspace-write`; `--strict-config` rejects unknown keys; `exec resume` takes `-c` but not `--sandbox`.

## Verification

- `make test`, `make lint` — green.
- `make evals SKILL=delegating-to-codex EVAL_ARGS="--count 3"` — trial beats baseline; routing passes.
- `make test:e2e` — real round trip passes.
