# bootstrap — eval record

Recorded 2026-10-11. Output evals from `iteration_05`; routing from `iteration_04`. Both used benchspec 0.0.5 (Docker sandbox) with Claude Code 2.1.296 in the guest and sonnet at `--count 3`. The baseline arm ran bare; the trial arm loaded the plugin via `--plugin-dir`. Re-run with `make evals SKILL=bootstrap EVAL_ARGS="-k repo --count 3 -n 8"` for output and `make evals SKILL=bootstrap EVAL_ARGS="-k 'triggers and trial' --count 3 -n 4"` for routing. Activation lines are scoped off baseline and excluded from these tallies; the skill fired in 6 of 6 trial output cells.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| existing-repo | 4/27 (15%) | 27/27 (100%) | +85pp |
| new-python-repo | 0/21 (0%) | 21/21 (100%) | +100pp |
| **Headline** (mean of per-sample rates) | **7%** | **100%** | **+93pp** (noise band ±2pp) |

## Routing evals — trial arm: 12/12

| Query | Expected | Result |
|---|---|---|
| house-setup | bootstrap invoked | 3/3 |
| fill-missing-setup | bootstrap invoked | 3/3 |
| cloud-session-hook | bootstrap not invoked | 3/3 |
| scaffold-nextjs | bootstrap not invoked | 3/3 |

## Notes

**What the skill fixes.**
- **Clobbering.** Told the pieces it should add, a bare agent rewrote `AGENTS.md`, replaced the real `CLAUDE.md` with a symlink (moving its note into `AGENTS.md`), and edited the `Makefile` in 3 of 3 runs. With the skill, every existing file stayed byte-identical in 3 of 3.
- **Gaps.** A bare agent reported what it changed, never what was missing. With the skill, the missing Landing changes section, the non-symlink `CLAUDE.md`, and the missing `format` target were reported in 3 of 3.
- **House content.** A bare agent invents its own PR template, style rules, and settings, and adds CI workflows and starter code nobody asked for. The decided rules (imports, testing tiers, landing) and the PR template only appear with the skill.

**The guest has no `make`, `uv`, or `python3`.** Gates can't run in the sandbox, so no eval grades them; trial agents reported them as "not run" rather than passing. The Python and TypeScript gates were checked by hand on fresh repos: `make test`/`make lint` and `npm test`/`npm run lint` all pass with and without a first test.

**The symlink assertion was dropped.** Every arm ran `ln -s AGENTS.md CLAUDE.md` once the prompt named it, and the judge can't tell a symlink from a copy (same SHA-256), so it failed one trial cell on evidence alone.

**The existing-repo no-clobber lines pass on a baseline that does nothing.** An earlier prompt that said only "my house setup" left the bare agent unsure what to build, so it touched nothing and passed them. Naming the pieces in the prompt made it try, and clobber.
