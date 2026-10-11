# <Project>

<What the project is and who uses it, its language and runtime, and how
settled the code is. Two or three sentences.>

## Autonomy

- **Freely reversible: just do it.** Edits, local commands, scratch files,
  branches.
- **Consequential: state intent, then proceed.** Pushing a branch, opening a
  PR, adding a dependency.
- **Irreversible: always confirm first.** Force-pushing a shared branch,
  deleting branches or data, anything posted outside the repo.

## Decision principles

- **Propose, then confirm.** For design choices, present 2–3 options with a
  recommendation before writing code.
- **Action over asking.** Exhaust reversible options (read the code, run a
  small experiment) before asking.
- **Simple over clever.** Question whether a concept needs to exist before
  adding one.
- **Concise over verbose.** Lead with the point; cut preamble.

## Conventions

- Ask one question at a time.
- Follow existing patterns in the file you're touching.
- Use conventional commits (`feat:`, `fix:`, `docs:`, `chore:`).
- Before claiming work is done, run `<test>` and `<lint>` and show the output.
- Keep `docs/` current: read the relevant doc before changing architecture,
  and update it in the same PR.

## Environment

- Needs <runtime>; run `<install>` when the lockfile changes.
- `<lint>` runs markdownlint through `npx`, so it also needs Node.
- `<test>` needs no credentials. Cloud setup: `docs/cloud-agents.md`.

## Landing changes

- Open every PR as a draft from `.github/pull_request_template.md`. Mark it
  ready yourself once every Ready gate row has evidence. If CI fails after
  that, convert it back to a draft, fix it, and mark it ready again.
- The PR body carries no process narrative and no line-number citations.
- Every PR lands on `main` as one squash commit, through GitHub's merge only.
  Never push to or rewrite `main`. Update a branch by rebase, or by merging
  `main` into it; the squash keeps history linear.

## Project structure

- `docs/*.md`: undated guides, one per feature or setup, indexed in
  `README.md`.
- `docs/specs/`, `docs/research/`: dated `YYYY-MM-DD-<slug>.md` files, created
  with the first one.
- `docs/style/`: how code, tests, and docs are written.
- `tmp/`: scratch space, git-ignored.

## References

Load on demand, not at session start.

- `docs/style/development.md`: code style. Read before changing source, tests,
  or docs, then the guide it names.
- `docs/cloud-agents.md`: cloud agent setup.
- `README.md`: human-facing overview.
