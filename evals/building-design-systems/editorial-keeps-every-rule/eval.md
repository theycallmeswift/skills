---
---

## Prompt

Our design docs in ./docs/design were written for human designers: long, full of rationale, and the same rules repeated in several files. Coding agents keep misreading them. Make them agent-readable.

## Assertions

- [ ] Skill `building-design-systems` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The hand-written Markdown files under ./docs/design/ total at most 845 words (the originals total 1,207); a generated contrast table doesn't count
- [ ] All twelve colour values survive somewhere under ./docs/design/, each still tied to its role and theme: `#0F172A` dark bg, `#FFFFFF` light bg, `#1E293B` dark surface, `#F1F5F9` light surface, `#E2E8F0` dark text, `#111827` light text, `#94A3B8` dark muted, `#475569` light muted, `#2563EB` accent, `#1D4ED8` accent hover, `#DC2626` danger, `#16A34A` success
- [ ] The spacing steps 4, 8, 12, 16, 24 and 32px and the type sizes 13, 15, 18 and 24px (with 13px as the minimum) survive under ./docs/design/
- [ ] The radii (6px for inputs, buttons and badges; 10px for cards; 999px for pills) and the 120ms transition survive under ./docs/design/
- [ ] The button heights (36px default, 28px small), the 40px input height with its 1px border, and the 20px badge height with weight-600 text survive under ./docs/design/
- [ ] The focus ring (2px, accent colour, 3px offset), the 0.45 disabled opacity, `aria-busy="true"` on loading buttons and `aria-invalid="true"` on invalid inputs survive under ./docs/design/
- [ ] The contrast targets survive under ./docs/design/: 4.6:1 for text and 3.2:1 for non-text marks
- [ ] Each colour hex value appears in exactly one hand-written file under ./docs/design/ (a tokens.css generated from tokens.json doesn't count); any other file that needs the colour names its token instead
- [ ] The focus-ring specification (2px, 3px offset) is written out in exactly one file under ./docs/design/; any other file refers to it rather than restating it
- [ ] The contrast targets (4.6:1 and 3.2:1) are written out in exactly one file under ./docs/design/
