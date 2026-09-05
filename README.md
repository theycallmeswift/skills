# MechaSwift

Swift's Agent Brain. An opinionated set of skills, tools, and prompts for use inside harnesses like Claude Code and Hermes.

## Skills

Model-invoked. The agent picks them up when the request matches; you can also call them by name.

## Install

### Claude Code

```sh
claude plugin marketplace add theycallmeswift/mechaswift
claude plugin install core@mechaswift
```

Skills are then available in every session as `core:<skill>` (e.g. `/core:to-spec`), and the agent triggers them on matching requests. A `SessionStart` hook nudges the agent to route through a matching skill instead of hand-rolling the task.

### Hermes

The repo is a skills tap: each directory under `skills/` is one installable skill.

```sh
hermes skills tap add theycallmeswift/mechaswift
hermes skills install theycallmeswift/mechaswift/<skill>
```

Without adding the tap, a single skill installs directly with `hermes skills install theycallmeswift/mechaswift/skills/<skill>`. While the repo is private, Hermes needs a `GITHUB_TOKEN` in its `.env` to read it. `skills.sh.json` at the repo root supplies the category groupings the Hermes hub shows.

## Development

```sh
git clone git@github.com:theycallmeswift/mechaswift.git
cd mechaswift
make install           # uv sync — pytest + ruff
make test              # unit tests for skill scripts
make lint              # ruff
```

Load the plugin from disk to try changes: `claude --plugin-dir /path/to/mechaswift`, then `/reload-plugins` after edits. For Hermes, `hermes skills trust` in the checkout loads `skills/` directly (via the `.agents/skills` symlink). The full loop — evals, credentials — is in [`docs/development.md`](docs/development.md).

## Project Structure

```
mechaswift/
├── .claude-plugin/          # plugin.json (core) + marketplace.json (mechaswift)
├── skills/                  # One directory per skill: SKILL.md + references/, assets/, scripts/
├── evals/                   # benchspec evals per skill: <skill>/<scenario>/eval.md + <skill>/<query>.eval.md
├── hooks/                   # SessionStart hook (Claude Code)
├── tests/skills/            # pytest for skill scripts, mirroring skills/
├── docs/
│   ├── development.md       # Dev loop, local install, evals
│   ├── evals/               # Recorded benchmark results per skill
│   └── specs/               # Design specs (written by to-spec)
├── skills.sh.json           # Hermes hub category groupings
├── AGENTS.md                # Working rules for agents editing this repo (CLAUDE.md symlinks to it)
└── tmp/                     # Scratch space (git-ignored)
```
