**TL;DR** — Make writing-agent-skills actually invoke `writing-prompts` and pick verb-form names by turning repeated prose mandates into workflow steps, advertise the advisory asks it already owns, and drop an activation line that can't pass.

## Problem

- **Symptom:** `writing-prompts` is skipped in 2 of 3 `build-commit-message-skill` samples and in `db-migrate-internals-trap`, despite the REQUIRED SUB-SKILL marker.
- **Symptom:** skills get noun names (`commit-message`) in 2 of 3 samples. The verb/gerund rule lives only in `references/skill-conventions.md`.
- **Symptom:** advisory asks ("do I need a skill or CLAUDE.md?", "what should I name this skill?") route 0/4 and 3/4. The body owns both; the description names neither.
- **Symptom:** `react-conventions-followthrough` fails its activation line by design: the skill correctly declines to build a skill for project conventions.
- **Why it stayed hidden:** the mandate is restated five times in capitals. Repetition reads as emphasis, not as a step with a place in the sequence.
- **Scope:** `skills/writing-agent-skills/SKILL.md` and `evals/writing-agent-skills/`.
- **Constraint:** general wording only. No text naming an eval's scenario.

## Solution

```
SKILL.md  REQUIRED SUB-SKILL + §5 restatements  ──►  one step: "Write SKILL.md, then invoke writing-prompts on it"
SKILL.md  §2 naming sentence                    ──►  "verb or gerund (`processing-pdfs`), never a noun (`pdf-utils`)"
description                                     +    "deciding whether something should be a skill, naming one"
evals/.../react-conventions-followthrough       −    activation line
```

The rule moves to the step where it happens, stated once with its reason.

## User Stories

1. As a skill author, I want **every description and body polished by writing-prompts**, so it ships tight.
2. As a skill author, I want **names predictable from the verb**, so they match the conventions.
3. As a user, I want **"skill or CLAUDE.md?" and naming questions to reach this skill**, so they get the "When NOT to create a skill" answer.

## Implementation Decisions

```
§1 Capture intent ──► §2 Scaffold (verb/gerund name) ──► §3–4 evals + RED ──► §5 Write SKILL.md ──► invoke writing-prompts ──► re-Write ──► §6 grade
```

- **One mandate, at the point of use.** Delete the REQUIRED SUB-SKILL paragraph and the §5 restatements; keep one numbered sub-step in §5 with its reason (the polish edits a saved file; skipping it inflates trigger surface).
  - Keep the "write before invoking" ordering; it prevents stranded writes.
  - "When NOT to create a skill" keeps one line pointing alternative docs at `writing-prompts`.
- **Naming rule inline in §2.** One sentence with a positive and a negative example.
- **Description gains the advisory clause.** General: deciding whether work belongs in a skill, and naming one. Existing negatives stay.
- **Drop the untestable activation line.** Its substantive assertions already discriminate.
- **Net body length goes down.**

## Testing Plan

### Behavior
- **Build scenarios invoke or recommend writing-prompts** in every trial sample.
- **Generated skill names are verb or gerund form.**
- **No output eval regresses** vs the recorded trial column.
### Interface
- **Advisory asks route here** and not to writing-prompts; all existing routing queries hold.
### Logic
- N/A — no scripts change.

## Documentation Plan

- **`docs/evals/writing-agent-skills.md`**: re-record; update the notes that describe the fixed gaps.

## Out of Scope

- `improve-changelog-skill` length-cut variance (77% → 94% trial); not a skill defect yet.
- Reference file rewrites beyond what the body changes require.

## References

- `docs/evals/writing-agent-skills.md` — per-scenario misses and routing notes.
- `skills/writing-agent-skills/references/skill-conventions.md:26` — the naming rule.

## Verification

- `make evals:lint` — clean.
- `make evals SKILL=writing-agent-skills EVAL_ARGS="--count 3"` — writing-prompts line and name line pass in every trial sample; routing ≥ 14/15.
- `make test && make lint` — green.
