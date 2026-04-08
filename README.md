# MechaSwift

Personal agent framework for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Skills, configuration, and workflows that load automatically into every session.

## Skills

- **ghostwrite** -- Rewrites rough content in Swift's voice, formatted for a target platform (email, LinkedIn, Slack, DEV blog).
- **prompt-engineer** -- Writes, improves, and debugs prompts for LLMs. System prompts, tool use, evals.
- **scope** -- Turns a vague idea into a structured spec through collaborative design. Enforces design-before-code.
- **summarize** -- Produces skimmable summaries of web pages, PDFs, and articles with TL;DR, cliff notes, and ready-to-share messages.

## MCP

- **brightdata** -- Hosted MCP server for web access. Provides `scrape_as_markdown`, `scrape_batch`, `search_engine`, `search_engine_batch`, and `discover`. Requires `BRIGHTDATA_API_TOKEN` in `.env`.

## Install

Clone the repo anywhere, then register it as a Claude Code plugin:

```sh
git clone git@github.com:theycallmeswift/mechaswift.git
cd mechaswift
cp .env.example .env   # then fill in API keys
claude plugins add /path/to/mechaswift
```

Skills are available in every Claude Code session after install. Invoke them by name (e.g. `/ghostwrite`, `/scope`, `/summarize`).

## Project Structure

```
mechaswift/
├── skills/                  # On-demand capability modules
│   ├── ghostwrite/          # Content rewriter
│   ├── prompt-engineer/     # Prompt authoring/debugging
│   ├── scope/               # Design & ideation
│   └── summarize/           # Content summarization
├── docs/                    # Hand-authored docs and prompt context
│   ├── about-swift.md       # Bio, tone, voice
│   ├── evals.md             # How to run and write skill evals
│   └── plugin-structure.md  # Plugin layout reference
├── tests/                   # Evals + harness
│   ├── core/                # Cross-cutting rules (no-ai-attribution, skill-triggers)
│   ├── skills/              # Per-skill eval suites
│   └── support/harness/     # Python eval runner
├── references/              # Agent-generated context
│   ├── plans/               # Implementation plans
│   ├── research/            # Best-practices research
│   └── specs/               # Detailed specifications
├── AGENTS.md                # Universal agent config (source of truth)
├── CLAUDE.md                # Symlink to AGENTS.md
└── tmp/                     # Scratch space (git-ignored)
```

## How Skills Work

Each skill lives in `skills/<name>/` with a `SKILL.md` that defines activation triggers, behavior rules, and output format. Skills are loaded on-demand to keep context lean.

Skills can reference hand-authored prompt context from `docs/` (e.g. `about-swift.md`) and skill-local `references/`, and write outputs to `references/specs/`, `references/plans/`, or `tmp/`.

## Testing

Eval suites live under `tests/skills/<name>/evals.json` (per-skill) and `tests/core/*.json` (cross-cutting rules). A Python harness runs them in parallel through the Claude Agent SDK, grades with an LLM judge (plus deterministic tool-trace and lint assertions), and prints a live table.

```
make test                                       # All suites
make test ARGS="ghostwrite summarize"           # Specific suites
make test ARGS="--no-baseline"                  # Skip baseline (with-skill only)
make test ARGS="--verbose"                      # Show passing assertion evidence
make test ARGS="--model claude-haiku-4-5-20251001"  # Override agent model
make test-unit                                  # Harness unit tests
```

Results print inline. Full outputs land in `tmp/evals/<timestamp>/`.

See [docs/evals.md](docs/evals.md) for the eval file format, tiers (lift vs regression), assertion types, and best practices.
