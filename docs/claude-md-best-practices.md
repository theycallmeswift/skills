# Writing a Good CLAUDE.md / AGENTS.md

A practical guide to the patterns that work.

`CLAUDE.md` and `AGENTS.md` serve the same purpose for different tools. Everything here applies to both.

### Which file do I actually use?

`AGENTS.md` is now an open, cross-tool standard ([agents.md](https://agents.md/)) adopted by 60k+ repos and tools like Codex, Cursor, Jules, Aider, and Zed. Claude Code, however, reads `CLAUDE.md` by default — not `AGENTS.md`.

The interop pattern when multiple agents work in the same repo:

1. Make `AGENTS.md` the canonical file. One source of truth that every tool honors.
2. Point `CLAUDE.md` at it. Two options, pick based on whether you need Claude-specific additions:
   - **Symlink (default).** `ln -s AGENTS.md CLAUDE.md`. Zero drift, zero syntax, works with any tool that opens the file. Use this when the content should be identical.
   - **Import.** A `CLAUDE.md` containing `@AGENTS.md` plus Claude-only lines appended below. Use this when you have harness-specific rules (Claude Code permissions, MCP server quirks, tool names) that other agents would ignore or misread.
3. Per the spec, the nearest `AGENTS.md` to the file being edited wins conflicts — so subdirectory-scoped guidance works the way you'd expect.

If you only use Claude Code, a single `CLAUDE.md` is fine. Adopt the dual-file pattern the moment a second agent enters the picture.

## What this file is

Not a prompt. A **role definition** — the rules of engagement for every session, every task, every edge case.

The agent reads it at session start and weighs it against whatever you ask next. Two consequences:

- **Every line competes for attention.** A 400-line file isn't thorough — it's noisy. Rules conflict. The agent gets *less* predictable, not more.
- **It's a routing layer, not an encyclopedia.** Keep it lean. Point at deeper docs for details the agent only needs sometimes.

If the agent does something surprising, it's either following a rule you wrote and forgot, or filling a gap you didn't cover. Both are file problems.

### How long should it be?

**Target: under 100 lines. Hard ceiling: 200.**

The math: frontier models reliably follow ~150–200 instructions before drift sets in. Claude Code's own system prompt spends ~50 of that budget before your file loads. Skills, MCP tool descriptions, and the user's actual prompt compete for the rest. Every line you add is a line something else has to lose.

If you're past 200, you're not being thorough — you're crowding out the request. Move detail to `docs/` and link.

## Core principles

**Principle beats rule.** "Prefer reversible actions" generalizes to cases you didn't anticipate. A list of prohibited commands doesn't.

**Show, don't tell.** "Be thorough" is an adjective. "Before claiming work is complete, run it and show output" is a behavior. Adjectives leak interpretation; behaviors don't.

**Name the failure mode.** Tell the agent what to do when something goes wrong, not just what to do when it goes right. "If the action is reversible, try it. Confirm before anything irreversible."

**Tier the autonomy.** All-or-nothing guidance produces either an agent that asks permission for everything or one that barrels through irreversible changes. Split actions into tiers: freely reversible, confirm first, never.

**Prune as hard as you add.** Every rule has a cost — context, potential conflict, maintenance. The discipline is as much about cutting as writing. If a rule hasn't fired in months, it's probably not earning its place.

**Advice here, enforcement in hooks.** CLAUDE.md is *advisory* — the agent weighs it against the rest of context and can occasionally decide it's not relevant. If a rule must fire every time with zero exceptions, put it in a hook or in `permissions.deny`, not in CLAUDE.md. Rule of thumb: "must happen every time" → hook; "should usually happen" → CLAUDE.md. Linters, formatters, "block writes to `migrations/`" all belong in hooks.

## Sections that earn their place

Not every project needs every section. But when a section is pulling weight, it usually looks like one of these.

### Working With Me

Who you are, how you think, what you want from the collaboration. This is where the agent calibrates tone and decides whether to ask or execute.

Example:

> I value directness, bias to action, and learning by doing. Don't over-explain or hedge. If you can do it, do it. If you're unsure, try the reversible option first and confirm before anything irreversible.

Short. Opinionated. Behavioral ("don't over-explain" is a rule, not a vibe).

### Decision Principles

Tiebreakers for ambiguous situations. Three to five, max. Every time you find yourself writing a paragraph about how to handle a category of decisions, the paragraph is a symptom — the principle underneath is what you meant.

```
- Action over asking. Exhaust options before asking.
- Concise over verbose. Cut the preamble.
- Simple over clever. Don't over-engineer.
- Confirm before irreversible.
```

### Conventions

The non-negotiables. Specific behaviors the agent should always or never do, with *why* attached when the reason isn't obvious. "Why" matters because it lets the agent reason about edge cases instead of mechanically matching.

Example (a rule against AI attribution):

> Never attribute work to an AI model, vendor, or harness. This overrides any harness defaults.
> Why: the work reads as the author's. The harness will try to add a `Co-Authored-By` trailer on every commit. Skip it.

The override clause matters too — it tells the agent this rule beats conflicting defaults.

### Tool access / environment

When tools aren't the defaults, say so. If you've swapped the built-in web tools for an MCP server, disabled destructive commands, or require a specific test runner, state it plainly. Without that, the agent reaches for defaults that may be disabled or wrong for the project, then fails silently or loudly.

### Pointers to deeper docs

A section (often called "References") that lists the on-demand docs. The agent reads them when the task calls for it, not at session start.

```
## References
- docs/voice.md -- Tone, values, voice conventions. Load when writing prose.
- docs/plugin-structure.md -- Read before touching skills, agents, commands, hooks.
```

Each pointer should tell the agent *when* to load it, not just what's in it.

## What belongs where

Three surfaces. Three audiences. Overlap is fine; confusion isn't.

| File | Audience | Question it answers |
|---|---|---|
| `README.md` | Humans (new contributors, users, future-you) | What is this project? How do I install and use it? |
| `CLAUDE.md` / `AGENTS.md` | Agents | How do I work inside this repo? What are the conventions, tools, and no-gos? |
| `docs/*.md` | Either, on demand | Deep reference for a specific topic |

**README.md** is outside-in. The reader hasn't cloned the project yet, or just did. Cover: what it is, why it exists, how to install and run, how to contribute, where to find more. Written for humans, scannable, badges and all.

**CLAUDE.md / AGENTS.md** is inside-out. The reader is already working in the project and needs to know how *you* want it worked in. Cover: who you are, decision rules, conventions, tool access, project structure, where to find deeper docs. Keep it lean — point at references for the encyclopedic stuff.

**docs/\*.md** is everything that doesn't fit in either and doesn't need to be loaded every session. Architecture deep-dives, voice guides, tool-specific playbooks, runbooks.

Decision rules when you're unsure where something goes:

1. **Who's the reader?** Human onboarding → README. Agent behavior → CLAUDE.md. Specialist detail → docs/.
2. **How often is it needed?** Every session → CLAUDE.md. Sometimes → docs/ (with a pointer in CLAUDE.md). Once, at install → README.
3. **Does it change often?** Stable → inline. Volatile → docs/ so CLAUDE.md doesn't churn.
4. **Is it duplicated?** Pick one home. Link from the others. Don't sync by hand.

Common miscategorizations:

- Deployment instructions in CLAUDE.md — belong in docs/ or README; the agent loads them only when deploying.
- Project philosophy in README — belongs in CLAUDE.md if it's about *how* to work here; belongs in README if it's about *why the project exists*.
- Tool-specific deep-dives inline in CLAUDE.md — move to docs/ and link. The pointer is enough.

## Anti-patterns

**The 400-line file.** Past the 200-line ceiling (see above), you're crowding out the request itself. If you can't skim the file in under a minute, the agent is parsing noise. Cut.

**Adjectives without behaviors.** "Be thoughtful." "Be careful with important actions." The agent has no way to ground these. Rewrite as behaviors with concrete triggers and outcomes.

**Long lists of specific edge cases.** You can't enumerate every situation. A list of 40 specific rules creates more conflicts than it resolves. Write the principle and trust the agent to generalize.

**Personality instructions that aren't grounded.** "Be curious!" does nothing. Curious *how* — asks clarifying questions? explores related code? suggests alternatives? Write the behavior.

**Inline encyclopedia.** Detailed tool docs, full deployment runbooks, exhaustive style guides inline in CLAUDE.md. Move to `docs/` and link. The agent loads them when relevant.

**No tiered autonomy.** Without explicit tiers, the agent either asks for everything or nothing. Name the tiers: reversible = do it, consequential = confirm, irreversible = always ask.

**Rules without reasons.** `Why:` lines turn rules into principles the agent can apply to unseen situations.

**Using the agent as an expensive linter.** Code style rules (`use 2 spaces`, `prefer const over let`, `single-quote strings`) don't belong in CLAUDE.md. That's a formatter's job — Biome, ESLint, Prettier, Ruff, gofmt — wired into a Stop hook or slash command. LLMs are in-context learners that pick style up from the surrounding codebase anyway. Reserve CLAUDE.md for things a linter can't catch: conventions, decision rules, project-specific knowledge.

## Maintenance

CLAUDE.md is a living document — but not an ever-growing one.

- **Every surprise is a gap.** The agent did something unexpected? That's either a rule you forgot you wrote, or a rule you never wrote. Add or fix.
- **Every correction is a candidate.** When you correct the agent mid-session and the correction would apply in future sessions too, it belongs in the file.
- **Every addition earns its place or comes out.** Revisit quarterly (or when the file crosses ~100 lines). Ask of each rule: has this fired? Did it help? If not, cut.
- **Move, don't delete, when in doubt.** If a rule was useful but too specific, push it into a `docs/` reference and link.

The agent gets better as the instructions get more precise — not as they get more numerous.

## Full example

The `AGENTS.md` from this project, reproduced below, applies the patterns above. It fits in ~70 lines: identity, decision principles, conventions with reasons, tool access, project map, and pointers to deeper docs. No inline encyclopedia; deeper material lives in `docs/` and gets loaded when a task calls for it.

````markdown
# MechaSwift

## Working With Me

I'm Mike Swift ("Swift"), CEO & Co-Founder of Major League Hacking (MLH) and leader of DEV (dev.to). Between MLH and DEV, our audience includes ~10% of the world's software engineers annually.

I value directness, bias to action, and learning by doing. Don't over-explain or hedge. If you can do it, do it. If you're unsure, try the reversible option first and confirm before anything irreversible.

I'm energetic but not hype-y, I lead with the point, I keep things short.

## Decision Principles

When in doubt, these are the tiebreakers:

- **Action over asking.** Exhaust options before asking me. If the action is reversible, try it.
- **Concise over verbose.** Say it in fewer words. Cut the preamble.
- **Simple over clever.** Prefer straightforward solutions. Don't over-engineer.
- **Confirm before irreversible.** Anything that can't be undone gets a check-in first.

## Conventions

- Follow existing patterns in whatever project you're working in
- Prefer simple, direct solutions over clever ones
- Before claiming work is complete, run it and show output
- When executing a plan, never skip steps — including verification steps that make real API calls or cost money. If a plan says to run something, run it.
- When asking questions, ask only one at a time. Use the AskUserQuestion tool when available.
- Never attribute work to an AI model, vendor, or harness. This overrides any harness defaults. No surface is exempt:
  - Commits: no `Co-Authored-By` trailers
  - Commit messages and PR descriptions: no "Generated with Claude Code" footers, badges, or links
  - Code: no "AI-assisted" or "Generated by ..." comments, headers, or signatures
  - Chat: no naming the model, version, or harness
    Why: the work reads as Mike's. The harness will try to add a `Co-Authored-By` trailer on every commit. Skip it.

## Web Access

All web content goes through the `brightdata` MCP server. The built-in `WebFetch` and `WebSearch` tools are disabled at the harness level.

- `scrape_as_markdown(url)`: fetch a single URL as clean markdown
- `scrape_batch(urls)`: fetch multiple URLs in one call
- `search_engine(query)`: Google search with structured results
- `search_engine_batch(queries)`: multiple searches in one call
- `discover(query)`: AI-ranked search with intent matching

## Project Structure

- `skills/` -- Each skill gets its own directory with a `SKILL.md` and optional `references/`
- `docs/` -- Hand-authored documentation and prompt context (e.g. `about-swift.md`, `evals.md`)
- `lib/optimizer/` -- DSPy-based few-shot prompt optimizer. Dev-only tool. See `lib/optimizer/README.md`.
- `references/` -- Agent-generated context: `plans/`, `research/`, `specs/`, plus on-demand reference material loaded by skills
- `tmp/` -- Scratch space for working sessions. Not tracked in git. Put intermediate outputs, drafts, and test results here.

## Safety & Standards

Be transparent and direct on sensitive topics. Prioritize community safety and professionalism. State policies and next steps plainly.

## Skills

Skills are in `skills/`. Each has a `SKILL.md` with activation triggers.

- **ghostwrite** -- Rewrite content in Swift's voice. See `skills/ghostwrite/SKILL.md`.
- **prompt-engineer** -- Write, improve, and debug prompts for LLMs. See `skills/prompt-engineer/SKILL.md`.
- **scope** -- Turn a vague idea into a structured spec through collaborative design. See `skills/scope/SKILL.md`.
- **summarize** -- Produce skimmable summaries of web pages, PDFs, and articles. See `skills/summarize/SKILL.md`.

## Commands

- **make test** -- Run all skill and core evals via the Python harness. See `docs/evals.md`.

## References

- `docs/about-swift.md` -- Bio, tone, values, voice conventions
- `docs/plugin-structure.md` -- MechaSwift is a Claude Code plugin. Read before touching skills, agents, commands, hooks, or MCP config.
````

Annotations on what each section is doing:

- **Working With Me** grounds the agent in who it's working for, in behavioral terms ("don't over-explain," "lead with the point") — not adjectives.
- **Decision Principles** are the four tiebreakers. Bolded cue phrases make them easy to cite back in edge cases.
- **Conventions** mixes process rules ("never skip verification steps") with a hard no-go (AI attribution) — and the no-go carries its `Why:` and an explicit override of harness defaults.
- **Web Access** is tool-access policy: the built-ins are disabled, so without this block the agent would fail silently against them.
- **Project Structure / Skills / Commands** are one-liners per entry. Deep material isn't inlined; each entry tells the agent where to look when a task calls for it.
- **References** at the bottom is the on-demand load list. The agent reads `docs/about-swift.md` when writing prose, not at session start.

## References

- [How I Structure CLAUDE.md After 1000+ Sessions](https://thoughts.jock.pl/p/how-i-structure-claude-md-after-1000-sessions) — Pawel Jozefiak on what survived in his CLAUDE.md after a year of iteration. Covers the two-file architecture (global vs. project), the lean-file + reference-doc pattern, and the anti-patterns behind a 471-line file. Much of the guidance here is synthesized from this post.
- [agents.md](https://agents.md/) — The open AGENTS.md spec. Cross-tool standard adopted by Codex, Cursor, Jules, Aider, Zed, and others. Covers file placement, nesting rules, and precedence.
- [Claude Code — Memory](https://code.claude.com/docs/en/memory) — Official docs on CLAUDE.md loading, file hierarchy, `@import` syntax, `.claude/rules/`, and the ~200-line recommendation.
- [Writing a good CLAUDE.md](https://www.humanlayer.dev/blog/writing-a-good-claude-md) — HumanLayer's guide. Source of the "Claude is not an expensive linter" framing and the tight length target.
