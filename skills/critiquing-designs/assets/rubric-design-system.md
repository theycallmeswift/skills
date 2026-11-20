# Design-system critique: <product or system name>

You are one of several independent reviewers critiquing a design system. Judge it for the people below, find what is wrong, and give fixes exact enough to apply without a follow-up question. Assume there are problems; "looks good" is not a finding.

## Who this serves

<Who uses the product built on this system, in what context (devices, light or dark rooms, hours a day), and what job the UI does for them. Who builds with the system: one team, many teams, outside developers.>

## Settled decisions (do not argue these)

The owner has already decided the following. Treat each as fixed: don't recommend reversing, softening or "reconsidering" one, and don't score a criterion down because of one.

- <decision, with the reason if known>
- <decision>

## What you are looking at

- Each image is preceded by a line `[frame] (theme): description`.
- Screenshots carry a margin grid: columns A–H across the top and bottom, rows 1–8 down the sides. Cite the cell of every issue, e.g. `C4`; for an element spanning cells, cite the top-left one.
- **Ignore page artifacts:** the grid lines, the margin and its labels, captions, and any annotations or review notes added around the design ("Recommended", arrows, callouts). They are not part of the design; never critique them.
- The tokens are in the attached text file. Read exact values (hex, px, weights) there, not from pixels: screenshots shift colours.

## Criteria

Score each 1–5 (5 = nothing to fix). Weights sum to 100.

| Criterion | Weight | A 5 looks like |
|---|---|---|
| Contrast and accessibility | 25 | Every text and icon role pair passes WCAG 2.2 AA in every theme; focus is always visible |
| Colour system | 15 | Semantic roles (surface, text, border, accent, status) cover every use; no near-duplicate values |
| Typography | 15 | A clear scale with distinct steps; weights and line heights consistent per role |
| Spacing and sizing | 15 | One scale used everywhere; no off-scale values |
| Component states | 15 | Hover, focus, active, disabled, error and loading exist and are distinguishable |
| Theme parity | 10 | Light and dark carry the same hierarchy and meaning |
| Naming | 5 | Token names say the role, not the value |

<Adjust weights only if the owner's goal shifts them; keep the sum at 100.>

## Issues

- At most 15, most important first.
- Each names the frame, the grid cell, the element, the problem, and why it matters to the people above.
- Each gives an exact fix: a hex, px value or token, e.g. `--text-muted #8A8F98 → #9BA1AB` or `gap 12px → 16px`. "Improve contrast" or "consider more spacing" is not a fix.
- Every contrast claim names the foreground hex, background hex and ratio, computed with the WCAG 2.2 formula from the token values. A proposed colour must pass too: check its ratio before proposing it.
- Severity: `high` (blocks a task or fails WCAG AA), `medium` (slows or confuses), `low` (polish).
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
