# Plan: slug length limits

Run tests with `python3 -m unittest -q`.

## Task 1 — Document slug rules (done)

## Task 2 — Add `max_length` to `slugify`

- **Implementer:** Codex
- **Change:** `slugify(text, max_length=None)`. When set, the slug is at most `max_length`
  characters.
- **Named risks:**
  - Truncation must never leave a trailing hyphen (`slugify("ab cd", 3)` is `"ab"`, not `"ab-"`).
  - `max_length=None` must keep today's behavior exactly.
- **Done when:** tests cover both risks and the suite passes.

## Task 3 — Use `max_length=60` in the CMS exporter
