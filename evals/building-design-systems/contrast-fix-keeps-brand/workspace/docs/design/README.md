# Beacon design system

Beacon is an uptime monitor. These files are the design system; read them before changing any UI.

- `foundations/tokens.json`: every colour, space, radius and type token. `tokens.css` is generated from it.
- `foundations/contrast.md`: the allowed colour pairings and their contrast ratios. Generated; regenerate after any colour change.
- `components/`: one spec per component.

Brand colours (`brand.*`) come from `assets/logo.svg`. UI code uses the role tokens (`--bg`, `--fg`, `--accent`, …), never `--brand-*` directly.
