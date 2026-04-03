# MechaSwift

Personal agent framework for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Skills, configuration, and workflows that load automatically into every session.

## Skills

- **ghostwrite** -- Rewrites rough content in Swift's voice, formatted for a target platform (email, LinkedIn, Slack, DEV blog).
- **scope** -- Turns a vague idea into a structured spec through collaborative design. Enforces design-before-code.
- **summarize** -- Produces skimmable summaries of web pages, PDFs, and articles with TL;DR, cliff notes, and ready-to-share messages.

## Install

Clone the repo anywhere, then register it as a Claude Code plugin:

```sh
git clone git@github.com:theycallmeswift/mechaswift.git
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

We use Anthropic's **skill-creator** skill to run evals. It handles parallel test execution, LLM-graded assertions, benchmark aggregation, and an HTML viewer for qualitative review.

Each skill with evals has an `evals/evals.json` defining test prompts and structural assertions. To run evals, invoke the skill-creator and point it at the skill you want to test. It runs each prompt with and without the skill loaded, grades against assertions, and produces a benchmark comparison.

Run all evals:

> Run the quality evals for all skills in this project using the skill-creator. Results should go in tmp/.

Run evals for a single skill:

> Run quality evals for the ghostwrite skill using the skill-creator.

See [docs/evals.md](docs/evals.md) for the full eval workflow, file format, and best practices.
