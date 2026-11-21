# Pilot design system

Welcome! This is the design system for Pilot, our deployment dashboard. We built it because, over the past year, the product grew a dozen slightly different blues, three button heights and no shared idea of what "muted" meant. The goal of this document set is to give everyone, designers and engineers alike, a shared vocabulary so the product feels like one thing.

## Our philosophy

We believe a good interface gets out of the way. Pilot is used by on-call engineers, often at night and often under stress, so we favour calm, high-contrast surfaces and a single accent colour that always means "you can act here". That accent is our blue, `#2563EB`, and we use it sparingly: primary buttons, links and focus. When the pointer is over it, it deepens to `#1D4ED8`, which gives a clear but quiet sign that something is interactive.

Because people spend long shifts in the dashboard, dark mode is the default. The dark background is `#0F172A` and cards sit on `#1E293B`. In light mode the background is `#FFFFFF` and cards sit on `#F1F5F9`. Body text is `#E2E8F0` in dark mode and `#111827` in light mode.

## Accessibility

Accessibility is not optional for us. Every text pairing must reach at least 4.6:1, slightly above the WCAG minimum of 4.5:1, so that rounding never tips us into failure. Non-text marks such as icons and status dots must reach 3.2:1. Focus must always be visible: we use a 2px ring in the accent blue with a 3px offset so it never touches the component's own border.

## Spacing and rhythm

We use a 4px base unit. The steps are 4px, 8px, 12px, 16px, 24px and 32px, and nothing else. Consistent spacing is what makes a dense dashboard feel ordered rather than cramped.

## Where to go next

- `foundations/color.md` for the full palette and why we chose it.
- `foundations/layout-and-type.md` for spacing, type and corners.
- `components/` for buttons, inputs and badges.
