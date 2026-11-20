# bootstrap — eval record

Recorded 2026-11-20, when bootstrap learned to adopt multi-package repos (#68). Output evals from `iteration_04`, with benchspec 0.0.5 (Docker sandbox), `claude-sonnet-5.5` through OpenRouter (`--set openrouter`, binder and judge on OpenRouter too) at `--count 3`; routing from 2026-10-11, since the description didn't change. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with:

```bash
uv run --group evals benchspec run --set openrouter --binder-provider openrouter \
  --judge-provider openrouter --judge-model anthropic/claude-sonnet-5.5 \
  --env UV_PROJECT_ENVIRONMENT=/srv/relay-venv --eval-paths evals/bootstrap \
  -- -k 'repo or adoption' --count 3 -n 6
```

Activation lines are scoped off baseline and excluded from these tallies.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| existing-repo | 6/27 (22%) | 27/27 (100%) | +78pp |
| new-python-repo | 0/30 (0%) | 30/30 (100%) | +100pp |
| fresh-repo-no-main | 0/12 (0%) | 11/12 (92%) | +92pp |
| monorepo-adoption | 20/48 (42%) | 32/32 (100%), 2 of 3 samples graded | +58pp |
| **Headline** (`iteration_04`, mean of per-sample rates) | **16%** | **98%** | **+82pp** |

One monorepo-adoption trial sample installed Node itself and ran `npm install`, and the judge rejected the resulting `node_modules` as too long a prompt; see Notes. The fresh-repo-no-main miss gave the branch and described the PR body without writing it out.

## Routing evals — trial arm: 12/12

| Query | Expected | Result |
|---|---|---|
| house-setup | bootstrap invoked | 3/3 |
| fill-missing-setup | bootstrap invoked | 3/3 |
| cloud-session-hook | bootstrap not invoked | 3/3 |
| scaffold-nextjs | bootstrap not invoked | 3/3 |

## Notes

**Multi-package adoption (`monorepo-adoption`).** A Python package in `pipeline/` with its own `uv.lock`, a plain-JavaScript Worker at the root, a pipeline test that reads git-ignored `pipeline/data/sources.json`, LLM prompts under `prompts/`, a docs script that pushes to `main`, non-conventional commit subjects, and no README. A bare agent flagged the data test and the push-to-`main` script on its own, but in 3 of 3 it edited the member's `pyproject.toml`, wrote no workspace root or per-package CI, left markdownlint on `prompts/`, and reported no lint baseline, README gap, or commit-style clash; one sample also skipped the data test in place and fixed lint findings in existing code. With the skill, every graded sample wrote a uv workspace root and a per-package `Makefile` and CI, staged Ruff `select` to the families with no findings (leaving out `ANN`, `D`, `F`, `UP`), scoped markdownlint off `prompts/`, kept the data test in `make test` but out of CI, and reported the baseline, ramp, clashes, and missing README. The earlier single-language evals held at 100% except the one fresh-repo-no-main sample above.

**The monorepo fixture keeps the judge's prompt small.** benchspec inlines every workspace file into one judge prompt. The setup provisions uv but not Node, so `npm install` can't fill `node_modules`; a trial agent that installs Node itself still can, and that cell errors. `UV_PROJECT_ENVIRONMENT` keeps the venv out of the workspace, where its dangling `python` symlink would crash fact collection. benchspec 0.0.5 passes the judge prompt as one argv string, which Linux caps at 128 KB; this run used a local patch that pipes it on stdin instead.

**What the skill fixes.**
- **Clobbering.** Told the pieces it should add, a bare agent rewrote `AGENTS.md`, replaced the real `CLAUDE.md` with a symlink (moving its note into `AGENTS.md`), and edited the `Makefile` in 3 of 3 runs. With the skill, every existing file stayed byte-identical in 3 of 3.
- **Gaps.** A bare agent reported what it changed, never what was missing. With the skill, the missing Landing changes section, the non-symlink `CLAUDE.md`, and the missing `format` target were reported in 3 of 3.
- **House content.** A bare agent invents its own PR template, style rules, settings, and CI, and adds starter code nobody asked for. The decided rules (imports, testing tiers, landing), the PR template, and the CI workflow that skips tests on docs-only PRs behind one `CI passed` check only appear with the skill.

**The guest has no `make`, `uv`, or `python3`.** Gates can't run in the sandbox, so no eval grades them; trial agents reported them as "not run" rather than passing. The Python and TypeScript gates were checked by hand on fresh repos: `make test`/`make lint` and `npm test`/`npm run lint` all pass with and without a first test.

**The symlink assertion was dropped.** Every arm ran `ln -s AGENTS.md CLAUDE.md` once the prompt named it, and the judge can't tell a symlink from a copy (same SHA-256), so it failed one trial cell on evidence alone.

**The existing-repo no-clobber lines pass on a baseline that does nothing.** An earlier prompt that said only "my house setup" left the bare agent unsure what to build, so it touched nothing and passed them. Naming the pieces in the prompt made it try, and clobber.

**The no-`main` path.** `fresh-repo-no-main` is a repo whose only branch is `claude/*`, with an `origin` that has no `main`; a hook on the remote mirrors its branches into `.fake-origin/branches.txt` for the judge. Run at `--count 3` on Claude Code 2.1.296 in benchspec's Docker sandbox. A bare agent committed on its branch and never pushed in 3 of 3. With the skill, an empty root `main`, the setup on a new branch, a PR body naming the branch, and the default-branch note appeared in 3 of 3. The existing-repo and new-python-repo trial arms, which have no remote, re-ran at `--count 1` after the change and passed 9/9 and 7/7.

**Keep the workspace's git dir out of `/workspace`.** The judge reads every file there as text, and a tiny loose object such as the empty tree decodes as text with NUL bytes, which the judge call rejects. The setup uses `--separate-git-dir`. Agents that install `uv` and leave a `.venv` can also crash fact collection on its dangling `python` symlink, which benchspec reads through; that cost one trial cell an early run and one in each of the two 2026-10-16 runs. A crashed cell is ungraded, not failed.
