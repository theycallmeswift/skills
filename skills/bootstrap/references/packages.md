# Several packages

For a repo with more than one package, or one package outside the root. The
root gets workspace files and a `Makefile` that call each package's own
commands; the packages stay where they are.

## Write

These rows replace the main table's language rows; its core rows still apply.

| Asset | Destination | When |
| --- | --- | --- |
| `template-Makefile-packages` | `Makefile`: one block of targets per package, with `PACKAGES` listing their ids | always |
| `template-ci-packages.yml` | `.github/workflows/ci.yml`: one job and one path filter per package, all needed by `CI passed` | always |
| `template-pyproject-workspace.toml` | `pyproject.toml`: every Python package listed under `members`, `select` at the ramp's current stage | a Python package outside the root |
| `template-style-python.md`, `template-style-typescript.md` | `docs/style/python.md`, `typescript.md` | each language present |
| `template-biome.jsonc` | `biome.jsonc` at the root | a JavaScript or TypeScript package |

- **Package id:** the directory name, or a short name for the root package
  (`worker`). Use it in `PACKAGES`, the target names, and the CI job.
- **Commands:** each package's targets call the tools it already uses: its
  `test` script or runner, its lockfile. A JavaScript package's `lint` runs
  Biome on its own source paths, never `tsc`. A Node package with no
  lockfile installs with `npm install` (the template checks), and its
  missing lockfile is a gap.
- **One Python package at the root** keeps `template-pyproject.toml` only when
  no `pyproject.toml` exists; never write a second root project beside a
  member's.
- **npm workspaces** need a root `package.json` with `workspaces`. With two
  or more Node packages, report the missing workspace root as a gap; don't
  write one.
- **A member's own `uv.lock`** is superseded by the workspace lock once `uv
  sync` runs at the root. Report it, and anything that runs `uv` inside the
  member directory, so its owner can delete the old lock.
- **A member's own `[tool.ruff]`** overrides the root's for its files. Report
  it; you can't stage it.

Add the dev tools at the root: `uv add --dev pytest ruff ty` in the workspace,
and `npm install -D @biomejs/biome markdownlint-cli2` where a `package.json`
exists.

## Fill the placeholders

- `AGENTS.md` and `docs/cloud-agents.md`: `<install>`, `<test>`, and `<lint>`
  are the root `make` targets; `<runtime>` names every language's runtime.
  Where a package's tests need local state, replace the "needs no
  credentials" line with what they need.
- CI: drop the setup step a package's language doesn't need, and the Test step
  of a package whose tests can't run in a clean checkout, with a comment
  saying why.

## Report

Under `Gaps`, a suggested layout when the packages sit at mixed depths: apps
under `apps/`, scripts and pipelines under `tools/`. It is a recommendation
only; moving code is the owner's call.
