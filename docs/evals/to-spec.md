# to-spec — eval record

Recorded 2026-09-04 from `iteration_16` (harnessbench 0.0.1, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet). Re-run with `make evals SKILL=to-spec`.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| spec-from-context | 4/12 (33%) | 11/12 (91%) | +58pp |
| too-thin-defers | 4/4 (100%) | 4/4 (100%) | +0pp |
| under-determined-open-questions | 1/6 (16%) | 6/6 (100%) | +84pp |
| **All (pooled)** | 9/22 (40%) | 21/22 (95%) | +55pp |

## Routing evals — trial arm: 20/20

| Query | Expected | Result |
|---|---|---|
| build-a-skill | not invoked | pass |
| capture-as-spec | invoked | pass |
| context-to-spec | invoked | pass |
| design-doc-from-here | invoked | pass |
| draft-spec | invoked | pass |
| export-session | not invoked | pass |
| handoff-doc | not invoked | pass |
| hardware-spec | not invoked | pass |
| impl-plan | not invoked | pass |
| ingest-source | not invoked | pass |
| notes-page | not invoked | pass |
| openapi-spec | not invoked | pass |
| prd-migration | invoked | pass |
| spec-the-feature | invoked | pass |
| spec-this-out | invoked | pass |
| summarize-readonly | not invoked | pass |
| tighten-prompt | not invoked | pass |
| turn-into-spec | invoked | pass |
| write-up-spec | invoked | pass |
| writeup-decision | invoked | pass |

## Notes

**`spec-from-context` — one recurring miss.** The prompt says the cache size is unresolved and must be flagged, not guessed; in roughly two of five samples across runs the spec states "capacity 256" as settled in Solution / Implementation Decisions instead of parking it under Open Questions. Everything else in that scenario — the grounded "no TTL exists in `./service/reads.py`" finding, the skim-first structure, the Testing Plan as a coverage contract — holds. That single behaviour is the first thing a tuning pass on the skill's step 4/5 wording should address.

**Migration note.** "Exactly one spec file exists under `./docs/specs/`" now reads "Exactly one `*.md` file", matching the sibling scenario: harnessbench binds the line to a file count, and the seeded `.gitkeep` was making the count two.

**Routing: 20/20 on sonnet, with a recap.** The ten positives carry a short shared `history:` recap of a design discussion. Without it, three positives ("draft a design spec from what we discussed", "write the design spec for the feature we just designed", "spec this out before we lose the thread") don't route in an empty session — the agent correctly says there is nothing to write up — and the upstream suite had annotated most of these positives as sonnet misses. With something to refer to, all ten route on sonnet.
