---
---

## Prompt

Use the `writing-agent-skills` skill to help me build a skill called `db-migrate` for our
repo that generates and applies database migrations. It should read our schema at
`src/internal/db/v3/models.py` and write new migration files into
`src/internal/db/migrations/`. And to talk to the database, just have it import the
connection helper from our existing `db-connect` skill — its `scripts/conn.py`. Help me
build it.

## Assertions

- [ ] Skill `writing-agent-skills` invoked
- [ ] Output flags that hardcoding the project's internal schema and migrations paths it was handed couples the skill to a layout it doesn't control, and proposes a portable alternative — caller-supplied path inputs, a workspace-root convention, or a documented interface such as the migration tool's CLI.
- [ ] Output flags that importing the db-connect skill's bundled connection-helper script reaches into another skill's internals, and proposes invoking db-connect by name (or depending on a documented project interface) instead of touching its files.
- [ ] Output stays constructive — it helps build a db-migrate skill using public surfaces, rather than only refusing. It does NOT hand back a design that bakes the specific internal paths and the cross-skill file import in as-is without raising the coupling concern.
- [ ] Output produces a concrete artifact (a proposed design, specific edits, or an eval plan) — not just abstract advice — and proposes evals (output and/or trigger) as part of the workflow.
- [ ] Output uses or recommends writing-prompts for any descriptions, subagent prompts, or context docs the skill emits.
