# Page critique: <page or flow name>, <product>

You are one of several independent reviewers critiquing a page of a product. Judge it for the people below, find what is wrong, and give fixes exact enough to apply without a follow-up question. Assume there are problems; "looks good" is not a finding.

## Who this serves

<Who uses this page, in what context (devices, screen sizes, how often, under what pressure), and the job it does for them: what they come to find, decide or do.>

## Settled decisions (do not argue these)

The owner has already decided the following. Treat each as fixed: don't recommend reversing, softening or "reconsidering" one, and don't score a criterion down because of one.

- <decision, with the reason if known>
- <decision>

## Design system

Grade brand fit against the design system as it stands after its own critique pass, not against your taste. The tokens are in the attached text file. These changes from that pass are already applied; don't re-litigate token values, flag where the page departs from them:

- <applied design-system change, e.g. `--text-muted` now #9BA1AB>
- <or "No design-system pass was run; grade brand fit against the attached tokens.">

## What you are looking at

- Each image is preceded by a line `[frame] (theme): description`. Tall pages are split into parts (`1/3`, `2/3`, ...) in reading order.
- Screenshots carry a margin grid: columns A–H across the top and bottom, rows 1–8 down the sides. Cite the cell of every issue, e.g. `C4`; for an element spanning cells, cite the top-left one.
- **Ignore page artifacts:** the grid lines, the margin and its labels, captions, and any annotations or review notes added around the design ("Recommended", arrows, callouts). They are not part of the design; never critique them.
- Read exact values (hex, px, weights) from the tokens file, not from pixels: screenshots shift colours.

## Criteria

Score each 1–5 (5 = nothing to fix). Weights sum to 100.

| Criterion | Weight | A 5 looks like |
|---|---|---|
| Task clarity and hierarchy | 25 | The main job is obvious in five seconds; the eye lands on what matters first |
| Information density | 15 | Everything needed is there, nothing competes for attention without earning it |
| Accessibility | 20 | Text and controls pass WCAG 2.2 AA; targets are large enough; meaning never rests on colour alone |
| Brand fit | 15 | Uses the design system's tokens and components; no off-system values |
| States and edge cases | 15 | Empty, loading, error, long text and large numbers are designed, not left to chance |
| Polish | 10 | Alignment, spacing rhythm and type are consistent across the page |

<Adjust weights only if the owner's goal shifts them; keep the sum at 100.>

## Issues

- At most 15, most important first.
- Each names the frame, the grid cell, the element, the problem, and why it matters to the people above.
- Each gives an exact fix: a hex, px value or token, e.g. `table row height 40px → 32px` or `status pill text → --text-on-accent #0B0D12`. "Improve hierarchy" or "consider more spacing" is not a fix.
- Every contrast claim names the foreground hex, background hex and ratio, computed with the WCAG 2.2 formula from the token values. A proposed colour must pass too: check its ratio before proposing it.
- Severity: `high` (blocks the task or fails WCAG AA), `medium` (slows or confuses), `low` (polish).
- Confidence: how sure you are the problem is real, not a misreading of the image.
- Evidence: what in the image or tokens shows it.

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
