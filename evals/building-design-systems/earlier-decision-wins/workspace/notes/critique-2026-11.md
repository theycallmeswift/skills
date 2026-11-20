# Run table critique, 2026-11

Findings from the multi-model critique of the run table, ranked by how many models raised them.

1. **Status labels should use sentence case** (Passed, Failed, Queued). All-caps text is harder to read and reads as shouting. 5/6 models.
2. **Rows need more vertical padding**: 8px feels cramped; use 12px. 4/6 models.
3. **Rows have no visible focus state** for keyboard users. Add a 2px `--accent` outline on `:focus-visible`. 4/6 models.
4. **Muted text is close to the contrast floor** on `--surface`. Check it. 2/6 models.
