# Test row

One test per row: a status dot, then the test name.

## Size

Rows have a fixed height of 44px. Long test names truncate with an ellipsis.

## States

| State | Treatment |
|---|---|
| pass | `--pass` dot |
| fail | `--fail` dot |
| queued | `--muted` text and a 1px dashed `--muted` outline |
| selected | 2px ring in `--stroke-ring`, inset |

Do: keep the dot before the name. Don't: colour the name by state.
