---
---

## Prompt

Set up a design system for Lumen that coding agents can build UI from, under docs/design.

## Assertions

- [ ] Skill `building-design-systems` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] ./docs/design/foundations/tokens.json exists
- [ ] ./docs/design/foundations/tokens.json contains the logo colour `#EF8354` (any letter case)
- [ ] ./docs/design/foundations/tokens.json contains the logo colour `#2B2D42` (any letter case)
- [ ] Every colour that ./docs/design/foundations/tokens.json presents as a brand colour appears in ./assets/logo/, ./assets/logo/render.sh or ./web/src/styles.css
- [ ] ./docs/design/foundations/tokens.json names the font family "IBM Plex Sans", the font the dashboard already uses
- [ ] ./docs/design/foundations/tokens.css exists
- [ ] ./AGENTS.md contains the path `docs/design/README.md`
- [ ] No file under ./docs/design/ has the `.svg` extension
