# MechaSwift

Swift's Agent Brain. An opinionated set of skills, tools, and prompts for use inside harnesses like Claude Code and Hermes.

## Skills

Model-invoked. The agent picks them up when the request matches; you can also call them by name.

- **interview-me** — A relentless, one-question-at-a-time interviewer that pairs every decision with a visual and runs until a stop condition you set: until you say stop, until a named skill (default `to-spec`) has enough, or until a stated goal is resolved. Say "interview me", "grill me", or "scope this out before we spec it".
- **to-spec** — Synthesize the design just reached in the session into a skim-first spec at `docs/specs/YYYY-MM-DD-<slug>.md`. No interview; it works from what's already in context and refuses politely when that's too thin. Say "spec this out", "write this up as a design spec", or "turn this into a PRD".
- **writing-prompts** — Draft or tighten anything an LLM will read: system prompts, subagent briefs, slash-command bodies, `SKILL.md` text, `AGENTS.md` / `CLAUDE.md`. Ends with an editorial pass that cuts filler without changing meaning.
- **writing-agent-skills** — Build, debug, and evaluate skills end to end: eval-first (RED → GREEN → REFACTOR), trigger-description tuning, and the conventions that keep a skill portable across harnesses. Calls `writing-prompts` for the wording.
- **delegating-to-codex** — Hand implementation or review work to the Codex CLI as background jobs: explicit effort per task, Codex edits but never commits, reviews come back as schema JSON, and fix rounds resume the same Codex thread. Say "have codex review my branch" or "let codex implement task 3", or assign a plan step to Codex. Needs the Codex CLI, signed in.

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
├── evals/                   # benchspec evals per skill: <skill>/<scenario>/eval.md + <skill>/{triggers,not-triggers}/<query>.eval.md
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
