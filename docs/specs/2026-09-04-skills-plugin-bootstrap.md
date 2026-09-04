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
PR 2  skills/writing-prompts/        evals migrated, run, recorded in docs/evals/
PR 3  skills/writing-agent-skills/   + references ported from evalspec to harnessbench
PR 4  skills/to-spec/                + tests/skills/to-spec/
PR 5  skills/interview-me/
```

Each skill PR is based on the one before it, so the stack merges in order and every PR carries its own eval evidence.

## User Stories

1. As a Claude Code user, I want **`claude plugin install core@mechaswift`** to give me the skills in every session, so I stop copying `SKILL.md` files between projects.
2. As a Hermes user, I want **`hermes skills tap add theycallmeswift/mechaswift`** to expose the same skills, so both harnesses run the same procedures.
3. As the maintainer, I want **`make test` and `make lint` to pass on a fresh clone without access to the private eval runner**, so CI and contributors never block on harnessbench.
4. As the maintainer, I want **each skill PR to show its baseline-vs-trial delta and trigger routing results**, so a reviewer can see the skill earns its place before it merges.

## Implementation Decisions

```
knowledge-base/skills/<name>/ ──copy──► skills/<name>/ ──migrate_evals──► evals/<slug>/eval.md + workspace/ + setup.sh
                                                                          evals/<name>-triggers/<query>.eval.md
.claude-plugin/plugin.json (core) + marketplace.json (mechaswift) ──► claude plugin validate --strict
hooks/session-start ──► hooks/hooks.json (SessionStart, ${CLAUDE_PLUGIN_ROOT})
pyproject.toml [tool.harnessbench] sets.default (baseline/trial, sonnet) ──► make evals
                                   sets.triggers (trial, opus, --plugin-dir /project) ──► make evals:triggers
tmp/evals/iteration_NN/benchmark.md ──copy──► docs/evals/<name>.md
```

- **Plugin is `core`, marketplace is `mechaswift`.** Matches the install line the README on `main` already advertised (`core@mechaswift`) and leaves room for sibling plugins later. Skills are invoked as `core:<name>`; `SKILL.md` frontmatter stays unprefixed. Marketplace `source` is `./`, so the repo root is both marketplace and plugin.
- **Hermes needs no extra manifest.** A tap is any repo with `skills/<name>/SKILL.md`; `name` and `description` are the only required frontmatter. `skills.sh.json` adds hub category labels without touching frontmatter; each skill PR adds its own entry.
- **`SessionStart` hook ships with the infrastructure.** One short directive to route through a matching skill. Claude-only by nature; it lives in `hooks/`, not in any `SKILL.md`.
- **harnessbench is an opt-in dependency group.** It is private and unpublished, so it cannot be a default dev dependency without breaking `make install` for anyone without repo access (CI included). `[dependency-groups] evals` plus a `[tool.uv.sources]` git pin; the `make evals*` targets use `uv run --group evals`. `make test` sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` because harnessbench's pytest plugin errors when loaded into a plain unit run.
- **Two eval sets.** `default` is the capability-lift pair (`baseline` installs nothing, `trial`'s per-eval `setup.sh` installs the skill plus declared sibling deps, both `claude-code` / `sonnet`). `triggers` is one `trial` arm on `opus` with `harness_args = ["--plugin-dir", "/project"]`, so routing is measured against the real plugin and its hook; a baseline arm is meaningless there because an uninstalled skill cannot fire. `make evals` filters `-k 'not triggers'` and `make evals:triggers` filters `-k triggers`; `SKILL=<name>` sets `--eval-paths skills/<name>`.
- **Eval migration is mechanical and per skill.** `evals/<slug>/prompt.md` → `evals/<slug>/eval.md` with `seed:`/`text` renamed to `history:`/`content`; `fixtures/` → `workspace/`; the per-suite `setup.sh` keyed on `$EVALSPEC_ARM` becomes a per-eval `setup.sh` keyed on `$HARNESSBENCH_ARM` that tars the skill (minus `evals/`) into `/home/harnessbench/skills/`; `trigger-evals.md` becomes `evals/<name>-triggers/<query>.eval.md`, each carrying the query as its prompt and one `` Skill `<name>` invoked `` / `` not invoked `` assertion. Trigger group folders are prefixed with the skill name because harnessbench keys evals on `(group, eval_id)` and several skills share query slugs.
- **Skill descriptions and bodies ship as eval-tuned upstream.** Only `writing-agent-skills` changes: its `SKILL.md` steps and its `running-evals.md` / `evaluating-skills.md` references describe the evalspec runner and are ported to harnessbench in its own PR, then re-run.
- **`tests/test_plugin.py` is the structural gate.** It checks the manifests agree, the hook script exists and is executable, `skills.sh.json` names real skills, and every `SKILL.md` has exactly `name` + `description` with `name` matching its directory. It is also why `make test` collects something before any skill lands.
- **`AGENTS.md` carries the no-attribution rule forward.** The rule existed on `dev`; it is restated with its why so it survives the branch reset. `CLAUDE.md` is a symlink.

## Testing Plan

### Logic
- **`validate_spec.py` keeps its contract** — every structural rule (required sections, TL;DR opener, empty section, leftover filler words, template comment, fenced content ignored) still flags exactly when the knowledge-base tests say it should.
- **Manifests agree** — the marketplace names exactly the plugin `plugin.json` declares, and every `SKILL.md` frontmatter is the portable `name` + `description` pair.

### Behavior
- **Every migrated output eval runs on both arms** and the trial arm's assertions pass, including activation.
- **Every migrated trigger eval passes on the plugin-loaded arm** — positives fire the skill, near-miss negatives do not.
- **The plugin loads from disk** — a Claude Code session started with `--plugin-dir` at the repo root sees each landed skill under the `core:` namespace.
- **The session hook emits valid `SessionStart` JSON** with `hookSpecificOutput.additionalContext` when run with `CLAUDE_PLUGIN_ROOT` set.

### Interface
- **Manifests validate under strict mode** — `plugin.json`, `marketplace.json`, and every `SKILL.md` pass `claude plugin validate --strict`.
- **A fresh clone builds without the private runner** — the default `uv sync` resolves with public packages only, and `make test` / `make lint` are green.
- **The opt-in group resolves** — `uv sync --group evals` installs harnessbench from git for a maintainer with repo access, and `harnessbench lint` runs clean on every suite.

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
- `make evals:lint` — the opt-in runner resolves and every suite lints clean.
- `make evals SKILL=<name> EVAL_ARGS="-n 6"` and `make evals:triggers SKILL=<name> EVAL_ARGS="-n 6"` — per skill PR, both arms run and the trial arm passes; the report is copied to `docs/evals/<name>.md`.
- `python3 skills/to-spec/scripts/validate_spec.py docs/specs/2026-09-04-skills-plugin-bootstrap.md` — this spec is structurally valid.
