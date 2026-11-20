---
---

## Prompt

Bring this repo up to my house setup: AGENTS.md with CLAUDE.md symlinked to
it, docs/style guides, test and lint gates, Claude settings, cloud-agent docs,
CI, and a PR template. It's been around a while and has real code in it. No
interactive user: finish end to end, then tell me what you did.

## Assertions

- [ ] Skill `bootstrap` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./pipeline/pyproject.toml is byte-identical to the seeded workspace file
- [ ] ./package.json still has a `test` script that runs `node --test`
- [ ] ./src/worker.js is byte-identical to the seeded workspace file
- [ ] ./tsconfig.json does not exist
- [ ] ./pyproject.toml declares a uv workspace (`[tool.uv.workspace]`) whose members include `pipeline`
- [ ] ./Makefile has a `test` target that runs both the tests under ./pipeline and the JavaScript tests under ./test
- [ ] ./Makefile has a `lint` target that lints both the Python under ./pipeline and the JavaScript under ./src
- [ ] ./.github/workflows/ci.yml has separate jobs for the ./pipeline package and the root JavaScript package, and its `CI passed` job needs both
- [ ] ./pyproject.toml sets Ruff's `select` to a list that includes none of `ANN`, `D`, `F`, `PTH`, or `UP`
- [ ] The `pipeline` job in ./.github/workflows/ci.yml has no step that runs the pipeline's tests
- [ ] Neither ./Makefile nor ./.github/workflows/ci.yml installs the root JavaScript package with `npm ci` alone; each falls back to `npm install` when ./package-lock.json is missing
- [ ] No file under ./pipeline, ./src or ./test contains a `noqa`, `biome-ignore`, or `eslint-disable` comment
- [ ] ./.markdownlint-cli2.jsonc keeps ./prompts/summarize.md out of markdownlint's scope
- [ ] The final message gives existing lint findings counted by tool or rule family, and names a later stage that turns on Ruff's `ANN` or `D` rules
- [ ] The final message says a pipeline test reads the git-ignored ./pipeline/data/sources.json, so it fails in a clean checkout
- [ ] The final message says ./scripts/publish-docs.sh pushes to `main`, which the house rules forbid
- [ ] The final message says the existing commit subjects don't follow conventional commits
- [ ] The final message says the repo has no root README.md
