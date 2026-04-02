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

Each skill with evals has an `evals/evals.json` file defining test cases with:
- `prompt` -- The input to the skill
- `expected_output` -- Human-readable description of what should happen
- `expectations` -- Structural assertions graded against the output

Evals run each prompt twice (`with_skill` via `--plugin-dir` and `without_skill` baseline) using `claude -p`, then grade the output against expectations:

```sh
# With skill loaded
claude -p --plugin-dir /path/to/mechaswift "<prompt>"

# Baseline (no skill)
claude -p "<prompt>"
```

Results land in `tmp/<skill>-evals/` with transcripts, grading, and metadata. Not tracked in git.
