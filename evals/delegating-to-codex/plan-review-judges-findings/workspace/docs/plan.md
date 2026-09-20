# Plan: pagination helpers

Run tests with `python3 -m unittest -q`.

## Task 3 — Add `page_count(total, size)`

- **Implementer:** Codex (done, committed on this branch)
- **Reviewers:** Claude first, then Codex (the implementer's family never reviews first)
- **Named risks:**
  - A partial last page must count as a page (`page_count(21, 10) == 3`).
  - `size <= 0` must raise `ValueError`.
- **Done when:** both reviews are handled, fixes are committed, and the suite passes.
