# <Product> design system

<One sentence: what the product is and who uses the UI.> Read this file before changing any UI; it links to everything else.

## Files

- `foundations/tokens.json`: every token, with a `usage` string naming its one job. The source of truth.
- `foundations/tokens.css`: generated from `tokens.json`. Never edit it by hand.
- `foundations/contrast.md`: the allowed colour pairings and their ratios. Generated. Use only pairings listed there.
- `components/<name>.md`: one spec per component.
- `brand/logos.md`: where the logo files live and how variants are rendered.

## Rules

<Brand-wide rules only, each stated once. A rule about one component goes in its spec; a rule about one token goes in its `usage`; ratios live in `contrast.md`. Examples:>

- Use role tokens (`--bg`, `--fg`, `--accent`, …) in UI code, never `--brand-*` or raw hex.
- Use only the spacing, type and radius steps in `tokens.json`.
- Every interactive element shows a focus ring: <width> `--accent`, <offset> offset.
- <Settled decision from the user, verbatim in effect: e.g. "Status labels are uppercase.">

## Themes

`<default theme>` is the default, on `:root`. `<other theme>` applies with `data-theme="<other theme>"` on `<html>`.

## Fonts

Self-hosted woff2 files listed in `tokens.json` under `type.fonts`. <If the page has a strict CSP:> The app serves `default-src 'self'`: no third-party font or CSS URLs, no `data:` URLs, no inline `style=""`.

## Open

<Decisions not yet made. Their tokens are not in the shipped files.>
