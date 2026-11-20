---
name: building-design-systems
description: "Use when the user wants a design system, design tokens or component specs built from their repo's brand, or existing design docs made usable by coding agents: \"set up a design system agents can build UI from\", \"build a design system for this repo\", \"turn our brand assets into tokens\", \"make our design docs machine-readable\", \"our design docs drifted from the CSS\", \"fix the contrast failures in our tokens\", \"export the design system to docs/design\". Use it whenever the output is design-system files an agent will read, even if the user doesn't say \"agents\". Don't use to critique a design (critiquing-designs), to build a page or component from an existing system, or to create a new logo or brand."
---

# Building design systems

Build a design system a coding agent can build UI from, out of the brand the repo already has. Agents copy what they read: an invented colour, a rule stated three ways, a hand-computed ratio or an example that breaks the page's CSP all end up in shipped UI. Every value traces to a source, every rule lives in one place, every ratio comes from a script.

## Modes

- **Build:** no design system yet. Run steps 1–8.
- **Make existing docs agent-readable:** steps 1, 5, 6, 8; step 2 only to move values into `tokens.json`.
- **Fix contrast:** steps 4 and 8.
- **Reconcile docs with CSS:** step 8 first, then fix what it reports.

## Scripts

In this skill's `scripts/` directory; stdlib only. Run them with `python3` from the project root, passing paths. If `python3` is missing, install it rather than computing by hand:

- `tokens_to_css.py docs/design/foundations/tokens.json` writes `tokens.css` beside it.
- `contrast_table.py docs/design/foundations/tokens.json` writes `contrast.md` beside it; exits 1 if any pair misses its target.
- `check_refs.py docs/design --css <each shipped CSS file>` lists token names and hex values that docs and CSS disagree on; exits 1 on any.

Templates are in `assets/`: `tokens.example.json` (the token format the scripts read), `readme-template.md`, `component-template.md`.

## 1. Inventory brand sources

Read, before writing anything: logo files and the script that renders them, CSS and theme files, README art, social images, existing UI, existing design docs, and the user's earlier UI decisions in this conversation and the repo. Record each brand value's source file (`source` in `tokens.json`) and the user's decisions as a settled list.

No source for a brand colour, font or logo: ask. Never invent one.

## 2. Tokens by role

Copy the shape of `assets/tokens.example.json` to `docs/design/foundations/tokens.json`:

- `brand`: the fixed palette from step 1, each with `value`, `source`, `usage`. Separate from UI roles.
- `color`: UI roles (`bg`, `surface`, `fg`, `muted`, `accent`, `on-accent`, `danger`, `status-*`), a value per theme. A role may reference a brand colour as `{brand.<name>}`.
- One `space` scale, one `type.scale`, one `radius` set. `type.fonts` lists each font's family, weight, file and licence.
- Every token has a `usage` string naming its one job. Name tokens by role, not by look (`muted`, not `grey-2`). Two tokens with the same job are one token.
- `pairings`: every foreground/background combination UI may use, `kind` `text` or `mark`.
- A token the user hasn't decided stays out of the shipped files; list it under Open in the README.

Run `tokens_to_css.py`; never edit `tokens.css` by hand.

## 3. Components

One file per component, `docs/design/components/<name>.md`, from `assets/component-template.md`: Provide (exact markup and classes), a state table (default, hover, focus, selected, disabled, empty, loading, as they apply), sizes and tokens, do/don't rules. Every value is a token name. No rule lives only in a picture.

## 4. Contrast

Run `contrast_table.py`. Targets sit above the WCAG floor so rounding can't tip a pair: 4.6:1 for text, 3.2:1 for marks. They replace any lower targets an older table states. Hand-computed ratios and stale tables don't count: 4.599 rounds to 4.60 and still fails.

Fix a failure by changing a UI role's value in `tokens.json`, never a `brand` value. When a role references a brand colour (`"dark": "{brand.haze}"`), replace the reference with a new hex for that role; don't edit the brand entry, since the logo still uses it. For a label on a brand fill, change the label role (`on-accent`) before the fill.

Rerun `tokens_to_css.py` and `contrast_table.py` until it exits 0. Never hand-edit `contrast.md`. Name every failure you fixed in the final message, with old and new ratios.

## 5. Editorial pass for agents

Each rule is stated once, in one place:

| Rule about | Lives in |
|---|---|
| The whole system | `README.md` |
| One component | `components/<name>.md` |
| One token | its `usage` string |
| Contrast targets and ratios | `contrast.md` only |

Elsewhere, name the token or link the file; never restate the value. Cut rationale, history and repetition, aiming for about 40% shorter. Add no new commentary files.

The pass changes wording, not values: report a failing pair or a value that looks wrong, and change it only if the user asks.

Before cutting, list every normative value and rule (hex codes, sizes, durations, thresholds, state names, ARIA attributes). After, confirm each exists in exactly one place; restore any that was lost.

**REQUIRED SUB-SKILL:** use `writing-prompts` for the wording, after the files are written.

## 6. Export

Kebab-case paths under `docs/design/`:

```
docs/design/README.md                  from assets/readme-template.md
docs/design/foundations/tokens.json    source of truth
docs/design/foundations/tokens.css     generated
docs/design/foundations/contrast.md    generated
docs/design/components/<name>.md
docs/design/brand/logos.md             where each logo file lives, how variants render
```

## 7. Point the context file at it

Add this line to the References section of `AGENTS.md` (or `CLAUDE.md` when that is the real file; create the section if missing):

```
- `docs/design/README.md`: the design system; read it before changing any UI.
```

## 8. Verify

Regenerate `tokens.css` and `contrast.md`, then run `check_refs.py` against every CSS file that ships. It catches names and hex values only. Then read each component's state table, sizes and layout rules against the CSS by hand: a state the CSS never draws, "fixed" where the CSS says `min-height`, or a layout that exists only in a preview file is a mismatch too.

Final message: what was sourced (and from where), what you asked or assumed, every conflict found and how it was resolved, and what is still open.

## Gotchas

- **Docs and CSS disagree.** Resolve toward the code, since it ships, and say so. Where the code looks wrong (a documented state the CSS never draws, a layout only in a preview), keep the docs true to the CSS and ask the user whether the CSS should change. Never pick the doc silently.
- **Prior decisions win.** The user's earlier UI decisions override rules from critiques, best practice or other docs. Keep the decision as a rule, drop the conflicting one, and name the conflict in the final message.
- **Strict CSP.** Check the app's Content-Security-Policy. Under `default-src 'self'`, third-party fonts and CSS, `data:` URLs and inline styles are blocked. Self-host woff2 files listed in `type.fonts` (`tokens_to_css.py` refuses remote and `data:` fonts) and tell the user if the app currently loads a blocked font. Examples follow every rule: no `style=""`, no `data:` masks, no Google Fonts imports in markup or CSS under `docs/design/`, since agents copy examples.
- **Single-source the logos.** `brand/logos.md` links the files where they live; never copy them into `docs/design/`. Variants come from the repo's render script.
- **Wordmarks are outlined paths, never live text.** Live text falls back to another face wherever the font isn't loaded.
