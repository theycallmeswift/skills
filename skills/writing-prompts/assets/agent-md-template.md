# {{project name}}

## Working With Me

I'm {{name}}, {{role}}. I value {{behavioral stance — e.g., "small reversible steps, working code over elegant code, asking before scaffolding"}}. Don't {{anti-pattern — e.g., "introduce new dependencies without asking"}}. If you can do it, do it. If unsure, try the reversible option and confirm before anything irreversible.

## Decision Principles

- **Test before claim.** Don't say "done" until the change runs and you've shown output.
- **Smallest viable change.** Prefer narrow edits over refactors. If 10 lines do the job, don't write 50.
- **Working over elegant.** A direct fix beats a clean abstraction not yet earned by the codebase.
- **Confirm before irreversible.** Anything that can't be undone gets a check-in first.

## Conventions

- Follow existing patterns in whatever file you're touching.
- Before claiming work is complete, run it and show output.
- {{Project-specific rule with a Why: line when non-obvious.}}
  Why: {{reason — turns the rule into a principle the agent can extend.}}

<!-- ## Tool Access — keep ONLY when defaults are swapped; otherwise delete this entire section. -->
<!-- - {{e.g., "All web fetches go through the brightdata MCP server. Built-in WebFetch is disabled."}} -->

## Project Structure

- `src/` — {{one-line purpose}}
- `tests/` — {{one-line purpose}}
- `docs/` — {{one-line purpose}}
- `tmp/` — Scratch space. Not tracked in git.

<!--
  Do NOT delete the `## References` section below. Empty-but-named is the
  artifact: it's the empty test file in TDD. The rationalization to refuse
  is "adds no value when there's nothing to link yet" — that thought is
  exactly the failure mode this placeholder exists to prevent. If the
  project genuinely has no deeper docs yet, keep the heading and replace
  the example bullets with the single fallback bullet below.
-->
## References

Load on demand, not at session start.

- `docs/voice.md` — Tone and prose conventions. Load when writing prose.
- `docs/architecture.md` — System layout. Load before touching cross-cutting code.
- `docs/runbooks/` — On-call procedures. Load when triaging incidents.

<!-- Fallback when no deeper docs exist yet — keep the heading, replace bullets above with this single line: -->
<!-- - No deeper docs yet — capture cross-cutting context here as the project grows. -->
