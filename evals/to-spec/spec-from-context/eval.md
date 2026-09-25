---
---

## Prompt

Use the `to-spec` skill to capture this read-through cache design as a spec before
we lose the context. Repo root: your current working directory. We've been
designing a read-through cache for the widget service. The design we landed on: put
a 256-entry in-process LRU in front of `service/reads.py`'s `read_widget`,
invalidate an entry whenever `service/writes.py`'s `write_widget` touches that
widget, and leave distributed/shared caching out for now. The whole point is cutting
DB load on hot widgets. Important: this design assumes we can reuse the 30-second
cache TTL I said is already hardcoded in `reads.py` — the spec must state whether
that assumption actually holds, checked against the file, not take my word for it. We
weren't sure what cache size to ship if 256 turns out too small; flag that, don't
guess.

Today is {TODAY}. No interactive user — proceed end-to-end, then tell me where you
wrote it.

## Assertions

- [ ] Skill `to-spec` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] A spec file was written at './docs/specs/{TODAY}-<slug>.md' — the filename is today's date plus a kebab-case slug derived from the title, with NO '-design' suffix
- [ ] Exactly one `*.md` file exists under './docs/specs/'
- [ ] The spec opens with a one-line TL;DR and contains all of these H2 sections: Problem, Solution, User Stories, Implementation Decisions, Testing Plan, Documentation Plan, Out of Scope, References, Verification
- [ ] The Problem section uses labeled bullets (e.g. Symptom / Constraint), not multi-sentence paragraphs
- [ ] The Solution section leads with a short copy-pasteable artifact (a code/config snippet) followed by no more than two sentences of prose
- [ ] Implementation Decisions contains a flow diagram whose nodes map to real symbols/paths from the repo (e.g. `./service/reads.py` read_widget, `./service/writes.py` write_widget)
- [ ] The Testing Plan is a coverage contract grouped under derived surfaces named Logic / Behavior / Interface — each entry states an observable guarantee, with NO test function names, file paths, or case counts, and NO runnable commands (commands live under Verification)
- [ ] The spec states that the assumed 30-second cache TTL does NOT exist in `./service/reads.py` (the file has no TTL constant and no caching), rather than repeating the assumption as fact or omitting any mention of it — the perishable-fact grounding the skill must do against the live tree
- [ ] The unresolved cache-size question appears under a '## Open Questions' section, not asserted as a settled decision in Problem/Solution/Implementation Decisions
- [ ] References and Verification are both present and non-empty; Verification lists runnable done-criteria commands
