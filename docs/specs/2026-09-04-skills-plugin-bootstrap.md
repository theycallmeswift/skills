**TL;DR** — Bootstrap `main` as an installable plugin for Claude Code and Hermes: one infrastructure PR (manifests, hook, tooling, docs), then one stacked PR per skill (`writing-prompts` → `writing-agent-skills` → `to-spec` → `interview-me`) that lifts the skill from the knowledge-base repo, migrates its evals to harnessbench, and lands with passing tests and a recorded baseline.

## Problem

- **Symptom:** `main` is a "Hello World" commit with a README that promises skills, a marketplace install, and an eval harness, none of which exist on the branch.
- **Scope:** the four skills live in `~/dev/knowledge-base/skills/`, a repo whose purpose is a PARA vault; the design and authoring skills are general-purpose and belong in the personal agent framework instead.
- **Constraint:** the skills must install unchanged in two harnesses. Claude Code wants `.claude-plugin/plugin.json` and a root `skills/` tree; Hermes wants a GitHub repo with `skills/<name>/SKILL.md` and reads subdirectories beside it. Both read the same tree, so a single layout works.
- **Constraint:** the skills' eval suites and eval-facing references target `evalspec`, which has since become `harnessbench` (private, pre-release, with a changed eval file format). Each skill has to land with its evals migrated and actually run, not carried over as dead files.
- **Constraint:** the skills depend on each other — `writing-agent-skills` installs `writing-prompts` as a sub-skill, and `interview-me`'s handoff eval targets `to-spec` — so they land in dependency order.

## Solution

```
PR 1  infra:  .claude-plugin/ hooks/ pyproject.toml Makefile tests/test_plugin.py docs/
PR 2  skills/writing-prompts/ + evals/writing-prompts/   migrated, run, recorded in docs/evals/
PR 3  skills/writing-agent-skills/ + evals/…             + references ported from evalspec to harnessbench
PR 4  skills/to-spec/ + evals/to-spec/                   + tests/skills/to-spec/
PR 5  skills/interview-me/ + evals/interview-me/
```

Each skill PR is based on the one before it, so the stack merges in order and every PR carries its own eval evidence.

## User Stories

1. As a Claude Code user, I want **`claude plugin install core@mechaswift`** to give me the skills in every session, so I stop copying `SKILL.md` files between projects.
2. As a Hermes user, I want **`hermes skills tap add theycallmeswift/mechaswift`** to expose the same skills, so both harnesses run the same procedures.
3. As the maintainer, I want **`make test` and `make lint` to pass on a fresh clone without access to the private eval runner**, so CI and contributors never block on harnessbench.
4. As the maintainer, I want **each skill PR to show its baseline-vs-trial delta and trigger routing results**, so a reviewer can see the skill earns its place before it merges.

## Implementation Decisions

```
knowledge-base/skills/<name>/ ──copy (minus evals/)──► skills/<name>/
knowledge-base/skills/<name>/evals/ ──migrate──► evals/<name>/<scenario>/eval.md + workspace/
                                                 evals/<name>/<query>.eval.md
.claude-plugin/plugin.json (core) + marketplace.json (mechaswift) ──► claude plugin validate --strict
hooks/session-start ──► hooks/hooks.json (SessionStart, ${CLAUDE_PLUGIN_ROOT})
pyproject.toml [tool.harnessbench] sets.default: baseline (bare) / trial (--plugin-dir /project), sonnet ──► make evals
tmp/evals/iteration_NN/benchmark.md ──copy──► docs/evals/<name>.md
```

- **Plugin is `core`, marketplace is `mechaswift`.** Matches the install line the README on `main` already advertised (`core@mechaswift`) and leaves room for sibling plugins later. Skills are invoked as `core:<name>`; `SKILL.md` frontmatter stays unprefixed. Marketplace `source` is `./`, so the repo root is both marketplace and plugin.
- **Hermes needs no extra manifest.** A tap is any repo with `skills/<name>/SKILL.md`; `name` and `description` are the only required frontmatter. `skills.sh.json` adds hub category labels without touching frontmatter; each skill PR adds its own entry.
- **`SessionStart` hook ships with the infrastructure.** One short directive to route through a matching skill. Claude-only by nature; it lives in `hooks/`, not in any `SKILL.md`.
- **harnessbench stays out of `pyproject.toml`.** It is private and unpublished, and uv resolves every dependency group on sync — so even an opt-in group with a git source breaks `make install` for anyone without repo access, CI included (observed on the first CI run). `make evals:install` puts it in the venv with `uv pip install` from git; the `make evals*` targets call that on demand and run with `uv run --no-sync` so a sync can't prune it mid-run. `make test` sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` because harnessbench's pytest plugin errors when loaded into a plain unit run.
- **One eval set, the plugin is the install.** `baseline` runs the agent bare; `trial` runs it with `harness_args = ["--plugin-dir", "/project"]`, the staged copy of this repo, so every eval measures the plugin as shipped — hook included — and no `setup.sh` exists anywhere. Routing evals are ordinary evals in the same set (harnessbench has no separate trigger format); their baseline column is uninformative and rides along. Both on `sonnet`; a routing miss that only opus resolves is recorded as a model-tier boundary, as the upstream suites did.
- **Evals live under a root `evals/` tree, skills ship clean.** `evals/<name>/<scenario>/eval.md` (+ `workspace/`) for output evals and `evals/<name>/<query>.eval.md` for routing queries. Sibling files make the group the skill name, so query slugs shared across skills (`tighten-prompt`, `fix-typeerror`) don't collide on harnessbench's `(group, eval_id)` key. `SKILL=<name>` sets `--eval-paths evals/<name>`.
- **Eval migration is mechanical and per skill.** `prompt.md` → `eval.md` with `seed:`/`text` renamed to `history:`/`content`; `fixtures/` → `workspace/`; `trigger-evals.md` → one `<query>.eval.md` per line carrying the verbatim query and a single `` Skill `<name>` invoked `` / `` not invoked `` assertion. Positives that presuppose a prior design discussion (to-spec's) get a short shared `history:` recap, because a bare session has nothing to write up and the agent correctly declines rather than routing.
- **Skill descriptions and bodies ship as eval-tuned upstream.** Only `writing-agent-skills` changes: its `SKILL.md` steps and its `running-evals.md` / `evaluating-skills.md` references describe the evalspec runner and are ported to harnessbench in its own PR, then re-run.
- **`tests/test_plugin.py` is the structural gate.** It checks the manifests agree, the hook script exists and is executable, `skills.sh.json` names real skills, and every `SKILL.md` has exactly `name` + `description` with `name` matching its directory. It is also why `make test` collects something before any skill lands.
- **`AGENTS.md` carries the no-attribution rule forward.** The rule existed on `dev`; it is restated with its why so it survives the branch reset. `CLAUDE.md` is a symlink.

## Testing Plan

### Logic
- **`validate_spec.py` keeps its contract** — every structural rule (required sections, TL;DR opener, empty section, leftover filler words, template comment, fenced content ignored) still flags exactly when the knowledge-base tests say it should.
- **Manifests agree** — the marketplace names exactly the plugin `plugin.json` declares, and every `SKILL.md` frontmatter is the portable `name` + `description` pair.

### Behavior
- **Every migrated output eval runs on both arms** and the trial arm's assertions pass, including activation.
- **Every migrated routing eval fires as expected on the trial arm** — positives invoke the skill, near-miss negatives do not — with any model-tier boundary recorded rather than hidden.
- **The plugin loads from disk** — a Claude Code session started with `--plugin-dir` at the repo root sees each landed skill under the `core:` namespace.
- **The session hook emits valid `SessionStart` JSON** with `hookSpecificOutput.additionalContext` when run with `CLAUDE_PLUGIN_ROOT` set.

### Interface
- **Manifests validate under strict mode** — `plugin.json`, `marketplace.json`, and every `SKILL.md` pass `claude plugin validate --strict`.
- **A fresh clone builds without the private runner** — the default `uv sync` resolves with public packages only, and `make test` / `make lint` are green.
- **The runner installs on demand** — `make evals:install` puts harnessbench in the venv for a maintainer with repo access, and `make evals:lint` runs clean on every suite.

## Documentation Plan

- **`README.md`**: install lines for both harnesses, dev commands, project tree; each skill PR appends its bullet under Skills.
- **`docs/development.md`**: prerequisites, `make` table, skill layout, Claude Code and Hermes local testing, the two eval sets and the authoring loop.
- **`docs/evals/<name>.md`**: the recorded benchmark each skill PR lands with.
- **`AGENTS.md`**: working rules, project structure, references; each skill PR appends its bullet under a Skills section.

## Out of Scope

- **Rewording skill descriptions or bodies** beyond porting `writing-agent-skills`' eval-runner text. Descriptions were trigger-eval-tuned upstream; changing them is a separate skill-authoring cycle.
- **The `ghostwrite`, `prompt-engineer`, `scope`, and `summarize` skills on `dev`**, and the DSPy optimizer under `lib/optimizer/`. `main` starts from the four requested skills only.
- **The brightdata MCP server and `WebFetch` deny rules** from `dev`. Not part of the skills' contract.
- **Publishing.** No marketplace registration and no Hermes tap verification against GitHub; the repo is private, so the Hermes install path additionally needs `GITHUB_TOKEN` in the user's Hermes env until it is public.

## References

- `~/dev/knowledge-base/skills/{interview-me,to-spec,writing-prompts,writing-agent-skills}` — the source of every skill file; `tests/skills/to-spec/` there is the source of the unit tests.
- `~/dev/knowledge-base/docs/style/writing-claude-plugins.md` — plugin layout, manifest, local-testing conventions followed here.
- Hermes docs, "Publishing a custom skill tap" (`~/.hermes/hermes-agent/website/docs/user-guide/features/skills.md`) — tap layout and frontmatter requirements.
- `~/dev/evalspec/docs/writing-evals.md`, `docs/configuration.md`, `docs/harnesses.md` — the harnessbench eval format, `[tool.harnessbench]` schema, and the `--plugin-dir /project` pattern for plugin-loaded arms.
- `git show dev:AGENTS.md` and `dev:docs/plugin-structure.md` — prior conventions carried forward (no attribution, `core@mechaswift`, nothing but manifests in `.claude-plugin/`).

## Verification

- `make install && make test && make lint` — fresh-clone build passes with public deps only.
- `claude plugin validate --strict . && claude plugin validate --strict .claude-plugin/plugin.json && claude plugin validate --strict skills` — manifests and skills are well-formed.
- `claude -p --plugin-dir . "List every skill whose name starts with core:"` — every landed skill loads under the `core:` namespace.
- `CLAUDE_PLUGIN_ROOT=. hooks/session-start | python3 -m json.tool` — the hook emits valid JSON.
- `make evals:lint` — the runner installs on demand and every suite lints clean.
- `make evals SKILL=<name> EVAL_ARGS="-n 4"` — per skill PR, both arms run over the skill's output and routing evals; the report is copied to `docs/evals/<name>.md`.
- `python3 skills/to-spec/scripts/validate_spec.py docs/specs/2026-09-04-skills-plugin-bootstrap.md` — this spec is structurally valid.
