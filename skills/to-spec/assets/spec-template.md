<!-- Copy this file, fill every section, and delete every HTML comment as you fill it.
     Leftover comments and placeholder words (TODO/TBD/FIXME) fail validation. Keep the
     section order and headings exactly. Delete the Open Questions section entirely if none. -->

**TL;DR** — <!-- one line: the change + the why. No preamble, no "this spec proposes". -->

## Problem

<!-- Labeled bullets, never paragraphs. Use the labels that fit (drop the rest): -->
- **Symptom:** <!-- what is visibly wrong today -->
- **Why it stayed hidden:** <!-- optional: why it wasn't caught earlier -->
- **Exposed by:** <!-- optional: what surfaced it now -->
- **Scope:** <!-- the boundary of the problem being solved -->
- **Constraint:** <!-- a hard requirement the solution must respect -->

## Solution

<!-- Lead with the copy-pasteable artifact (~5 lines): the config/snippet/command that IS the change. -->
```
<the artifact>
```
<!-- Then at most two sentences of prose. Stop. -->

## User Stories

<!-- Dedup. Bold the differentiator so the eye skips the repeated "As a … I want" opening. -->
1. As a <role>, I want **<the differentiator>**, so <payoff>.
2. As a <role>, I want **<the differentiator>**, so <payoff>.

## Implementation Decisions

<!-- A flow diagram whose nodes are REAL symbols / paths / commands from the codebase — it doubles
     as the implementation skeleton. -->
```
<input> ──► <step: real symbol> ──► <step: real symbol> ──► <terminal artifact>
```

- **<bold claim>.** <the specifics as sub-bullets.>
  - <detail>
- **<bold claim>.** <the specifics.>

## Testing Plan

<!-- A coverage contract: one-line GUARANTEES, not test names, file paths, or case counts (the
     implementation plan enumerates tests). No commands here — those live under Verification.
     Derive the surfaces; instantiate Interface to THIS artifact: a skill → trigger routing; a
     service → its API contract + authz; a CLI → args + exit codes; a library → consumer back-compat.
     Pick only surfaces that genuinely apply; declare one N/A with a one-line reason rather than
     manufacturing an empty bucket. -->
### Logic
- **<guarantee>** — <what is true when it passes.>
### Behavior
- **<guarantee, the artifact run for real and its output observed>**
### Interface
- **<guarantee at the boundary the outside invokes/consumes it through>**

## Open Questions

<!-- CONDITIONAL: include ONLY when the context under-determines the spec. If nothing is open,
     DELETE this whole section. Never leave it empty. One bullet per genuinely-open decision —
     the honest home for what the synthesis could not ground, never padded into confident prose. -->
- <the open decision, phrased as a question, plus what would resolve it.>

## Documentation Plan

- **<path>**: <what to update — no prose paragraphs.>

## Out of Scope

- <explicit negative scope: what this deliberately does NOT do, and why if non-obvious.>

## References

<!-- Required, every time. Linked issues / PRs / prior art / files that ground the proposal. -->
- <#NN / link / path> — <why it grounds this.>

## Verification

<!-- Required, every time. Runnable done-criteria commands. -->
- `<command>` — <what passing proves.>
