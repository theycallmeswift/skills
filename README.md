# MechaSwift

Swift's Agent Brain. An opinionated set of skills, tools, and prompts for use inside harnesses like Claude Code and Hermes.

## Skills

Model-invoked. The agent picks them up when the request matches; you can also call them by name.

- **interview-me** — A relentless, one-question-at-a-time interviewer that pairs every decision with a visual and runs until a stop condition you set: until you say stop, until a named skill (default `to-spec`) has enough, or until a stated goal is resolved. Say "interview me", "grill me", or "scope this out before we spec it".
- **to-spec** — Synthesize the design just reached in the session into a skim-first spec at `docs/specs/YYYY-MM-DD-<slug>.md`. No interview; it works from what's already in context and refuses politely when that's too thin. Say "spec this out", "write this up as a design spec", or "turn this into a PRD".
- **writing-prompts** — Draft or tighten anything an LLM will read: system prompts, subagent briefs, slash-command bodies, `SKILL.md` text, `AGENTS.md` / `CLAUDE.md`. Ends with an editorial pass that cuts filler without changing meaning.
- **writing-agent-skills** — Build, debug, and evaluate skills end to end: eval-first (RED → GREEN → REFACTOR), trigger-description tuning, and the conventions that keep a skill portable across harnesses. Calls `writing-prompts` for the wording.
- **catch-me-up** — Re-orient you on the current session after a break. Narration comes from context, but branch, PR, CI, and claimed files are checked before they're stated, and a compacted context is disclosed rather than filled in. Ends with what needs your call and what the agent can clear on its own. Say "catch me up", "where were we", or "what's on me".
- **delegating-to-codex** — Hand implementation or review work to the Codex CLI as background jobs: explicit effort per task, Codex edits but never commits, reviews come back as schema JSON, and fix rounds resume the same Codex thread. Say "have codex review my branch" or "let codex implement task 3", or assign a plan step to Codex. Needs the Codex CLI, signed in.
- **claude-cloud-orchestrator** — In a Claude Code cloud session, hand PR-sized tasks to worker cloud sessions and supervise them: dispatch, review each PR with a fresh subagent, request changes until clean, then hand the PR to you. Say "hand this to a cloud agent", "spin up a worker for this", or "check on the workers".
- **claude-cloud-worker** — The worker side of that protocol: open a draft PR, address review rounds, and report back to the orchestrator session. Loads when a worker's prompt names it.
- **bootstrap** — Set up a repo, new or existing, to the house setup: `AGENTS.md` with a `CLAUDE.md` symlink, `docs/style/` guides (Python or TypeScript detected), test and lint gates, Claude settings, cloud-agent docs, a CI workflow that skips tests on docs-only PRs, and a PR template with a Ready gate. On an existing repo it never rewrites a file; it adds what's missing and lists the gaps. Say "bootstrap this repo" or "set this repo up the way my repos are".
- **pull-request** — Open and update PRs in one format: what changed and why, a `Decide` section, and a Ready gate table. Each row is filled only from what the agent actually ran or changed this session; an empty row keeps the PR a draft, and it goes ready only once every row has evidence and CI is green. Say "open the PR", "mark it ready", or "update the PR body".
- **google-slides** — Build a new Google Slides deck from your template and content, or add and redesign slides in an existing deck so they look like the rest of it. Copies the template rather than starting blank, keeps your wording and every sourced name and number exact, and sweeps an existing deck for other slides, trackers and speaker notes the change makes wrong. Ends with what changed, what the render review caught, and what needs your call. Say "make a deck from our brand template", "make these slides look like the others" or "the numbers changed, update the deck".

## Install

### Claude Code

```sh
claude plugin marketplace add theycallmeswift/skills
claude plugin install core@mechaswift
```

Skills are then available in every session as `core:<skill>` (e.g. `/core:to-spec`), and the agent triggers them on matching requests. A `SessionStart` hook nudges the agent to route through a matching skill instead of hand-rolling the task.

### Hermes

The repo is a skills tap: each directory under `skills/` is one installable skill.

```sh
hermes skills tap add theycallmeswift/skills
hermes skills install theycallmeswift/skills/<skill>
```

Without adding the tap, a single skill installs directly with `hermes skills install theycallmeswift/skills/skills/<skill>`. `skills.sh.json` at the repo root supplies the category groupings the Hermes hub shows.

## Development

```sh
git clone git@github.com:theycallmeswift/skills.git
cd skills
make install           # uv sync — pytest + ruff
make test              # unit tests for skill scripts
make lint              # ruff
```

Load the plugin from disk to try changes: `claude --plugin-dir /path/to/skills`, then `/reload-plugins` after edits. For Hermes, `hermes skills trust` in the checkout loads `skills/` directly (via the `.agents/skills` symlink). The full loop — evals, credentials — is in [`docs/development.md`](docs/development.md).

## Project Structure

```
skills/
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
