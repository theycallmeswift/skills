# Badge

Badges show the status of a service or deploy at a glance.

## Shape

Badges are 20px tall with a 6px radius, the same corner as buttons and inputs. Text inside a badge is 13px, our smallest size, at weight 600 so it stays legible at that size. Horizontal padding is 8px.

## Colours

- **Healthy / succeeded:** `#16A34A`.
- **Failed:** `#DC2626`.
- **Neutral / unknown:** the muted text colour, `#94A3B8` in dark mode and `#475569` in light mode.

Badge text is text, so it needs 4.6:1 against the badge background. The dot inside a badge is a non-text mark and needs 3.2:1.

## Usage

Use a badge for state, never for counts; counts go in plain text. Don't put a badge inside a button.
