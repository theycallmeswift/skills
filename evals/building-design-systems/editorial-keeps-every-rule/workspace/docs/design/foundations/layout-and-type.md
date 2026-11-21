# Layout and type

## Spacing

Pilot uses a 4px grid. We considered an 8px grid, but dense tables needed the half-steps. The allowed steps are 4px, 8px, 12px, 16px, 24px and 32px. If you find yourself wanting 20px, pick 16px or 24px instead; the constraint is the point.

## Type

We use a small scale so the hierarchy stays obvious. The sizes are 13px for captions and table metadata, 15px for body text, 18px for section headings and 24px for page titles. Nothing should be smaller than 13px, because people read Pilot on laptop screens at the end of long days.

## Corners

Corners are subtle. Inputs, buttons and badges use a 6px radius. Cards use 10px. Pills, such as filter chips, use 999px so they are fully rounded at any height.

## Motion

Transitions are short, 120ms, because on-call engineers don't want to wait for animations. Use them only for hover and focus changes.
