# bootstrap — eval record

Recorded 2026-11-20, when bootstrap learned to adopt multi-package repos (#68). Runs used benchspec 0.0.5 (Docker sandbox) and `claude-sonnet-5.5` through OpenRouter (`--set openrouter`, with binder and judge on OpenRouter too) at `--count 3`. Both eval sets in `pyproject.toml` set `UV_PROJECT_ENVIRONMENT`; see Notes. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Routing is from 2026-10-11, since the description didn't change. Activation lines are scoped off baseline and excluded from these tallies.

- **monorepo-adoption:** `iteration_05`, on stock benchspec 0.0.5 and the committed config.
- **The other three:** `iteration_04`, before the review fixes, on benchspec with a local patch that pipes the judge prompt on stdin. Their judge prompts were at most 64 KB, under the 128 KB argv cap that patch works around. The fixes left their templates and assertions unchanged, so they weren't re-run.

Re-run output and routing evals with:

```bash
uv run --group evals benchspec run --set openrouter --binder-provider openrouter \
  --judge-provider openrouter --judge-model anthropic/claude-sonnet-5.5 \
  --eval-paths evals/bootstrap -- -k 'repo or adoption' --count 3 -n 6
make evals SKILL=bootstrap EVAL_ARGS="-k 'triggers and trial' --count 3 -n 4"
```

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| existing-repo (`iteration_04`) | 6/27 (22%) | 27/27 (100%) | +78pp |
| new-python-repo (`iteration_04`) | 0/30 (0%) | 30/30 (100%) | +100pp |
| fresh-repo-no-main (`iteration_04`) | 0/12 (0%) | 11/12 (92%) | +92pp |
| monorepo-adoption (`iteration_05`) | 22/54 (41%) | 54/54 (100%) | +59pp |
| **Headline** (mean of per-eval rates) | **16%** | **98%** | **+82pp** |

The fresh-repo-no-main miss gave the branch and described the PR body without writing it out.

## Routing evals — trial arm: 12/12

| Query | Expected | Result |
|---|---|---|
| house-setup | bootstrap invoked | 3/3 |
| fill-missing-setup | bootstrap invoked | 3/3 |
| cloud-session-hook | bootstrap not invoked | 3/3 |
| scaffold-nextjs | bootstrap not invoked | 3/3 |

## Notes

**Multi-package adoption (`monorepo-adoption`).** The fixture is a Python package in `pipeline/` with its own `uv.lock`, a plain-JavaScript Worker at the root with no lockfile, and a pipeline test that reads git-ignored `pipeline/data/sources.json`. It also has LLM prompts under `prompts/`, a docs script that pushes to `main`, non-conventional commit subjects, and no README. A bare agent flagged the data test and the push-to-`main` script on its own. In 3 of 3 it still did all of the following:
- edited the member's `pyproject.toml`;
- wrote no workspace root and no per-package CI jobs;
- wrote CI that runs the data test and uses `npm ci` with no lockfile;
- left markdownlint on `prompts/`;
- reported no lint baseline, README gap, or commit-style clash.

With the skill, all 3 samples wrote a uv workspace root and a per-package `Makefile` and CI. Each set Ruff `select` to `B, E, I, N, RUF, SIM, W`, leaving out every family with findings (`ANN`, `D`, `F`, `PTH`, `UP`). Each fell back to `npm install` without a lockfile, kept the data test in `make test` but out of CI, and scoped markdownlint off `prompts/`. Each reported the baseline, ramp, clashes, and missing README.

**Keeping the monorepo eval gradeable.** benchspec inlines every workspace file into one judge prompt, passed as a single argv string that Linux caps at 128 KB. The fixture installs uv but not Node, so `npm install` can't fill `node_modules`. In `iteration_04` one trial agent installed Node itself, and that cell errored as infra. The eval sets' `UV_PROJECT_ENVIRONMENT` keeps uv's venv out of the workspace, where its dangling `python` symlink would crash fact collection.

**What the skill fixes.**
- **Clobbering.** Told the pieces it should add, a bare agent rewrote `AGENTS.md`, replaced the real `CLAUDE.md` with a symlink (moving its note into `AGENTS.md`), and edited the `Makefile` in 3 of 3 runs. With the skill, every existing file stayed byte-identical in 3 of 3.
- **Gaps.** A bare agent reported what it changed, never what was missing. With the skill, the missing Landing changes section, the non-symlink `CLAUDE.md`, and the missing `format` target were reported in 3 of 3.
- **House content.** A bare agent invents its own PR template, style rules, settings, and CI, and adds starter code nobody asked for. The decided rules (imports, testing tiers, landing), the PR template, and the CI workflow that skips tests on docs-only PRs behind one `CI passed` check only appear with the skill.

**The guest has no `make`, `uv`, or `python3`.** Gates can't run in the sandbox, so no eval grades them; trial agents reported them as "not run" rather than passing. The Python and TypeScript gates were checked by hand on fresh repos: `make test`/`make lint` and `npm test`/`npm run lint` all pass with and without a first test.

**The symlink assertion was dropped.** Every arm ran `ln -s AGENTS.md CLAUDE.md` once the prompt named it, and the judge can't tell a symlink from a copy (same SHA-256), so it failed one trial cell on evidence alone.

**The existing-repo no-clobber lines pass on a baseline that does nothing.** An earlier prompt that said only "my house setup" left the bare agent unsure what to build, so it touched nothing and passed them. Naming the pieces in the prompt made it try, and clobber.

**The no-`main` path.** `fresh-repo-no-main` is a repo whose only branch is `claude/*`, with an `origin` that has no `main`; a hook on the remote mirrors its branches into `.fake-origin/branches.txt` for the judge. Run at `--count 3` on Claude Code 2.1.296 in benchspec's Docker sandbox. A bare agent committed on its branch and never pushed in 3 of 3. With the skill, an empty root `main`, the setup on a new branch, a PR body naming the branch, and the default-branch note appeared in 3 of 3. The existing-repo and new-python-repo trial arms, which have no remote, re-ran at `--count 1` after the change and passed 9/9 and 7/7.

**Keep the workspace's git dir out of `/workspace`.** The judge reads every file there as text, and a tiny loose object such as the empty tree decodes as text with NUL bytes, which the judge call rejects. The setup uses `--separate-git-dir`. Agents that install `uv` and leave a `.venv` can also crash fact collection on its dangling `python` symlink, which benchspec reads through; that cost one trial cell an early run and one in each of the two 2026-10-16 runs. A crashed cell is ungraded, not failed.
