# to-spec — eval record

Recorded 2026-09-04 from `iteration_28`, `iteration_29` (benchspec 0.0.1, Claude Code in the guest; baseline bare, trial with the plugin loaded via `--plugin-dir`, sonnet). Re-run with `make evals SKILL=to-spec`.

## Output evals — baseline vs trial

| Eval | baseline | trial | Δ |
|---|---|---|---|
| spec-from-context | 4/12, 5/12, 2/12 (30%) | 12/12, 12/12, 12/12 (100%) | +70pp |
| too-thin-defers | 4/4 (100%) | 4/4 (100%) | +0pp |
| under-determined-open-questions | 1/6 (16%) | 6/6 (100%) | +84pp |
| **All (pooled)** | 16/46 (34%) | 46/46 (100%) | +66pp |

## Routing evals — trial arm: 20/20

| Query | Expected | Result |
|---|---|---|
| build-a-skill | to-spec not invoked | pass |
| export-session | to-spec not invoked | pass |
| handoff-doc | to-spec not invoked | pass |
| hardware-spec | to-spec not invoked | pass |
| impl-plan | to-spec not invoked | pass |
| ingest-source | to-spec not invoked | pass |
| notes-page | to-spec not invoked | pass |
| openapi-spec | to-spec not invoked | pass |
| summarize-readonly | to-spec not invoked | pass |
| tighten-prompt-reliably | to-spec not invoked | pass |
| capture-as-spec | to-spec invoked | pass |
| context-to-spec | to-spec invoked | pass |
| design-doc-from-here | to-spec invoked | pass |
| draft-spec | to-spec invoked | pass |
| prd-migration | to-spec invoked | pass |
| spec-the-feature | to-spec invoked | pass |
| spec-this-out | to-spec invoked | pass |
| turn-into-spec | to-spec invoked | pass |
| write-up-spec | to-spec invoked | pass |
| writeup-decision | to-spec invoked | pass |

## Notes

**`spec-from-context` — clean under benchspec, one thing to watch.** All four trial samples (the suite pass plus a 3× re-sample) score 12/12: the grounded "no TTL exists in `./service/reads.py`" finding, the skim-first structure, the Testing Plan as a coverage contract, and the unresolved cache size parked under Open Questions. Earlier runs had the spec state "capacity 256" as settled in about two of five samples.

**Migration notes.** "Exactly one spec file exists under `./docs/specs/`" reads "Exactly one `*.md` file", matching the sibling scenario: benchspec binds the line to a file count, and the seeded `.gitkeep` was making the count two. The ten positives carry a short shared `history:` recap of a design discussion; without it, three of them ("draft a design spec from what we discussed", "write the design spec for the feature we just designed", "spec this out before we lose the thread") don't route in an empty session because the agent correctly says there is nothing to write up.

**Routing: 20/20 on sonnet.** Every positive routes with the recap in place (the upstream suite had most of them annotated as sonnet misses when run bare), and every near-miss stays quiet — including the asks that belong to `writing-prompts` and `writing-agent-skills` and the ones that belong to skills not in this plugin (`handoff`, `ingest`, `archive`, `writing-plans`), which can only ever be plain near-misses of the description.
