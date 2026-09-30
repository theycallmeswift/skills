# Running evals

Execution, grading, and aggregation reference for the `benchspec` runner (a pytest plugin
driven through `make evals` and `make evals:lint`). Covers the honesty contract, clean-room
isolation, binder-plus-judge grading, routing evals, the +20pp rule, and the analyst pass.

For eval *design* (scenario selection, assertion writing, eval-first discipline) see
[`evaluating-skills.md`](evaluating-skills.md). For the runner's own reference — every config
key, flag, and exit code — see `docs/` in the benchspec repo.

---

## Contents

- [Honesty contract](#honesty-contract)
- [How the runner works](#how-the-runner-works)
- [Grading — binder, then judge](#grading--binder-then-judge)
- [Routing evals — real routing](#routing-evals--real-routing)
- [Aggregation and the +20pp rule](#aggregation-and-the-20pp-rule)
- [Analyst pass](#analyst-pass)
- [CLI usage](#cli-usage)

---

## Honesty contract

An honest eval is one where the baseline can't reproduce the skill's conventions by reading
the surrounding project. The runner enforces it:

1. **Every arm starts from the same clean room.** Each `(eval, arm)` cell boots a microVM
   from a cached agent-ready snapshot, with the agent's working directory `/workspace` seeded
   from only the eval's `workspace/`. Both arms boot from the identical snapshot; the sole
   asymmetry is that the `trial` arm loads the plugin.
2. **The VM is the containment boundary.** The agent runs with permissions bypassed — all
   writes and Bash commands allowed — but nothing escapes the VM. Provider credentials are
   injected at the network boundary, never as readable environment variables in the guest.

   **Requirements:** a supported host (Apple Silicon or Linux with KVM), microsandbox
   (installed with benchspec through the `evals` dependency group), and credentials in a repo-root `.env`:
   `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) or `ANTHROPIC_API_KEY` for the agent
   and judge, plus `GEMINI_API_KEY` for the binder. Preflight fails fast if any are unmet.
3. **No placeholder reaches either arm.** Eval prompts must be self-contained. `{TODAY}` is the
   one substitution (the host's UTC date, applied to prompt, history, assertions, and
   workspace file names and contents); any other `{UPPERCASE}` token is rejected before the
   agent runs.
4. **`/project` is identical for every arm; loading it is the only asymmetry.** A staged copy
   of the repo — what a clone would contain, never `.env`, `.git`, or earlier runs' artifacts —
   is mounted read-only at `/project` for every cell. The `trial` arm runs the agent with
   `--plugin-dir /project`, so the whole plugin (every skill, plus the session hook) is what
   it measures; `baseline` runs the agent bare. There is no per-eval install script. Sibling
   skills are always present on trial, so assertions that require invoking another skill are
   satisfiable.
5. **Loaded is not invoked — activation is graded, not gated.** An agent can have the skill
   installed yet hand-roll the task; then the trial arm secretly measures the no-skill path and
   the delta is meaningless. So every arm records its dispatched skills, and activation is an
   ordinary assertion — `` Skill `<name>` invoked `` — graded deterministically off that set:
   True where the skill fired, False where it didn't. A trial arm that fails its own activation
   line is a routing finding, not a weak skill.

Why this matters: a tempting shortcut is running baselines as in-session subagents whose cwd is
the project worktree. They read the project's `docs/` and `skills/<name>/` and reproduce the
conventions the skill exists to teach — collapsing the delta to ~zero. An honest baseline is a
fresh agent process in a clean room outside the project.

---

## How the runner works

benchspec is a pytest plugin. It walks the configured search path (`evals/` here) for
`eval.md` / `*.eval.md` files, keys each on `(group, eval_id)` — the parent folder and the
file stem — and parametrizes one `test_eval` over `(eval × arm)`, the unit of parallelism.
Arms come from the one eval set in `pyproject.toml` (`[tool.benchspec.sets.default]`):
`baseline` bare, `trial` with `--plugin-dir /project`.

**For each `(eval, arm)` cell:**

1. The eval's `workspace/` is copied to a fresh host temp dir outside the project and mounted
   at `/workspace`; the SHA-256 of every seeded file is recorded for byte-identity assertions.
2. The staged repo mounts read-only at `/project`; on `trial` the agent is launched with it
   as a plugin directory. benchspec also runs a `setup.sh` from the eval folder if one exists;
   this plugin has none, since loading the plugin is the install.
3. The agent runs on the eval's prompt (any `history:` turns are rendered as a transcript
   prefix), streaming a trajectory from which the dispatched skills are read back.
4. The facts are collected — file tree, contents, SHA-256s, the final message, the tool and
   skill calls — and every assertion is graded (next section).
5. Artifacts land under `tmp/evals/iteration_NN/skills/<group>/eval-<eval_id>/<arm>/sample-K/`
   (`grading.json`, `timing.json`, `transcript.json`, `provenance.json`, `session.jsonl`), with
   `meta.json`, `index.jsonl`, `benchmark.json`, and `benchmark.md` at the iteration root.

**Pass, fail, error.** A cell's pytest outcome is about infrastructure: it passes when the agent
ran and grading completed, and *errors* (excluded from pass rates, surfaced through the
`errored` flag and the report) when the agent CLI crashed or timed out or the judge failed at
the transport level. A *failed* assertion is a measurement, not a test failure: the agent ran
and the claim did not hold. Assertion results feed the benchmark; the only gate is
`--fail-under`, which fails the run when a non-baseline arm's raw delta drops below the
threshold in any group. The baseline arm's misses are the desired signal, not a bug.

**Iteration numbering** auto-increments (`iteration_01`, `iteration_02`, …), chosen once per
run and shared across `-n` workers. The workspace is ephemeral and gitignored under `tmp/`.
The first run builds the agent-ready VM snapshot under a file lock
(`tmp/.benchspec-snapshot-<name>.lock`); later runs reuse it until the harness version, the
base image, or the environment script changes.

---

## Grading — binder, then judge

Every assertion takes one of two paths, decided per line at grade time by the **binder**, a
fixed Gemini call (hence `GEMINI_API_KEY`):

- **Bind**: the prose maps to one deterministic checker, run on the host against the final
  workspace or the run's process facts. Zero variance, zero judge cost.
- **Punt**: everything else goes to the **judge** — the configured judge harness run on the
  host (`[tool.benchspec.judge]`; default Claude Code on `sonnet`, and benchspec's advice for
  published numbers is a judge from a different model family than the arms) — which receives the assertion list, the workdir file tree,
  relevant file contents, the runner-computed SHA-256s, the agent's final message, and the
  dispatched tools and skills, and emits a structured verdict per assertion reasoning only
  from that evidence. All of a cell's punted lines go to the judge in one call.

Checkers the binder can emit: `file_exists` / `not_file_exists`, `glob_count`, `regex`,
`frontmatter_has`, `sha256_match`, `skill_invoked` / `not_skill_invoked`. The binder is tuned
so a false positive — a surface check passing on wrong output — is the one unacceptable
error; anything doubtful punts. Persistence and negation claims ("still present", "not
duplicated") always punt; an explicit byte-identity claim binds to `sha256_match`.

**`grading.json` shape:**

```json
{
  "eval_id": "your-eval-id",
  "skill": "your-group",
  "arm": "trial",
  "sample": 0,
  "errored": false,
  "binder_degraded": 0,
  "assertions": [
    {"text": "the assertion text", "passed": true, "evidence": "quoted from the output", "type": "deterministic"},
    {"text": "another assertion", "passed": false, "evidence": "output says X, not Y", "type": "semantic"}
  ]
}
```

`skill` is the group (the eval's parent folder). `errored` flags an infra failure (excluded
from the benchmark) versus an honest assertion miss; `binder_degraded` counts lines the binder
could not classify and handed to the judge. Beside it sit `timing.json` (duration, judge time,
token split), `transcript.json` (prompt, result, tool count, workdir tree, skills dispatched),
`provenance.json` (the agent version observed in the guest, the snapshot), and `session.jsonl`
(the raw stream). There is no separate shared-assertion checklist — fold session-level claims into the
single `## Assertions` list, and put any lead-up the assertion depends on into `history:`.

---

## Routing evals — real routing

Tests whether the `description:` fires the skill via real routing, not a judge's prediction.
There is no separate trigger-eval format: a routing eval is an ordinary eval whose prompt is
the verbatim user query and whose assertions are activation lines, one per skill with a stake
in the ask — `` Skill `<name>` invoked `` for the skill it should reach, `` Skill `<other>` not
invoked `` for a sibling that shares the vocabulary. A namespaced dispatch (`core:to-spec`)
satisfies a line written against `to-spec`. A query lives once: under `evals/<skill>/triggers/` for the skill it should reach, or
under `not-triggers/` of the first skill that listed it as a near-miss when no loaded skill owns
it. A later skill that shares the vocabulary adds its own line to that file instead of duplicating
the query, because benchspec keys every eval on (folder, file stem) across the whole run.

They run in the same set as everything else. On `trial` the whole plugin is loaded, so the
skill competes against its real peers (hook included). Each activation line carries
`- if: {BENCHSPEC_ARM} != "baseline"`, since an uninstalled skill can't fire on `baseline`. A positive that
presupposes a prior design discussion carries a short `history:` recap, because in an empty
session the agent correctly says there is nothing to write up rather than routing.

`make evals SKILL=<name>` runs one skill's suite; `EVAL_ARGS="-k <slug> --count 3"` samples
a query that looks flaky. Cap at 10 queries; see [`evaluating-skills.md`](evaluating-skills.md) § Routing evals.
Routing is a model-tier decision: a query that routes on opus and misses on sonnet is a
boundary to record in the skill's eval notes, not a description defect.

---

## Aggregation and the +20pp rule

When the run finishes the runner writes `benchmark.{json,md}` and prints the report path.
The headline is one line per non-baseline arm — `baseline 72% → trial 86% (+14pp)` — with a
noise band once every arm has at least two samples (`--count 2` or more); the matrix below it has one row
per `group/eval_id` and one column per arm, baseline first, each trial cell showing its rate
and delta. Per-arm sections carry harness, model, tokens, and duration.

**Per-sample aggregation.** Under `--count N`, every `(eval × sample)` pair contributes one
observation. `benchmark.md` flags a delta that sits `within noise`; trust small deltas only
after sampling.

**The +20pp rule.** If with-skill doesn't beat baseline by roughly +20 percentage points on
the skill's core scenarios, cut content rather than add. A skill that can't noticeably
outperform no-skill is context noise.

---

## Analyst pass

Read the benchmark critically, not just the pass rates:

- **Assertions that pass regardless of skill** — not discriminating; rewrite or drop.
- **High run-to-run variance** — flaky scenario, weak assertion, or genuine instability. Sample
  with `--count N -n N` (pytest-repeat + xdist) to quantify it.
- **Time/token deltas pointing the wrong way** — quality up, cost up disproportionately; flag
  the tradeoff.

Aggregate pass rates hide things worth knowing. Do this before calling a skill done.

---

## CLI usage

Run from the project root via the `make` targets, which wrap `benchspec run` with the right
set and group filter. `SKILL=<name>` narrows discovery to that skill's tree; everything in
`EVAL_ARGS` goes to pytest verbatim.

```
make evals SKILL=<name> [EVAL_ARGS="…"]      # the skill's evals, baseline vs trial
make evals:lint                               # static assertion lint, free
uv run --group evals benchspec analyze   # which assertions bind vs. punt (Gemini)
```

Useful pytest args for `EVAL_ARGS`:

```
  --collect-only -q    # print the plan, spawn nothing — always first for anything broad
  -k EXPR              # select by test id substring: test_eval[<group>-<eval_id>-<arm>]
  -x | --maxfail N     # stop after first / N failing cells
  -n N                 # parallel microVMs (pytest-xdist)
  --count N            # N samples per cell (pytest-repeat); benchmark surfaces noise
```

Pass runner flags through the same variable: `--benchspec-model haiku` overrides the set's
task model for every inheriting arm (both arms move, so the delta stays real);
`--benchspec-set NAME` picks another set; `--benchspec-config FILE` layers a scratch set;
`--benchspec-fail-under PP` turns the run into a gate. Exit codes: 0 clean, 1 a lint finding
or an errored cell or a tripped gate, 2 a usage or preflight error before anything ran, 5
no evals discovered.

| Want | Invocation |
|---|---|
| Everything for one skill | `make evals SKILL=to-spec` |
| A single eval | `make evals SKILL=to-spec EVAL_ARGS="-k spec-from-context"` |
| One eval, trial arm only | `make evals SKILL=to-spec EVAL_ARGS="-k 'spec-from-context and trial'"` |
| Baseline (bare agent) only | `make evals SKILL=to-spec EVAL_ARGS="-k baseline"` |
| Repeat one eval 5× in parallel | `make evals SKILL=to-spec EVAL_ARGS="-k spec-from-context --count 5 -n 5"` |
| Routing evals only | `make evals SKILL=to-spec EVAL_ARGS="-k 'not (spec-from-context or too-thin-defers or under-determined-open-questions)'"` — or name the query slugs |
| Everything on haiku | `make evals SKILL=to-spec EVAL_ARGS="--benchspec-model haiku"` |

**Always `--collect-only` first** for scope broader than a single eval — it lists the cells
pytest will run and spawns nothing. Confirm the count (each cell is one VM boot plus one agent
run, plus a judge call for every punted assertion) before launching; broad runs are expensive.
