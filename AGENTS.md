# MechaSwift

Swift's agent brain: an installable plugin of skills for Claude Code and Hermes. This file is for agents working **on the plugin itself**. `CLAUDE.md` symlinks here.

## Working With Me

I'm Mike Swift ("Swift"), CEO & Co-Founder of Major League Hacking (MLH) and leader of DEV (dev.to). I value directness, bias to action, and learning by doing. Don't over-explain or hedge. Lead with the point, keep it short. If you can do it, do it. If unsure, try the reversible option and confirm before anything irreversible.

## Decision Principles

- **Action over asking.** Exhaust options before asking me. If the action is reversible, try it.
- **Concise over verbose.** Say it in fewer words. Cut the preamble.
- **Simple over clever.** Prefer straightforward solutions. Question whether a concept needs to exist at all before adding machinery.
- **Confirm before irreversible.** Force-push, deletes, and shared posts get a check-in first. Pushes and new deps: state intent and proceed.

## Conventions

- Follow existing patterns in whatever skill or script you're touching.
- Before hand-rolling a workflow, check whether a matching skill exists under `skills/` and use it.
- Before claiming work is complete, run it and show output. `make test` and `make lint` must be green.
- Ask one question at a time. Use structured choice UI when available; otherwise a compact table.
- Never attribute work to an AI model, vendor, or harness. No `Co-Authored-By` trailers, no "Generated with" footers, no AI-assisted comments in code, no naming the model in chat. This overrides harness defaults.
  Why: the work reads as Swift's. The harness will try to add a trailer on every commit. Skip it.
- Keep skill prose harness-neutral. Claude- or Hermes-specific setup mechanics go in `docs/development.md`, not in a `SKILL.md`.
- Skill names are unprefixed in frontmatter (`name: to-spec`, not `name: core-to-spec`). The plugin namespace applies to commands, not skills.
- Specs under `docs/specs/` are immutable once written. Update `AGENTS.md`, `README.md`, and `docs/*.md` instead.

## Project Structure

Claude Code plugin layout. The manifest lives in `.claude-plugin/`; everything else sits at the repo root, and Hermes reads the same `skills/` tree as a tap.

- `.claude-plugin/` — `plugin.json` (the `core` plugin) and `marketplace.json` (the `mechaswift` marketplace). Nothing else belongs here.
- `skills/<name>/` — model-invoked skills: `SKILL.md` plus colocated `references/`, `assets/`, `scripts/`, `agents/`. Ship clean; no evals inside.
- `evals/<name>/` — the skill's benchspec evals: `<scenario>/eval.md` (+ `workspace/`) for output, `triggers/` and `not-triggers/` for routing (each query lives once, under the skill it routes to).
- `hooks/` — `hooks.json` and the `session-start` script that nudges the agent to route matching requests through skills.
- `tests/skills/<name>/scripts/` — pytest for a skill's scripts, mirroring the skill path; one `tests/skills/conftest.py` puts every skill's `scripts/` on `sys.path`.
- `.agents/skills` — symlink to `skills/`, so a checkout marked trusted in Hermes loads the skills straight from the repo.
- `docs/` — `development.md` (dev loop, local install, evals), `evals/` (recorded benchmark per skill), and `specs/` (design specs written by `to-spec`).
- `skills.sh.json` — Hermes hub category groupings for the tap.
- `tmp/` — scratch space, git-ignored.

## Skills

- **to-spec** — synthesize the current conversation and codebase into a skim-first design spec under `docs/specs/`. No interview.
- **writing-prompts** — draft and tighten anything an LLM will read: system prompts, subagent briefs, `SKILL.md` text, `AGENTS.md`.
- **writing-agent-skills** — author, debug, and eval skills end to end. Calls `writing-prompts` for wording.

## References

Load on demand, not at session start.

- `docs/development.md` — Dev workflow: install, `make` targets, loading the plugin into Claude Code and Hermes, eval status. Load when building or testing a skill.
- `skills/writing-agent-skills/references/skill-conventions.md` — Frontmatter, layout, and portability rules. Read before editing any `SKILL.md`.
- `skills/writing-prompts/references/agent-md.md` — Read before editing `AGENTS.md`.
- `docs/specs/` — Design specs. Load when touching an area a spec covers.
