# MechaSwift

Swift's Agent Brain. An opinionated set of skills, tools, and prompts for use inside harnesses like Claude Code and Hermes.

## Skills

 - **example** -- This is an example included skill

## MCPs

 - **example-mcp** -- This is an example included MCP server


## Install

```sh
claude plugins marketplace add theycallmeswift/mechaswift
claude plugins install core@mechaswift
```

Skills are available in every Claude Code session after install. Invoke them by name (e.g. `/skill-name`).

### Development

Clone the repo for local development and eval authoring:

```sh
git clone git@github.com:theycallmeswift/mechaswift.git
cd mechaswift
cp .env.example .env   # then fill in API keys
make install           # installs Python deps for the eval harness via uv
```

## Project Structure

```
mechaswift/
├── skills/                  # On-demand capability modules
├── docs/                    # Hand-authored docs and prompt context
├── tests/                   # Evals + harness
│   ├── fixtures/            # Synthetic test data
│   ├── skills/              # Per-skill eval suites
│   └── support/             # Shared resources for test files
├── references/              # Agent-generated context
│   ├── plans/               # Implementation plans
│   ├── research/            # Best-practices research
│   └── specs/               # Detailed specifications
├── AGENTS.md                # Universal agent config (source of truth)
├── CLAUDE.md                # Symlink to AGENTS.md
└── tmp/                     # Scratch space (git-ignored)
```

## Development

Makefile targets:

```
make install    # uv sync (install Python deps)
make lint       # uv run ruff check --fix .
make format     # uv run ruff format .
```
