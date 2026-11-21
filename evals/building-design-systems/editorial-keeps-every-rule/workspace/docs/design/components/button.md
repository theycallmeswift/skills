# Button

Buttons are the most important interactive element in Pilot, so we spent a lot of time on them.

## Sizes

The default button is 36px tall. A small button, 28px tall, is for dense table rows. We don't offer a large size; in our experience large buttons in a dashboard look like marketing.

## Primary button

The primary button is filled with the accent blue, `#2563EB`, with white text. On hover it deepens to `#1D4ED8`. Hover, focus and pressed changes animate over 120ms. Corners use the standard 6px radius.

## States

Every button supports these states: default, hover, focus-visible, pressed, disabled and loading.

- **Focus-visible:** a 2px ring in `#2563EB` with a 3px offset. Never remove the focus ring; keyboard users depend on it.
- **Disabled:** the button drops to 0.45 opacity and ignores clicks. We chose 0.45 after testing because 0.5 looked too active in dark mode.
- **Loading:** the label is replaced by a spinner and the button sets `aria-busy="true"`, so screen readers announce that work is in progress. The button keeps its width so the layout doesn't jump.

## Destructive button

Destructive actions, such as rolling back a deploy, use `#DC2626` instead of the accent. Everything else about them matches the primary button.
