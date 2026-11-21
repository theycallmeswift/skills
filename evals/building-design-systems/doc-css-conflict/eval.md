---
---

## Prompt

Turn our brand doc and CSS into an agent-readable design system under docs/design.

## Assertions

- [ ] Skill `building-design-systems` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] No file under ./docs/design/ gives `#7C3AED` as the accent colour's value
- [ ] Either the accent token under ./docs/design/ is `#6D28D9`, or no accent value is set and the final message asks me which value to use
- [ ] The final message names the conflict between `#7C3AED` in ./docs/brand.md and `#6D28D9` in ./src/theme.css
