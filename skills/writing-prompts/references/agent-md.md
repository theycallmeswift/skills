# Writing AGENTS.md and CLAUDE.md

Additional rules for repo-level agent guidance files — `AGENTS.md` (the cross-tool open standard, read by Codex, Cursor, Aider, Jules, Zed) and `CLAUDE.md` (Claude Code's equivalent). Both serve the same purpose: tell an agent how to work inside *this* repo. Loaded once at session start, in every turn's context for the rest of the session — so every line competes with the user's actual ask.

## Target length

**Under 100 lines is the target. 200 is the hard ceiling.**

The math: frontier models reliably follow ~150–200 instructions before drift sets in. The harness's own system prompt spends some of that budget before this file loads. Skills, MCP tool descriptions, and the user's prompt compete for the rest. Every line added is a line something else loses.

If the file is past 200, it's not thorough — it's crowding out the request. Move detail to `docs/` and link.

## It's a role definition, not a prompt

The agent reads this once and weighs it against everything that follows. Two consequences:

- **It's a routing layer, not an encyclopedia.** Point at deeper docs for details only needed sometimes.
- **Every surprising agent behavior is a file problem.** Either following a rule the author forgot writing, or filling a gap the author didn't cover.

## Behavioral, not adjectival

"Be thoughtful" is an adjective. The agent has no way to ground it. Rewrite as a behavior with a concrete trigger:

| Adjective | Behavior |
|-----------|----------|
| "Be thorough" | "Before claiming work is complete, run it and show output." |
| "Be careful with important actions" | "Confirm before destructive commands; otherwise try the reversible path first." |
| "Be curious" | "When the request is ambiguous, ask one clarifying question before drafting." |

## Tiered autonomy

All-or-nothing guidance produces an agent that either asks for everything or barrels through irreversible changes. Split into tiers:

- **Freely reversible** — just do it. Edits, local commands, scratch files.
- **Consequential** — state intent and proceed. Pushes to a branch, new dependencies.
- **Irreversible** — always confirm first. Force-push, drop tables, delete data, post to shared channels.

Naming the tiers gives the agent a place to put novel situations.

## Sections that earn their place

Not every project needs every section, with one exception — **every session-level doc gets a `## References` section as a top-level heading**, even when there is nothing yet to link (in which case the section explicitly says so). The rest are optional; when they do pull weight, they usually look like one of these:

- **Working With Me** — who the author is, how they think, the calibration. Behavioral ("ask once before refactoring", "show output before claiming done"), not vibes ("be friendly").
- **Decision Principles** — three to five tiebreakers, bolded cue phrases. *"Test before claim", "Smallest viable change", "Confirm before irreversible."* If a paragraph keeps explaining a category of decisions, the principle is what's underneath.
- **Conventions** — specific non-negotiables. Each carries a `Why:` line when the reason isn't obvious. Why-lines turn rules into principles the agent can extend to unseen cases.
- **Tool access / environment** — when defaults are swapped (WebFetch disabled, a specific MCP server replaces it, the test runner isn't standard). Without this, the agent reaches for defaults that may be wrong and fails silently.
- **Project structure** — one-liners per directory, not inline encyclopedia. Each entry tells the agent where to look when relevant.
- **References** — on-demand docs. **Required for any session-level doc that fits in under 200 lines** — the alternative is inlining encyclopedic detail that crowds out the request. Each pointer says *when* to load, not just *what*. *"`docs/voice.md` — load when writing prose."* If the topic genuinely has no deeper detail to point at, say so explicitly under the heading rather than omitting it.

## Template

Canonical scaffold: [`../assets/agent-md-template.md`](../assets/agent-md-template.md).

Copy that file to the target path, then fill the `{{variables}}` and delete the
`<!-- comments -->`. Delete entire sections only when the comment marks them
optional. The template is the source of truth for structure; this reference is
the source of truth for *why* each section exists.

Do not hand-write the structure from memory — copy the asset.

## Show, don't tell

Concrete behaviors don't leak interpretation. Adjectives do.

```
# Wrong
Be careful with destructive commands.

# Right
Never run `rm -rf`, `git reset --hard`, force-push, or drop-table without
explicit confirmation. For other consequential commands (publishing, pushing),
state intent in one sentence and proceed.
```

## Pruning

Every rule has a cost — context, conflict, maintenance. Treat the file as a living document but not an ever-growing one.

- **Every surprise is a gap.** Either following a forgotten rule or filling an uncovered one.
- **Every correction is a candidate.** A mid-session correction that would apply next session too belongs in the file.
- **Every addition earns its place or comes out.** Revisit when the file approaches 100 lines: has this rule fired? Did it help? If not, cut.
- **Move, don't delete, when in doubt.** Useful-but-too-specific rules go to `docs/` with a pointer.

The agent gets better as instructions get more precise, not as they get more numerous.

## Common mistakes

- **The 400-line file.** Past 200 lines, the file is crowding out the request itself. Cut.
- **Adjectives without behaviors.** *"Be thoughtful."* / *"Be careful."* Rewrite as concrete behaviors with triggers.
- **Long lists of edge cases.** Enumerating every situation creates conflicts. State the principle and trust the model to generalize.
- **Personality lines that aren't grounded.** *"Be curious!"* Curious how? Asks clarifying questions? Explores related code? Suggests alternatives? Write the behavior.
- **Inline encyclopedia.** Detailed tool docs, deployment runbooks, exhaustive style guides inline. Move to `docs/` and link.
- **No tiered autonomy.** Without explicit tiers, the agent either asks for everything or asks for nothing.
- **Rules without reasons.** The `Why:` line is what lets the agent apply the rule to unseen cases.
- **Using the file as a linter.** Code style (2 spaces, prefer const, single quotes) belongs in a formatter — Ruff, Prettier, gofmt — wired into a hook. Models pick up style from surrounding code anyway. Reserve this file for things a linter can't catch.

## The two-file pattern

When more than one agent works in the same repo, `AGENTS.md` is the cross-tool standard and the canonical file; `CLAUDE.md` either symlinks to it (zero drift) or imports it (`@AGENTS.md` plus Claude-only additions below). Per the AGENTS.md spec, the nearest file to the work being done wins conflicts, so subdirectory-scoped guidance works as expected.
