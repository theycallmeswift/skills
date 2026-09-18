**TL;DR** — Add a harness-neutral `delegating-to-codex` skill whose job-manager script hands implementation and review tasks to `codex exec`, so an orchestrator can use a second model family without a Claude-only plugin or a hand-rolled shell recipe.

## Problem

- **Symptom:** Delegating to Codex today means a hand-copied shell recipe: raw `codex exec` flags, prompt assembly with `cat`, and `--add-dir` workarounds so Codex can commit inside linked worktrees. No skill in `skills/` covers it, and the only Codex mention in the repo is `skills/writing-prompts/references/agent-md.md:3`.
- **Exposed by:** Another agent's temporary recipe worked, and its process rules proved valuable. For example, a review with only the brief and the diff caught 0 of 10 findings. Its mechanics are fragile, though: effort falls back to whatever the user's config says (`ultra` on Swift's machine), and making `.git` writable lets Codex plant git hooks that later run outside the sandbox.
- **Why not the official plugin:** `openai/codex-plugin-cc` is built from Claude Code commands, a Node helper, an app-server broker and hooks. None of that carries over to Hermes. It also hardcodes network off in write mode, and linked-worktree commits are still an open issue there (#273).
- **Scope:** One skill with two modes, **implement** (Codex edits the worktree) and **review** (Codex returns structured findings), plus a job manager for long-running work.
- **Constraint:** `SKILL.md` prose must be harness-neutral, with Claude and Hermes setup in `docs/development.md` (`AGENTS.md`). Frontmatter is `name` and `description` only. The eval VM has no `codex` binary and no OpenAI credentials.

## Solution

```bash
python skills/delegating-to-codex/scripts/codex_run.py start implement --effort high \
  --brief brief.md --context ctx.md --risks risks.md            # -> job id
python skills/delegating-to-codex/scripts/codex_run.py status
python skills/delegating-to-codex/scripts/codex_run.py result <id>   # last message + usage
python skills/delegating-to-codex/scripts/codex_run.py start implement --resume <id> --effort high --brief fixes.md
python skills/delegating-to-codex/scripts/codex_run.py start review --effort low --base main --brief brief.md --report report.md --risks risks.md
```

The script builds and runs every `codex exec` call, keeps job state outside the repo, and returns review findings in the official plugin's JSON schema. `SKILL.md` carries the process rules that made delegation work: named risks go to the implementer up front, reviews cross model families, reviewers run their own mutation checks, and the orchestrator commits.

## User Stories

1. As an orchestrator executing a plan, I want **to hand a task marked "Implementer: Codex" to Codex in the background**, so I can keep working while it edits the worktree.
2. As an orchestrator, I want **to send review findings back into the same Codex thread**, so fix rounds don't re-pay for the full context.
3. As an orchestrator, I want **review findings as schema-valid JSON**, so I can sort by severity and check each file:line without parsing prose.
4. As Swift, I want **"have codex review this" to show me the findings and stop**, so I decide what gets fixed.
5. As Swift, I want **my Codex config's policy settings (attribution, AGENTS.md, MCP, auth) respected while effort is chosen per task**, so an `ultra` default never silently drives a cheap review.
6. As a Hermes user, I want **the same skill and script to work without Claude-only env vars**, so one `skills/` tree serves both harnesses.
7. As a future skill author, I want **a documented lookup order for persistent state dirs**, so the next skill that stores state doesn't reinvent it.

## Implementation Decisions

```
SKILL.md (trigger: user names Codex | plan assigns Codex)
  └─► codex_run.py preflight ── `codex` on PATH? `codex login status` ok? CODEX_THREAD_ID unset?
        └─► state_dir()  CLAUDE_PLUGIN_DATA → HERMES_HOME/mechaswift → XDG_STATE_HOME → ~/.local/state
              └─► <root>/mechaswift/codex-jobs/<repo>-<sha256(worktree root)[:16]>/<job-id>/
                    prompt.md  events.jsonl  last.md  meta.json(mode, pid, thread_id, status, usage, session)
        └─► build_prompt(mode, files)  ── missing input file → exit non-zero
        └─► build_argv(mode, flags)
              implement: codex exec --sandbox workspace-write --cd WT --json --strict-config
                         -c model_reasoning_effort=E [-c service_tier=T] [-m M]
                         [-c sandbox_workspace_write.network_access=true] -o last.md -
              resume:    codex exec resume <thread_id> --json --strict-config
                         -c sandbox_mode="workspace-write" -c model_reasoning_effort=E ... -o last.md -
              review:    codex exec --sandbox read-only --ephemeral --cd WT --json --strict-config
                         -c model_reasoning_effort=E --output-schema assets/review-output.schema.json -o last.md -
        └─► spawn detached, stdout → events.jsonl ; exit → meta.status, usage from last `turn.completed`
  status | result <id> | cancel <id>  ── read or kill from meta.json; cancel leaves edits in place
```

- **Job manager, not a synchronous wrapper.** `start`, `status`, `result` and `cancel` subcommands, modeled on the official plugin's companion script.
  - `start` detaches the Codex process and prints the job id immediately.
  - `result` prints `last.md` plus a one-line token summary taken from the final `turn.completed` event (`input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_output_tokens`).
  - The 50 newest jobs per worktree are kept and older ones are pruned, as the plugin's `MAX_JOBS` does.
- **State dir: the best information available wins.** A single `state_dir()` function is the script's only harness-specific branch.
  - `CLAUDE_PLUGIN_DATA` (Claude Code's persistent plugin dir), then `$HERMES_HOME/mechaswift`, then `$XDG_STATE_HOME`, then `~/.local/state`. Codex and OpenCode expose no data-dir variable to subprocesses; OpenCode follows XDG.
  - Jobs are keyed by a hash of the worktree root, as the plugin does. `status` shows only the current session's jobs when `CLAUDE_CODE_SESSION_ID` is set; `result` and `cancel` accept any id.
- **Task settings explicit, user policy inherited.**
  - `--effort` is required, and a call without it is an error. `SKILL.md` guidance: implement normally `high`, review normally `low`, raise effort for risky diffs.
  - `--model` is optional; when omitted, Codex resolves the model from config. `SKILL.md` never names models.
  - `--tier` passes `service_tier`. `--network` opts into network access (implement only).
  - `--strict-config` is always passed, so a mistyped `-c` setting fails the run. A mistyped `service_tier` value still only warns, which is Codex behavior.
  - `--ignore-user-config` is never passed. Attribution, `AGENTS.md`, MCP servers, auth and profiles come from the user's Codex setup.
- **Codex only edits; the orchestrator commits.** Implement mode never makes `.git` or tool caches writable, so the recipe's `--add-dir "$GIT_COMMON"` and hook-escape risk go away. The orchestrator inspects `git status`, re-runs the test gate itself and makes the commit.
- **Fix loops resume by default.** `--resume <job-id>` runs `codex exec resume <thread_id>`, with the thread id taken from the `thread.started` event in `meta.json`. Resume has no `--sandbox` flag, so the sandbox is set through `-c sandbox_mode=…`. `--fresh` opts out and starts a new thread.
- **Review follows Codex's own conventions.**
  - Output: `assets/review-output.schema.json`, copied verbatim from `openai/codex-plugin-cc@db52e28` (Apache-2.0, attribution kept). It has verdict `approve|needs-attention` and severity `critical|high|medium|low`.
  - Stance: adapted from the plugin's `prompts/adversarial-review.md` into `assets/review-prompt.md`.
  - Inputs, assembled in order with fail-loud checks: brief, implementer report, named risks, optional extra rules, and the diff. Codex reads the project's `AGENTS.md` natively, so rules are extra only.
  - The diff is pasted inline only for 2 files or fewer and 256 KB or less, as the plugin does. Otherwise the prompt tells Codex to inspect `git diff $(git merge-base HEAD <base>)` with read-only git.
  - Named risks and the mutation-check instruction live in the prompt. Failures come back as ordinary findings.
- **Findings handling depends on the trigger** (`SKILL.md`).
  - When the user asked directly: present the findings, stop, and ask which to fix, as in the plugin's `codex-result-handling`.
  - When a plan step triggered it: the orchestrator verifies each finding against the code, fixes the ones that hold, and reports the dismissed ones with a reason.
- **Process rules carried from the recipe into `SKILL.md`:**
  - Named risks go into the implementer's context when the task is dispatched.
  - When a risk depends on code outside the diff, the full text of that function goes into the risks file.
  - The model family that wrote the code never reviews first.
  - Reviewers redo mutation checks: change one thing, run one test, undo it with an inverse edit (never `git checkout`, `restore` or `stash`), and end with `git status`.
  - Every test must answer "does this fail against the implementation it rules out?"
  - The orchestrator re-runs the test gate before accepting a result as done.
- **Guards.**
  - Preflight fails fast with the fix when `codex` is missing or logged out.
  - The script refuses to run when `CODEX_THREAD_ID` is set (already inside Codex), which prevents self-delegation through the `.agents/skills` symlink.
  - Implement mode requires a clean worktree before it starts.
- **Layout.**
  - `skills/delegating-to-codex/SKILL.md` includes a `## Workspace root` section and honors `PROJECT_ROOT`.
  - `scripts/codex_run.py` uses the standard library only.
  - `assets/review-output.schema.json`, `assets/review-prompt.md` and `assets/implement-prompt.md`.
  - Tests go under `tests/skills/delegating-to-codex/scripts/`.
  - Evals go under `evals/delegating-to-codex/`, with a fake `codex` in each scenario's `workspace/` that records its arguments and emits canned JSONL.

## Testing Plan

### Logic
- **Command building** — every mode, flag combination and override produces the exact `codex` argv in the diagram. A missing `--effort` or input file exits non-zero before anything is spawned.
- **State-dir resolution** — the lookup order above holds for every combination of set and unset env vars, and job dirs are stable per worktree root.
- **Prompt assembly** — sections appear in a fixed order, and the diff is inlined only under the size thresholds.
- **Usage parsing** — the final `turn.completed` in a JSONL stream yields the four token counts. A truncated stream yields a clear "no usage" result rather than a crash.
- **Pruning** — never more than 50 jobs per worktree, and newest jobs survive.

### Behavior
- **Job lifecycle against a fake `codex`** — `start`, then `status` (running), then `result` (done, with last message and usage). `cancel` kills the process, marks the job `cancelled` and leaves worktree edits intact. `--resume` reuses the recorded thread id.
- **Guards fire for real** — a missing binary, a logged-out stub, `CODEX_THREAD_ID` set, or a dirty worktree in implement mode each exits non-zero with a remediation message.
- **The agent follows the skill end to end** — given a plan step assigning Codex, it starts a job with explicit effort, never commits from Codex's side, and commits only after re-running the tests. Given "have codex review this", it presents the findings and stops.

### Interface
- **Trigger routing** — fires when the user names Codex or a plan assigns work to it. Does not fire on a generic "review my branch", on requests to use Codex's own CLI features, or on to-spec and writing-plans phrasings.

## Documentation Plan

- **`skills/writing-agent-skills/references/skill-conventions.md`**: new "Persistent state" section covering the harness env-var lookup order, per-worktree keying, never storing state in the skill dir, and the "task settings explicit, user policy inherited" rule for wrapping external CLIs.
- **`AGENTS.md`**: add a `delegating-to-codex` bullet under Skills.
- **`README.md`**: add a skill entry with example phrasings.
- **`skills.sh.json`**: add the skill to a new "Delegation" grouping.
- **`docs/development.md`**: Codex prerequisites (`codex` on PATH, `codex login`), where job state lands under Claude Code and under Hermes, and the fake-`codex` eval pattern.
- **`docs/evals/delegating-to-codex.md`**: the recorded baseline once the first graded run lands.

## Out of Scope

- **Adopting `openai/codex-plugin-cc`,** its app-server protocol or broker: it only works in Claude Code.
- **Codex committing or pushing:** this removes the `.git` write access and the hook-escape risk that comes with it.
- **The plugin's review-gate Stop hook:** it can loop and burn usage, and it's harness-specific.
- **Hardcoded model names:** they go stale, and the config's model is the fallback.
- **Choosing Codex without being asked:** the skill fires only on an explicit user or plan assignment.
- **A native `codex exec review` mode:** its fixed prompt can't carry the brief, report and named risks.
- **A custom review schema:** named-risk and mutation results ride inside the standard findings.

## References

- `openai/codex-plugin-cc@db52e28` — `plugins/codex/scripts/lib/state.mjs` (state dir, `MAX_JOBS = 50`), `scripts/lib/git.mjs` (review scope and inline-diff thresholds), `schemas/review-output.schema.json`, `prompts/adversarial-review.md`, `skills/codex-cli-runtime/SKILL.md:21` (effort left unset unless asked).
- openai/codex #7071 and #5034, codex-plugin-cc #273 and #304 — the linked-worktree `index.lock` EPERM and network-off issues that the orchestrator-commits decision sidesteps.
- Local verification against `codex-cli 0.144.1`, recorded in this session:
  - `approval: never` is forced in `exec`.
  - Network is off under `workspace-write`, and `sandbox_workspace_write.network_access=true` turns it on.
  - Commits from a linked worktree fail with EPERM on `index.lock` without write access to the git common dir.
  - `turn.completed` has the usage shape above.
  - `--strict-config` rejects unknown keys.
  - `codex exec resume` accepts `-c` but not `--sandbox`.
- `docs/specs/2026-09-04-skills-plugin-bootstrap.md` — one `skills/` tree installs unchanged in Claude Code and Hermes.
- `skills/writing-agent-skills/references/skill-conventions.md` ("Script invocation", "Workspace root", "Harness portability") — invocation path, `PROJECT_ROOT`, and the single-decision-point rule.
- `skills/to-spec/scripts/validate_spec.py` + `tests/skills/conftest.py` — the existing script and test pattern to mirror.

## Verification

- `make test` — script logic, lifecycle and guard tests pass alongside the existing suite, including the `skills.sh.json` groupings check.
- `make lint` — ruff is clean on the new script and tests.
- `make evals:lint` — the new eval files are well-formed.
- `make evals SKILL=delegating-to-codex` — trial beats baseline on the output evals, and the trigger and not-trigger routing evals pass.
- A manual smoke test in a real linked worktree with an authenticated `codex`: a `start implement` → `result` → `start implement --resume` → `start review` round trip completes, leaves `.git` untouched by Codex, and returns schema-valid review JSON.
