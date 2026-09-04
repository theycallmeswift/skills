# Running evals

Execution, grading, and aggregation reference for the `harnessbench` runner (a pytest plugin
driven through `make evals` and `make evals:lint`). Covers the honesty contract, clean-room
isolation, binder-plus-judge grading, routing evals, the +20pp rule, and the analyst pass.

For eval *design* (scenario selection, assertion writing, eval-first discipline) see
[`evaluating-skills.md`](evaluating-skills.md). For the runner's own reference — every config
key, flag, and exit code — see `docs/` in the harnessbench repo.

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
   (installed with harnessbench by `make evals:install`), and credentials in a repo-root `.env`:
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

harnessbench is a pytest plugin. It walks the configured search path (`evals/` here) for
`eval.md` / `*.eval.md` files, keys each on `(group, eval_id)` — the parent folder and the
file stem — and parametrizes one `test_eval` over `(eval × arm)`, the unit of parallelism.
Arms come from the one eval set in `pyproject.toml` (`[tool.harnessbench.sets.default]`):
`baseline` bare, `trial` with `--plugin-dir /project`.

**For each `(eval, arm)` cell:**

1. The eval's `workspace/` is copied to a fresh host temp dir outside the project and mounted
   at `/workspace`; the SHA-256 of every seeded file is recorded for byte-identity assertions.
2. The staged repo mounts read-only at `/project`; on `trial` the agent is launched with it
   as a plugin directory.
3. The agent runs on the eval's prompt (any `history:` turns are rendered as a transcript
   prefix), streaming a trajectory from which the dispatched skills are read back.
4. The facts are collected — file tree, contents, SHA-256s, the final message, the tool and
   skill calls — and every assertion is graded (next section).
5. Artifacts land under `tmp/evals/iteration_NN/skills/<group>/eval-<eval_id>/<arm>/sample-K/`
   (`grading.json`, `timing.json`, `transcript.json`, `provenance.json`, `session.jsonl`), with
   `meta.json`, `index.jsonl`, `benchmark.json`, and `benchmark.md` at the iteration root.

**Pass/fail.** A cell passes when every assertion passes — including activation, so an agent
that hand-rolled the task fails on that line and the delta stays meaningful. The baseline arm's
failures are the desired signal, not a bug; both arms feed the delta.

**Iteration numbering** auto-increments (`iteration_01`, `iteration_02`, …), chosen once per
run and shared across `-n` workers. The workspace is ephemeral and gitignored under `tmp/`.

---

## Grading — binder, then judge

Every assertion takes one of two paths, decided per line at grade time by the **binder**, a
fixed Gemini call (hence `GEMINI_API_KEY`):

- **Bind**: the prose maps to one deterministic checker, run on the host against the final
  workspace or the run's process facts. Zero variance, zero judge cost.
- **Punt**: everything else goes to the **judge** — a separate `claude -p` on the host, no
  plugin, no cwd constraint — which receives the assertion list, the workdir file tree,
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
  "group": "your-eval-id",
  "arm": "trial",
  "sample": 0,
  "errored": false,
  "assertions": [
    {"text": "the assertion text", "passed": true, "evidence": "quoted from the output", "type": "deterministic"},
    {"text": "another assertion", "passed": false, "evidence": "output says X, not Y", "type": "semantic"}
  ]
}
```

`errored` flags an infra failure (excluded from the benchmark) versus an honest assertion
miss. There is no separate shared-assertion checklist — fold session-level claims into the
single `## Assertions` list, and put any lead-up the assertion depends on into `history:`.

---

## Routing evals — real routing

Tests whether the `description:` fires the skill via real routing, not a judge's prediction.
There is no separate trigger-eval format: a routing eval is an ordinary eval whose prompt is
the verbatim user query and whose only assertion is the activation line —
`` Skill `<name>` invoked `` for a should-trigger query, `` Skill `<name>` not invoked `` for a
near-miss. They live as sibling files `evals/<skill>/<query-slug>.eval.md`, so the group is
the skill name and a slug shared with another skill's suite doesn't collide.

They run in the same set as everything else. On `trial` the whole plugin is loaded, so the
skill competes against its real peers (hook included); the `baseline` column is
uninformative — an uninstalled skill can't fire — and just rides along. A positive that
presupposes a prior design discussion carries a short `history:` recap, because in an empty
session the agent correctly says there is nothing to write up rather than routing.

`make evals SKILL=<name>` runs one skill's suite; `EVAL_ARGS="-k <slug> --count 3"` samples
a query that looks flaky. Build 20 queries, ≈50/50 should-trigger / should-not, weighted
toward near-miss negatives (share the skill's vocabulary but need different handling).
Routing is a model-tier decision: a query that routes on opus and misses on sonnet is a
boundary to record in the skill's eval notes, not a description defect.

---

## Aggregation and the +20pp rule

When the run finishes the runner writes `benchmark.{json,md}` and prints the report path.
The headline is one line per non-baseline arm — `baseline 72% → trial 86% (+14pp)` — with a
noise band when the run has enough samples to compute one; the matrix below it has one row
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

Run from the project root via the `make` targets, which wrap `harnessbench run` with the right
set and group filter. `SKILL=<name>` narrows discovery to that skill's tree; everything in
`EVAL_ARGS` goes to pytest verbatim.

```
make evals SKILL=<name> [EVAL_ARGS="…"]      # the skill's evals, baseline vs trial
make evals:lint                               # static assertion lint, free
uv run --no-sync harnessbench analyze     # which assertions bind vs. punt (Gemini)
```

Useful pytest args for `EVAL_ARGS`:

```
  --collect-only -q    # print the plan, spawn nothing — always first for anything broad
  -k EXPR              # select by test id substring: test_eval[<group>-<eval_id>-<arm>]
  -x | --maxfail N     # stop after first / N failing cells
  -n N                 # parallel microVMs (pytest-xdist)
  --count N            # N samples per cell (pytest-repeat); benchmark surfaces noise
```

Pass runner flags through the same variable: `--harnessbench-model haiku` overrides the set's
task model for every inheriting arm (both arms move, so the delta stays real);
`--harnessbench-set NAME` picks another set; `--harnessbench-config FILE` layers a scratch set.

| Want | Invocation |
|---|---|
| Everything for one skill | `make evals SKILL=to-spec` |
| A single eval | `make evals SKILL=to-spec EVAL_ARGS="-k spec-from-context"` |
| One eval, trial arm only | `make evals SKILL=to-spec EVAL_ARGS="-k 'spec-from-context and trial'"` |
| Baseline (bare agent) only | `make evals SKILL=to-spec EVAL_ARGS="-k baseline"` |
| Repeat one eval 5× in parallel | `make evals SKILL=to-spec EVAL_ARGS="-k spec-from-context --count 5 -n 5"` |
| Routing evals only | `make evals SKILL=to-spec EVAL_ARGS="-k 'not (spec-from-context or too-thin-defers or under-determined-open-questions)'"` — or name the query slugs |
| Everything on haiku | `make evals SKILL=to-spec EVAL_ARGS="--harnessbench-model haiku"` |

**Always `--collect-only` first** for scope broader than a single eval — it lists the cells
pytest will run and spawns nothing. Confirm the count (each cell is one VM boot plus one agent
run, plus a judge call for every punted assertion) before launching; broad runs are expensive.
