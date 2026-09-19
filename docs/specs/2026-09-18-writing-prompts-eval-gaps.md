**TL;DR** — Split `vague-triage-intent` into an ask eval and an answered-draft eval so it grades the path the skill prescribes, and try one general description fix for the sonnet routing miss on `docs/*.md` convention files.

## Problem

- **Symptom:** `vague-triage-intent` scores 51% on trial. The skill says to ask when an ask is vague; the eval's draft-shaped assertions fail whenever the agent asks.
- **Symptom:** `writing-tests-doc` routing misses on sonnet (9/10). The body claims on-demand `docs/*.md` references; the description only names `docs/*.md` "that an agent will read as context", which a team conventions doc doesn't say.
- **Scope:** `evals/writing-prompts/` and the `description:` of `skills/writing-prompts/SKILL.md`.
- **Constraint:** fixes stay general. No trigger phrase written to match one query.

## Solution

```
evals/writing-prompts/vague-triage-intent/eval.md      asserts: asks scoping questions, drafts nothing
evals/writing-prompts/vague-triage-answered/eval.md    history: same ask + questions + answers; asserts the draft
skills/writing-prompts/SKILL.md description            `docs/*.md` conventions or reference docs agents load
```

Each eval grades one path. The description names the doc class the body already owns.

## User Stories

1. As the maintainer, I want **each eval to grade one path**, so a low score means the skill regressed, not that the eval disagreed with it.
2. As a user, I want **a conventions doc under `docs/` to route to writing-prompts**, so it gets the four ingredients and the editorial pass.

## Implementation Decisions

```
vague ask ──► SKILL.md §Workflow 1 "ask before drafting" ──► vague-triage-intent (questions, no draft)
answered  ──► §Workflow 3–6 draft + editorial pass      ──► vague-triage-answered (draft assertions)
```

- **Ask eval asserts behavior, not format.** At least one scoping question; no drafted prompt; ends waiting on the user.
- **Answered eval reuses the current draft assertions.** `history:` holds the vague ask, a short scoping reply, and concrete answers (ticket source, priority taxonomy, output consumer).
- **Description edit is one clause.** Widen the `docs/*.md` clause to convention/reference docs agents load. Keep every negative trigger.
  - If no general wording routes the query without breaking a negative, revert and record the miss as a sonnet model-tier boundary.

## Testing Plan

### Behavior
- **Vague ask gets questions, not a draft** on trial.
- **Answered ask gets a structured draft** with role, delimiters, output shape, and a tightened final version.
### Interface
- **Routing holds on every existing query**, positives and negatives, with the full plugin loaded.
- **`writing-tests-doc` routes on sonnet**, or is recorded as a boundary.
### Logic
- N/A — no scripts change.

## Documentation Plan

- **`docs/evals/writing-prompts.md`**: re-record from the new run; drop the ask-or-draft note.

## Out of Scope

- Body changes to `skills/writing-prompts/SKILL.md`. The body already prescribes asking.

## References

- `docs/evals/writing-prompts.md` — the 51% result and the sonnet miss.
- `skills/writing-prompts/SKILL.md` — Workflow step 1; Triage bucket naming `docs/writing-tests.md`.

## Verification

- `make evals:lint` — suites parse, no lint findings.
- `make evals SKILL=writing-prompts` — trial beats baseline on both split evals; routing ≥ 9/10.
- `make test && make lint` — green.
