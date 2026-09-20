# Developing MechaSwift

How to work on the plugin: environment, `make` targets, loading it into Claude Code and Hermes, and how skill evals are laid out and run. Pairs with `AGENTS.md` (working rules) and the authoring references shipped inside the skills themselves.

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) — Python and venv management. `pytest` and `ruff` install through it.
- Claude Code and/or Hermes, to load and trigger the skills.
- **Evals only:** see [Evals](#evals) for the runner install and credentials.

## Commands

| Command | Does |
|---|---|
| `make install` | `uv sync` — creates `.venv` with the `dev` group (pytest, ruff). |
| `make test` | Tests under `tests/`: plugin manifest checks, each skill's script tests, and the Codex contract test (needs `codex` installed; it runs the real binary against a fake API server on localhost — no credentials, no internet). Autoload is off so the benchspec plugin never leaks in. |
| `make test:e2e` | Opt-in end-to-end tests against real external CLIs (today: `codex`, signed in). Skipped by `make test`. |
| `make lint` | `ruff check .` |
| `make format` | `ruff format .` |
| `make evals` | Skill evals, baseline vs trial, in microVMs. `SKILL=to-spec` scopes to `evals/to-spec`; `EVAL_ARGS="-n 6"` adds pytest args. |
| `make evals:lint` | Static lint of eval assertions. No credentials, no sandbox. |
| `make clean` | Remove `.venv` and caches. |

CI (`.github/workflows/ci.yml`) runs `make lint`, `claude plugin validate .`, and `make test` (with a pinned `codex` installed) on every PR and on pushes to `main` and `dev`. Evals never run in CI.

Most tests and every eval use a fake `codex`, so they can't notice when the real CLI changes. The contract test in `make test` covers that, and a nightly workflow reruns it against the latest Codex release.

## Layout of a skill

```
skills/to-spec/
  SKILL.md                     Model-invoked entry point: name + description + thin procedure
  assets/, references/, ...    Templates and docs the skill tells the agent when to load
  scripts/validate_spec.py     Tiny CLI the skill runs (stdlib only)
evals/to-spec/
  <scenario>/eval.md           One output eval: history + prompt + assertions
  <scenario>/workspace/        Starting files for that eval (optional)
  triggers/<query>.eval.md     Routing evals: asks that must reach this skill, one per query
  not-triggers/<query>.eval.md Near-misses that must not, when no other skill owns the ask
tests/skills/
  conftest.py                  Puts every skills/*/scripts/ on sys.path, once for all skills
  to-spec/scripts/
    test_validate_spec.py      Deterministic unit tests, mirroring skills/to-spec/scripts/
docs/evals/to-spec.md          The recorded benchmark from the skill's last eval run
```

Skills ship clean: nothing under `skills/<name>/` but what the agent loads. Evals live beside them under `evals/<name>/`, which is what benchspec walks.

Frontmatter is `name` and `description` only (`tests/test_plugin.py` enforces it). Keep skill prose harness-neutral; the rules are in `skills/writing-agent-skills/references/skill-conventions.md`, and the `writing-agent-skills` skill is the workflow for changing one. Editing a skill without re-running its evals is the same mistake as shipping one without them.

## Testing in Claude Code

Load the plugin from disk for one session, from any directory you want to work in:

```bash
cd /some/project
claude --plugin-dir /path/to/mechaswift
```

- `/plugin` lists the `core` plugin and its skills.
- Trigger a skill with natural language ("spec this out") or by name (`/core:to-spec`).
- `/reload-plugins` picks up `SKILL.md` edits. Restart Claude Code for `plugin.json`, `marketplace.json`, or `hooks/` changes.
- `claude plugin validate --strict .` checks the manifests; `claude plugin validate --strict skills` checks every `SKILL.md`. `claude --plugin-dir . plugin details core` prints the component inventory and projected token cost.

To test the marketplace install path rather than `--plugin-dir`:

```
/plugin marketplace add /path/to/mechaswift
/plugin install core@mechaswift
```

## Testing in Hermes

Hermes loads repo-local skills from `./.agents/skills` in a project you've marked trusted, and `.agents/skills` here is a symlink to `skills/`. So the local loop is:

```bash
cd /path/to/mechaswift
hermes skills trust        # once per checkout
hermes skills list         # the four skills show as project skills
```

Edits to `skills/` are live in the next session. To try a skill against some other project instead, link the skill directories into `~/.hermes/skills/<name>`.

The published path is the tap in the README: `hermes skills tap add theycallmeswift/mechaswift`, then `hermes skills install theycallmeswift/mechaswift/<name>`. Hermes downloads `SKILL.md` and every subdirectory beside it, so `references/`, `assets/`, and `scripts/` arrive intact. Skills installed from a tap go through Hermes's security scan and show its third-party notice on first install.

## Evals

The runner is [benchspec](https://pypi.org/project/benchspec/), a pytest plugin that boots each `(eval × arm)` cell in a microVM and grades the result with deterministic checkers plus an LLM judge. It lives in the opt-in `evals` dependency group so a plain `make install` stays pytest + ruff; the `make evals*` targets sync it on demand with `uv run --group evals`.

**Requirements for a graded run:** an Apple Silicon Mac or Linux with `/dev/kvm`, microsandbox (installed with benchspec), and credentials in `.env` (copy `.env.example`): `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` for the agent and judge, and `GEMINI_API_KEY` for benchspec's assertion binder. The first run builds a VM snapshot (a few minutes); later runs reuse it.

**One eval set**, `default` in `pyproject.toml`: a `baseline` arm runs the agent bare and a `trial` arm runs it with the whole plugin loaded (`harness_args = ["--plugin-dir", "/project"]`, the staged copy of this repo), both on `claude-code` / `sonnet`. No `setup.sh` anywhere — loading the plugin is the install. Two kinds of eval run in it, and they differ only in what they assert:

- **Output evals** (`evals/<skill>/<scenario>/eval.md`) grade the work: the files written and the final message. The delta is what the plugin taught.
- **Routing evals** (`evals/<skill>/triggers/` and `not-triggers/`) are the same format with the verbatim user ask as the prompt and one `` Skill `X` invoked `` / `` not invoked `` line per skill that has a stake in it, graded deterministically from the agent's dispatches. Every query lives once, under the skill it should route to (`triggers/`) or, when no skill in the plugin owns it, under the first skill whose suite listed it as a near-miss (`not-triggers/`); a later skill that shares the vocabulary adds its own line to that file rather than duplicating the query, since benchspec keys evals on (folder, file stem) across the whole run. On the trial arm every description competes with its real peers. Every activation line carries `- if: {BENCHSPEC_ARM} != "baseline"`: an uninstalled skill can't fire, so grading it on baseline would inflate the Δ. Positives that presuppose a prior design discussion carry a short `history:` recap so the ask refers to something.

`SKILL=<name>` narrows discovery to `evals/<name>`; `EVAL_ARGS="-k <scenario>"` narrows further.

**Authoring loop.** `make evals:lint` is free and static. `uv run --group evals benchspec analyze` asks the binder which assertions grade deterministically. `make evals SKILL=<name> EVAL_ARGS="--collect-only -q"` lists the cells without spawning anything — do this before any run broader than one eval, because every cell is a VM boot plus an agent call, and every punted assertion is a judge call. The format reference is `docs/writing-evals.md` in the benchspec repo; the design methodology (scenarios, discriminating assertions, RED → GREEN → REFACTOR) is `skills/writing-agent-skills/references/evaluating-skills.md`.

**Recording results.** Runs write `tmp/evals/iteration_NN/benchmark.md` (git-ignored). When a skill lands or changes, copy that report to `docs/evals/<skill>.md` so the last measured baseline and delta travel with the repo.

## Further reading

- `AGENTS.md` — working rules for agents editing this repo.
- `skills/writing-agent-skills/references/skill-conventions.md` — frontmatter, layout, portability, discipline patterns.
- `skills/writing-agent-skills/references/evaluating-skills.md` — eval design: scenarios, assertions, RED → GREEN → REFACTOR.
- `skills/writing-prompts/references/agent-md.md` — how `AGENTS.md` / `CLAUDE.md` should be written.
