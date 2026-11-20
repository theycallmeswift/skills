---
name: bootstrap
description: Use when the user wants a repository set up, bootstrapped, or brought up to their house or standard setup, new or existing — "bootstrap this repo", "set this repo up the way all my repos are", "add what's missing from our standard setup", "give this repo my usual AGENTS.md, style docs, gates, and PR template". Fires for a brand-new empty repo and for a partly set-up one. Don't use to scaffold an app or framework (Next.js, Vite, Django), to set up only a SessionStart hook or cloud-session environment, to write or edit AGENTS.md or CLAUDE.md prose alone (writing-prompts), or to author a skill (writing-agent-skills).
---

# bootstrap

Set a repo up to the house setup in `assets/`. The assets are the canonical copies: copy them, never paraphrase.

## Rules

- **Never edit a file that exists.** Two exceptions: append missing `.gitignore` lines, and add dev dependencies through the package manager. Whatever an existing file lacks is a gap to report, not a fix: its content is someone's decision.
- **Never move a file or directory.** Schedulers and deploy hosts reach code by its path. Write around the layout you find.
- **Write only what the table lists.** No starter code, sample tests, or empty directories.
- **Never suppress a finding** with a `noqa`, `biome-ignore`, or per-file ignore. Stage the rules instead (Verify).
- **Fill every `<placeholder>`** from the repo, and wrap filled prose at 80 columns.

## 1. Detect packages

A package is a directory holding a `pyproject.toml`, `package.json`, or `tsconfig.json`, at any depth. List them with `git ls-files --cached --others --exclude-standard`, or `find` outside `node_modules/` and `.venv/` without git.

- **Python:** a `pyproject.toml`, or loose `requirements*.txt` or `*.py` with no package.
- **TypeScript:** a `tsconfig.json` or `*.ts` files.
- **JavaScript:** a `package.json` with neither. Never give it TypeScript config.
- **Neither:** the core only. In an empty repo, ask unless the user named the language.

Code no package covers, such as loose scripts with tests, is a gap.

| | `<install>` | `<test>` | `<lint>` | `<runtime>` |
| --- | --- | --- | --- | --- |
| Python | `make install` | `make test` | `make lint` | Python 3.13 and uv |
| TypeScript | `npm ci` | `npm test` | `npm run lint` | Node 26 |
| JavaScript | `npm ci`, or `npm install` with no lockfile | `npm test` | `npx --yes @biomejs/biome check <paths> && npx --yes markdownlint-cli2` | Node 26 |
| Several packages | `make install` | `make test` | `make lint` | each language's |
| Core only | — | — | `npx --yes markdownlint-cli2` | Node |

Core only: drop the lines naming `<install>` or `<test>`, and report the missing test gate.

More than one package, or one outside the root: read [references/monorepos.md](references/monorepos.md) before writing, and use its rows in place of the language rows below.

## 2. Write what's missing

If the repo has a remote and the remote has no `main`, first push an empty root commit to it as `main` by SHA (`git push origin <sha>:refs/heads/main`, which the settings' deny rules don't match), then work on a new branch from that commit carrying the current branch's commits.

| Asset | Destination | For |
| --- | --- | --- |
| `template-AGENTS.md` | `AGENTS.md`; intro from the README and code; add the repo's top-level folders to Project structure | all |
| — | `CLAUDE.md` as a symlink: `ln -s AGENTS.md CLAUDE.md` | all |
| `template-style-development.md`, `template-style-markdown.md`, `template-style-testing.md` | `docs/style/development.md`, `markdown.md`, `testing.md` | all |
| `template-style-python.md` or `template-style-typescript.md` | `docs/style/python.md` or `typescript.md` | Python, TypeScript; JavaScript has no style doc, so report it as a gap |
| `template-markdownlint-cli2.jsonc` | `.markdownlint-cli2.jsonc`; add `ignores` for Markdown that isn't documentation | all |
| `template-claude-settings.json` | `.claude/settings.json` | all |
| `template-claude-cloud-node26-path.sh` | `.claude/hooks/claude-cloud-node26-path.sh`, executable | all |
| `template-cloud-agents.md` | `docs/cloud-agents.md`; drop the uv block outside Python | all |
| `template-pull_request_template.md` | `.github/pull_request_template.md`, byte for byte | all |
| `template-dependabot.yml` | `.github/dependabot.yml`, byte for byte | with a CI workflow |
| `template-ci-python.yml` or `template-ci-typescript.yml` | `.github/workflows/ci.yml`, byte for byte | Python, TypeScript |
| `template-ci-javascript.yml` | `.github/workflows/ci.yml`; fill `<paths>` with the package's source folders | JavaScript |
| `template-gitignore` | lines appended to `.gitignore`; Node adds `node_modules/` | all |
| `template-Makefile`, `template-pyproject.toml` | `Makefile`, `pyproject.toml` | Python |
| `template-package.json`, `template-tsconfig.json`, `template-biome.jsonc`, `template-vitest.config.ts` | the name without `template-` | TypeScript |
| `template-biome.jsonc` | `biome.jsonc` | JavaScript |

Markdown that isn't documentation (LLM prompts and their variants, raw notes, generated output) changes meaning when rewrapped. Find it by path and contents; ask when a folder is unclear and someone can answer.

If `CLAUDE.md` is a regular file and `AGENTS.md` is missing, write neither; report that `CLAUDE.md` should move to `AGENTS.md` with a symlink back.

Then add the dev tools:

- Python: `uv add --dev pytest ruff ty`
- TypeScript: `npm install -D @biomejs/biome typescript vitest markdownlint-cli2 @types/node`
- JavaScript: `npm install -D @biomejs/biome markdownlint-cli2`; its tests keep their runner. A missing `lint` or `format` script is a gap: report the script to add.

## 3. Verify

Run `<test>` and `<lint>` and fix what you wrote until both pass. If a tool is missing, say so; never report a gate that didn't run as passing.

**Tests run anywhere.** With git and at least one commit, also run `<test>` in a clean checkout (`git worktree add` to a temp dir outside the repo, then `<install>`). A test that fails only there reads git-ignored files or local secrets, though the docs you wrote say the gate needs none. Report each as a gap naming the file it needs, and write that need where the docs claim none. With several packages, keep that package in `<test>` but drop its Test step from CI until its tests pass clean; with one, say CI's tests will fail until then.

**Existing code that fails a gate** gets a baseline and a ramp, never a red first CI run:

1. Count the findings per tool and per rule family (`ruff check --statistics`, `ty check`, `biome check`, markdownlint).
2. Stage the config you wrote to what passes now: Ruff `select` keeps only families with no findings, markdownlint `globs` cover only files that pass, and `ruff format --check`, `ty`, or Biome stay out of `<lint>` while they fail.
3. Plan the later stages: a formatter-only PR, then Ruff `F`, `E`, `W`, `I`, `B`, `UP`, then `ANN`, `D`, and `ty` per package.

A config file that already existed can't be staged; report its findings as a gap instead.

## 4. Report

If you pushed `main`, commit the setup, push the branch, and open a draft PR into `main` with the PR template as its body and the Ready gate filled in from Verify; with no PR tool, give the branch and the filled-in body above the report instead. Say `main` should become the default branch, a repo setting you can't change, and list `main` and the PR under Added.

If you wrote `.github/workflows/ci.yml`, say branch protection on `main` should require only its `CI passed` check, a repo setting you can't change.

Check every existing file that has an asset against it:

- `AGENTS.md`: each template section it lacks, with the text you'd add, and each repo path it names that doesn't exist.
- `CLAUDE.md`: not a symlink to `AGENTS.md`.
- `README.md`: missing at the root; `AGENTS.md` names it as the docs index.
- `.claude/settings.json`: missing attribution, deny rules, or the SessionStart hook.
- Gate file: each missing `install`, `test`, `lint`, or `format` target or script.
- `.github/workflows/ci.yml`: no docs-only skip for the tests, or no `CI passed` job for branch protection to require.
- Style docs: each asset rule they lack or contradict.

Then check existing practice against the house rules, and list each clash with its options:

- Scripts, docs, and automation that push to `main` (`git push origin main` and the like): the landing rules and the deny rules break them.
- Recent `git log` subjects that don't follow conventional commits.

End with:

```text
Added
- <path>
Gaps
- <path>: <what it lacks, one line>
Clashes
- <existing practice> vs <house rule>: <options>
Gates
- <command>: passed | failed: <why> | not run: <why>
- Baseline: <tool> <rule family>: <findings>
- Ramp: <stage>: <what it turns on>
```

Drop `Clashes`, `Baseline`, and `Ramp` lines when there are none.
