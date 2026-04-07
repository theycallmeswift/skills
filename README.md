# MechaSwift

Personal agent framework for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Skills, configuration, and workflows that load automatically into every session.

## Skills

- **ghostwrite** -- Rewrites rough content in Swift's voice, formatted for a target platform (email, LinkedIn, Slack, DEV blog).
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
│   ├── ghostwrite/        # Content rewriter
│   │   ├── SKILL.md
│   │   └── references/      # Style samples
│   ├── scope/               # Design & ideation
│   │   ├── SKILL.md
│   │   └── evals/           # Eval definitions
│   └── summarize/           # Content summarization
│       ├── SKILL.md
│       └── evals/           # Eval definitions
├── references/              # Shared context (bio, voice profile)
├── docs/
│   ├── research/            # Best practices research
│   ├── plans/               # Project plans
│   └── specs/               # Detailed specifications
├── AGENTS.md                # Universal agent config (source of truth)
├── CLAUDE.md                # Symlink to AGENTS.md
└── tmp/                     # Scratch space (git-ignored)
```

## How Skills Work

Each skill lives in `skills/<name>/` with a `SKILL.md` that defines activation triggers, behavior rules, and output format. Skills are loaded on-demand to keep context lean.

Skills can reference shared context from `references/` (e.g. voice profile, bio) and write outputs to `docs/specs/` or `tmp/`.

## Testing

Each skill with evals has an `evals/evals.json` defining test prompts and structural assertions. The `/eval` slash command runs them in parallel: each prompt is executed with and without the skill loaded, graded by an LLM judge against the assertions, and printed as a pass/fail summary table.

```
/eval                        # All skills + project evals
/eval ghostwrite summarize   # Specific skills
/eval --no-baseline          # Skip the without-skill comparison
/eval --verbose              # Show full grading evidence
```

Results print inline. Full outputs land in `tmp/evals/<timestamp>/`.

For the full lifecycle (iteration, HTML viewer, trigger-eval description optimization), use Anthropic's **skill-creator** skill instead.

See [docs/evals.md](docs/evals.md) for the eval file format, current coverage, and best practices.
