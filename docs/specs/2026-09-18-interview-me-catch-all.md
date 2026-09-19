**TL;DR** — Stop interview-me from opening a new scoped decision once the stop gate is met: state in §3 that grilling ends at the gate and that the catch-all is prose, so the visual habit no longer beats the §5 carve-out.

## Problem

- **Symptom:** `catch-all-pose` is 60% on both arms. After the goal resolves, 3 of 4 samples ask one more scoped question with an options table instead of the single open catch-all.
- **Why it stayed hidden:** the suite pass got it right (5/5); only the 3× re-sample exposed it.
- **Root cause:** §3 says every decision ships a visual and to walk the tree; the stop and prose-catch-all rules live only in §5. When unsure whether the tree is exhausted, the agent keeps grilling.
- **Scope:** `skills/interview-me/SKILL.md` §3 and §5.
- **Constraint:** general wording; the fix covers modes B and C.

## Solution

```
§3  + "Grill only branches the stop condition needs. Once its gate is met, stop asking decisions (§5)."
§5  catch-all paragraph: tighten; state it is prose and ends the turn
```

The stop rule appears where the grilling rule does.

## User Stories

1. As an interviewee, I want **the interview to wrap once my goal is resolved**, so I'm not grilled on adjacent branches.
2. As an interviewee, I want **one open catch-all in prose**, so I can add anything missed without choosing from options.

## Implementation Decisions

```
§3 grill ──► gate met? ──yes──► §5 Shared Understanding ──► one prose catch-all ──► empty? stop : §3
             └─no──► next branch (visual)
```

- **Gate check before each question.** One sentence in §3; no new section.
- **§5 gets shorter.** Merge the "exempt from §3" sentence into the catch-all definition.
- **Net body length does not grow.**

## Testing Plan

### Behavior
- **Goal resolved ⇒ one prose catch-all, no new decision**, in every trial sample.
- **No other interview-me scenario regresses.**
### Interface
- **Routing unchanged**: all 18 queries hold.
### Logic
- N/A — no scripts.

## Documentation Plan

- **`docs/evals/interview-me.md`**: re-record; replace the `catch-all-pose` soft-spot note.

## Out of Scope

- The high baselines from continuation-style scenarios. An eval design question, not a skill gap.

## References

- `docs/evals/interview-me.md` — `catch-all-pose` note.
- `skills/interview-me/SKILL.md` — §3 visual rule, §5 catch-all.

## Verification

- `make evals SKILL=interview-me EVAL_ARGS="-k catch-all --count 3"` — `catch-all-pose` passes in all samples on trial.
- `make evals SKILL=interview-me` — no scenario below its recorded trial rate.
- `make test && make lint` — green.
