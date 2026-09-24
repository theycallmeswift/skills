**TL;DR** — Add a `catch-me-up` skill that re-orients Swift on the *current* session after returning cold, narrating from context but verifying every hard fact against git and `gh` before it speaks.

## Problem

- **Symptom:** returning to a session after an overnight gap means re-reading the thread to recover what was being built, what landed, and what is waiting on a decision. Nothing in `skills/` covers it.
- **Exposed by:** running 5–8 parallel sessions across repos, where the context switch cost is paid on every re-entry, not just after sleep.
- **Scope:** one new skill directory `skills/catch-me-up/` plus its evals. No changes to existing skills or to `hooks/`.
- **Constraint:** the recap is written for a reader without full project context — it names the repo, glosses jargon, and restates the *why* before the *what*.
- **Constraint:** narration comes from the context window, but a recalled fact that the tree contradicts must never reach the reader. Memory goes stale precisely where it costs most — tests observed green at 23:00, CI red at 06:00.

## Solution

```
skills/catch-me-up/SKILL.md      model-invoked: "catch me up", "where were we"

  §Verify (before emitting)      git status --short
                                 git log main..HEAD --oneline
                                 gh pr view --json state,statusCheckRollup

  §Output                        TL;DR  ***  Cliff Notes  ***  Next Up (You: / Me:)
```

Hard facts come from the verify pass; narrative comes from memory. The output grammar is lifted from the web-page summarize prompt Swift already uses.

<details><summary>Rendered example</summary>

### TL;DR

You're adding a feature to **MechaSwift**, your personal agent-skills plugin — specifically making one skill hand off grunt work to a throwaway helper agent instead of doing it itself. The code is written and the pull request is up, but an automated check failed overnight. One design question is waiting on you; the failure is mine to fix.

***

### Cliff Notes

- **The project:** `mechaswift` is your repo of reusable *skills* — instruction files that teach an agent how to do a specific job the same way every time. This work is on the skill that helps you **write other skills**.
- **What the issue asks for:** when that skill needs to read another skill's instructions, it should **spin up a cheap throwaway subagent** to go read it and report back, *rather than pulling the whole file into the main conversation.* The point is keeping your working context clean.
- **Where it stands:** the change is written and **the pull request is open** — 3 commits, ready for your eyes.
- **Local checks passed** last night at 23:15. *`make test` runs the test suite; `make lint` checks style. Both green.*
- **The overnight failure:** CI went red at 06:02 on two errors from **`ty`**, the type-checker added to this repo last week. *It's flagging a mismatch in `scripts/run_eval.py` — bookkeeping, not a flaw in the feature.*
- **The open question we punted on:** should the helper agent **always** use the cheap model, or should the caller pick? We shipped the PR without deciding so it wouldn't block.

***

### Next Up

**You:** Decide the helper-agent model question — always-cheap, or caller's choice. *Always-cheap is simpler and the job is trivial.* Then give the pull request a look.

**Me:** Fix the two `ty` errors, re-run the local checks, push. No decision needed from you first.

</details>

## User Stories

1. As Swift returning overnight, I want **the repo and its purpose named before the delta**, so I do not have to reconstruct what the project is before I can read the update.
2. As Swift, I want **CI and branch state read from the tree, not recalled**, so "tests are green" is never eight hours stale.
3. As Swift, I want **what needs me split from what the agent can clear**, so I spend my first five minutes on the decision and nothing else.
4. As Swift, I want **the skill to admit when its context was compacted**, so a visible gap replaces a confident invention.
5. As Swift in a session with no repository — research, planning, a scratch thread — I want **the recap to still run**, so re-entry works the same everywhere rather than only where there is a branch to inspect.
6. As the maintainer, I want **one output shape, not a terse/verbose pair**, so there is one eval surface and no flag to remember at 9am.

## Implementation Decisions

```
"catch me up" ──► skills/catch-me-up/SKILL.md
                    ├─► §Verify: git status / git log main..HEAD / gh pr view   ──► hard facts
                    └─► context window                                          ──► narrative
                                                                                     │
                    §Output: TL;DR ─*** ─ Cliff Notes ─ *** ─ Next Up  ◄─────────────┘
```

- **Warm narration, verified facts.** The skill does not parse transcripts or rebuild from git history.
  - Branch, PR number, CI state, dirty tree, commit count: verified or not stated.
  - Calls that do not apply are skipped — no repo, no PR, no failure.
- **The skill fires wherever it is invoked, repository or not.** Grounding is a bonus, not a precondition.
  - With no repo the verify pass degrades to nothing and the recap is pure warm narration. It still emits all three sections.
  - It makes no branch, PR, or CI claims rather than reporting their absence as news.
  - Declining in a research or planning thread would fail exactly the re-entry the skill exists to serve.
- **Compaction is disclosed, not repaired.** If context was compacted, the TL;DR says so and Cliff Notes covers only what remains. No transcript read, no gap-filling.
- **The output grammar is fixed.** `***` between sections, never `---`.
  - **TL;DR** — 1–2 sentences of normal body text, not a heading or bold block.
  - **Cliff Notes** — 5–8 bullets, 1–2 sentences each; **bold** for names and critical facts, *italics* for nuance; ordered by importance, not chronology.
  - **Next Up** — **You:** what needs a decision; **Me:** what the agent can clear unblocked.
- **Always-explaining register, single shape.** Cheaper to eval, and never wrong for the only reader this skill has.
- **Five output evals, each planting one way the skill could lie or refuse.**
  - `stale-state` — context claims green; scripted `git`/`gh` fakes report red and a dirty tree. The only eval that proves the verify pass runs.
  - `invented-artifacts` — a file discussed but never written must not appear as progress.
  - `compaction-honesty` — context begins mid-thread; the gap must be flagged.
  - `empty-ownership` — nothing pending on Swift; the **You:** slot must say so rather than manufacture a decision to fill itself.
  - `no-repo-session` — a workspace with no `.git` at all. The recap must still emit, and must not claim or invent branch, PR, or CI state.
- **Fixtures are curated real captures in the native shape.** Each scenario carries a sibling `session.jsonl` loaded via `history: ./session.jsonl`.
  - Real captures as raw material so transcripts carry genuine tool-call rhythm; doctored because four of the five scenarios are *defined* by a discrepancy no real session contains.
  - Native `{"role","content"}` over Claude Code vendor shape: ~14.6k tokens per 20 turns against ~68.6k, and no hand-maintained `uuid`/`parentUuid` chain while trimming.
  - Depends on theycallmeswift/benchspec#151 for the path form. Inline `history:` turns are the drop-in fallback — that issue keeps the list form working, so nothing here blocks.
  - **The transcript must sit inside its own scenario folder.** That change rejects a path escaping the eval directory, so `session.jsonl` cannot be shared from `evals/support/` the way `fake-codex/setup.sh` is sourced.
- **The scripted fakes follow the existing shared-fake layout.** `evals/support/fake-git/` alongside `evals/support/fake-codex/`, sourced from each scenario's `setup.sh`. `no-repo-session` sources nothing and ships a workspace without `.git`.

## Testing Plan

### Logic
- **A fact the verify pass contradicts never reaches the output** — where recalled state and observed state disagree, the observed state is what is reported.
- **Inapplicable verify calls degrade silently** — a session with no PR produces a recap with no PR claims, not an error and not an invented one.

### Behavior
- **A recap emits exactly the three sections in order**, separated by `***`, with TL;DR as body text rather than a heading.
- **Progress claims are restricted to artifacts that exist** — a file discussed but never written is absent from Cliff Notes, or marked as planned.
- **A compacted context is disclosed in the TL;DR** and the bullets cover only surviving turns.
- **An empty ownership slot is reported as empty** rather than filled with a fabricated decision.
- **A workspace with no repository still produces a full recap** — three sections, no refusal, and no branch, PR, or CI claim in the output.
- **Jargon is glossed** — the recap names the repo and its purpose, and explains tooling terms rather than assuming them.

### Interface
- **Trigger routing** — "catch me up", "where were we", "what's the state here" activate the skill, in a repository or not; requests for a cross-session or multi-repo survey do not.

## Documentation Plan

- **`README.md`**: add the `catch-me-up` bullet to the skills list, matching the existing one-line-plus-trigger-phrases form.
- **`CLAUDE.md`**: add `catch-me-up` to the `## Skills` list.
- **`skills.sh.json`**: add `catch-me-up` to the appropriate Hermes hub category.
- **`docs/evals/catch-me-up.md`**: record the benchmark once the suite runs, matching the existing per-skill eval docs.

## Out of Scope

- **Cross-session portfolio standup.** "What is happening across all my work" is a real want and a separate skill; this one recaps the session it runs in.
- **Auto-firing from `hooks/session-start`.** The hook exists and could emit a recap unprompted, but it runs on every resume including twenty-second ones, spending tokens uninvited. Model-invoked keeps it opt-in and yields clean trigger/not-trigger evals.
- **Transcript parsing at runtime.** Rebuilding the session from `~/.claude/projects/**/*.jsonl` was considered and rejected — warm narration plus a cheap verify pass covers the failure that actually bites, at a fraction of the cost.
- **A terse mode.** Two shapes, two eval sets, and a flag nobody remembers at 9am.
- **A paste-ready resume prompt.** The analog of the summarize prompt's "Share on Slack" section; **Next Up** carries it.
- **Per-line citations.** Turns a briefing into an audit log.
- **Vendor-shaped fixtures.** 4.7x the tokens and manual `uuid` bookkeeping; revisit only if an eval shows the skill needs raw `tool_use` blocks to work.

## References

- [theycallmeswift/mechaswift#39](https://github.com/theycallmeswift/mechaswift/issues/39) — the tracking issue this spec grounds, written from the same interview.
- [theycallmeswift/benchspec#151](https://github.com/theycallmeswift/benchspec/issues/151) — adds the `history: ./session.jsonl` path form, and supplies the token figures and the eval-folder containment rule cited above.
- `evals/support/fake-codex/` — the shared-fake layout (`README.md`, `lib.sh`, `setup.sh`) the `git`/`gh` fakes follow; `evals/delegating-to-codex/python3-missing/setup.sh` shows the one-line source.
- `evals/interview-me/` — the per-skill eval layout this mirrors: one directory per scenario, plus `triggers/` and `not-triggers/`.
- `hooks/hooks.json` — the `SessionStart` hook deliberately left untouched.
- `skills/writing-agent-skills/references/skill-conventions.md` — frontmatter, layout, and portability rules the new `SKILL.md` must satisfy.

## Verification

- `make lint` — ruff and ty pass on anything added under `tests/` or `evals/support/`.
- `make test` — the suite stays green with the new skill present.
- `make evals SKILL=catch-me-up` — the five output scenarios plus `triggers/` and `not-triggers/` collect and run, baseline versus trial.
