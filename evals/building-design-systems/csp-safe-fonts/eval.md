---
---

## Prompt

Build docs/design for Tally: a tokens.json, a tokens.css generated from it, and specs for the button and badge components, so coding agents can build UI from it.

## Assertions

- [ ] Skill `building-design-systems` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] No file under ./docs/design/ contains `fonts.googleapis.com`
- [ ] The tokens.css under ./docs/design/ does not contain `data:`
- [ ] The tokens.css under ./docs/design/ contains an `@font-face` rule
- [ ] Every font file that the tokens.json under ./docs/design/ lists is a same-origin path to one of the `.woff2` files in ./web/static/fonts/ (such as `/static/fonts/Inter-Regular.woff2`), not a URL on another host
- [ ] No example markup in the button or badge specs under ./docs/design/ uses a `style="` attribute or a `data:` URL
- [ ] The final message says the app's Google Fonts import is blocked by its `default-src 'self'` Content-Security-Policy
