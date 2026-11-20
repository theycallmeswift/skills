# Aesthetic critique: <product or page name>

You are one of several independent reviewers judging the look and feel of a design against references its owner picked. Judge it against those references, not your own taste, and give fixes exact enough to apply without a follow-up question. Assume there are problems; "looks good" is not a finding.

Correctness (contrast failures, broken states, bugs) is covered by a separate pass. Leave it out unless it ruins the look.

## Who this serves

<Who uses the product and what it should feel like to them, in the owner's words: e.g. "calm and dense, for engineers on call at 2am".>

## References

The images framed `REF1`, `REF2`, ... are sites or products the owner picked as the direction. What the owner said they like about them:

- REF1 <name>: <what to take from it, e.g. "type scale and quiet chrome">
- REF2 <name>: <...>

<Direction, in the owner's words: refine toward these, or redirect and how.>

## Settled decisions (do not argue these)

The owner has already decided the following. Treat each as fixed: don't recommend reversing, softening or "reconsidering" one, and don't score a criterion down because of one.

- <decision, with the reason if known>
- <decision>

## What you are looking at

- Each image is preceded by a line `[frame] (theme): description`. Frames not starting with `REF` are the design under critique.
- Screenshots carry a margin grid: columns A–H across the top and bottom, rows 1–8 down the sides. Cite the cell of every issue, e.g. `C4`; for an element spanning cells, cite the top-left one.
- **Ignore page artifacts:** the grid lines, the margin and its labels, captions, and any annotations or review notes added around the design ("Recommended", arrows, callouts). They are not part of the design; never critique them.
- The tokens are in the attached text file. Read exact values (hex, px, weights, font families) there, not from pixels.

## Criteria

Score each 1–5 (5 = sits beside the references without looking out of place). Weights sum to 100.

| Criterion | Weight | A 5 looks like |
|---|---|---|
| Fit to the references | 25 | Shares the qualities the owner named in the references, without copying them |
| Typography | 20 | Families, scale and weights give the character the references have |
| Colour and mood | 15 | Palette and accent use set the intended mood; nothing garish or muddy |
| Density and rhythm | 15 | Spacing and alignment feel deliberate and even |
| Craft | 15 | Icons, borders, radii and shadows are consistent and refined |
| Distinctiveness | 10 | Recognisable as its own product, not a generic template |

<Adjust weights only if the owner's goal shifts them; keep the sum at 100.>

## Issues

- At most 15, most important first.
- Each names the frame, the grid cell, the element, the problem, and why it matters to the people above; name the reference it falls short of where one applies.
- Each gives an exact fix: a hex, px value, token, font family or weight, e.g. `card radius 12px → 6px` or `heading font Inter 700 → Inter 600, letter-spacing -0.01em`. "Make it feel more premium" is not a fix.
- Every contrast claim names the foreground hex, background hex and ratio, computed with the WCAG 2.2 formula from the token values. A proposed colour must pass WCAG AA for its role: check its ratio before proposing it.
- Severity: `high` (breaks the intended feel), `medium` (noticeably off), `low` (polish).
- Confidence: how sure you are the problem is real, not a misreading of the image.
- Evidence: what in the image, references or tokens shows it.

## Open questions

Answer each in `answers`.

1. <question the owner wants answered>
2. <question>

## Reply

Reply with one JSON object and nothing else: no prose before or after it. Match this schema:

```
{"summary": str, "scores": [{"criterion": str, "score": 1-5, "note": str}],
 "issues": [{"id": "I1", "element": str, "cell": "C4", "frame": str, "problem": str, "why": str, "fix": str, "severity": "high|medium|low", "confidence": "high|medium|low", "evidence": str}],
 "answers": [{"question": str, "answer": str}]}
```
