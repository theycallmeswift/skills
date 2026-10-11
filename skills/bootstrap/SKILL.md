---
name: bootstrap
description: Use when the user wants a repository set up, bootstrapped, or brought up to their house or standard setup, new or existing — "bootstrap this repo", "set this repo up the way all my repos are", "add what's missing from our standard setup", "give this repo my usual AGENTS.md, style docs, gates, and PR template". Fires for a brand-new empty repo and for a partly set-up one. Don't use to scaffold an app or framework (Next.js, Vite, Django), to set up only a SessionStart hook or cloud-session environment, to write or edit AGENTS.md or CLAUDE.md prose alone (writing-prompts), or to author a skill (writing-agent-skills).
---

# bootstrap

Set a repo up to the house setup in `assets/`. The assets are the canonical copies: copy them, never paraphrase.

## Rules

- **Never edit a file that exists.** Two exceptions: append missing `.gitignore` lines, and add dev dependencies through the package manager. Whatever an existing file lacks is a gap to report, not a fix: its content is someone's decision.
- **Write only what the table lists.** No CI workflows, starter code, sample tests, or empty directories.
- **Fill every `<placeholder>`** from the repo, and wrap filled prose at 80 columns.

## 1. Detect the language

- **Python:** `pyproject.toml`, `requirements*.txt`, or `*.py`.
- **TypeScript:** `package.json`, `tsconfig.json`, or `*.ts`.
- **Neither:** the core only. In an empty repo, ask unless the user named the language.

| | `<install>` | `<test>` | `<lint>` | `<runtime>` |
| --- | --- | --- | --- | --- |
| Python | `make install` | `make test` | `make lint` | Python 3.13 and uv |
| TypeScript | `npm ci` | `npm test` | `npm run lint` | Node 26 |
| Core only | — | — | `npx --yes markdownlint-cli2` | Node |

Core only: drop the lines naming `<install>` or `<test>`, and report the missing test gate.

## 2. Write what's missing

If the repo has a remote and the remote has no `main`, first push an empty root commit to it as `main` by SHA (`git push origin <sha>:refs/heads/main`, which the settings' deny rules don't match), then work on a new branch from that commit carrying the current branch's commits.

| Asset | Destination | For |
| --- | --- | --- |
| `template-AGENTS.md` | `AGENTS.md`; intro from the README and code; add the repo's top-level folders to Project structure | all |
| — | `CLAUDE.md` as a symlink: `ln -s AGENTS.md CLAUDE.md` | all |
| `template-style-development.md`, `template-style-markdown.md`, `template-style-testing.md` | `docs/style/development.md`, `markdown.md`, `testing.md` | all |
| `template-style-python.md` or `template-style-typescript.md` | `docs/style/python.md` or `typescript.md` | language |
| `template-markdownlint-cli2.jsonc` | `.markdownlint-cli2.jsonc` | all |
| `template-claude-settings.json` | `.claude/settings.json` | all |
| `template-claude-cloud-node26-path.sh` | `.claude/hooks/claude-cloud-node26-path.sh`, executable | all |
| `template-cloud-agents.md` | `docs/cloud-agents.md`; drop the uv block outside Python | all |
| `template-pull_request_template.md` | `.github/pull_request_template.md`, byte for byte | all |
| `template-gitignore` | lines appended to `.gitignore`; TypeScript adds `node_modules/` | all |
| `template-Makefile`, `template-pyproject.toml` | `Makefile`, `pyproject.toml` | Python |
| `template-package.json`, `template-tsconfig.json`, `template-biome.jsonc`, `template-vitest.config.ts` | the name without `template-` | TypeScript |

If `CLAUDE.md` is a regular file and `AGENTS.md` is missing, write neither; report that `CLAUDE.md` should move to `AGENTS.md` with a symlink back.

Then add the dev tools:

- Python: `uv add --dev pytest ruff ty`
- TypeScript: `npm install -D @biomejs/biome typescript vitest markdownlint-cli2 @types/node`

## 3. Verify

Run `<test>` and `<lint>` and fix what you wrote until both pass. A failure in a file you didn't write is a gap. If a tool is missing, say so; never report a gate that didn't run as passing.

## 4. Report

If you pushed `main`, commit the setup, push the branch, and open a draft PR into `main` with the PR template as its body and the Ready gate filled in from Verify; with no PR tool, give the branch and the filled-in body above the report instead. Say `main` should become the default branch, a repo setting you can't change, and list `main` and the PR under Added.

Check every existing file that has an asset against it:

- `AGENTS.md`: each template section it lacks, by heading.
- `CLAUDE.md`: not a symlink to `AGENTS.md`.
- `.claude/settings.json`: missing attribution, deny rules, or the SessionStart hook.
- Gate file: each missing `install`, `test`, `lint`, or `format` target or script.
- Style docs: each asset rule they lack or contradict.

End with:

```text
Added
- <path>
Gaps
- <path>: <what it lacks, one line>
Gates
- <command>: passed | failed: <why> | not run: <why>
```
