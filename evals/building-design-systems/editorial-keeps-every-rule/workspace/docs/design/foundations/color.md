# Colour

Colour in Pilot does a lot of work, so it deserves a careful explanation. We started from the observation that on-call engineers scan for two things: what is broken, and what they can do about it. Everything else should recede.

## Grounds

Dark mode is the default because most of our users work long shifts. The page background in dark mode is `#0F172A`, a deep slate that is easy on the eyes. Cards, panels and menus sit one step up on `#1E293B`. In light mode, which some teams prefer for daytime work, the page background is plain `#FFFFFF` and cards use `#F1F5F9`.

## Text

Body text is `#E2E8F0` in dark mode and `#111827` in light mode. Secondary text, such as timestamps, commit hashes and hints, uses a muted colour: `#94A3B8` in dark mode and `#475569` in light mode. We tested these carefully: every text pairing must reach at least 4.6:1. We chose 4.6:1 rather than the WCAG floor of 4.5:1 because rounding in design tools has burned us before.

## Accent

The accent is `#2563EB`. It means "you can act here": primary buttons, links and the focus ring. Its hover state is `#1D4ED8`. Please don't use the accent for decoration, because once it decorates it stops signalling.

## Status

Failed deploys and destructive actions use `#DC2626`. Healthy services and successful deploys use `#16A34A`. Status dots and icons are non-text marks, so they need 3.2:1 against their background rather than the text target.
