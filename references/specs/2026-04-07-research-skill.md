# Research Skill

**Date:** 2026-04-07
**Status:** Draft

## Goal

Add a `mechaswift:research` skill that turns a research request into a cited, well-structured report at `references/research/YYYY-MM-DD-<slug>.md`. The skill orchestrates one or more focused researcher subagents that gather and synthesize information from the web, local files, or other available tools. It exists so that "research X" becomes a one-step request that produces a durable, reviewable artifact instead of a transient chat reply.

## Non-Goals

- **Not a summarizer.** Summarizing a single page or document is `mechaswift:summarize`.
- **Not a writer.** Polishing or rewriting prose is `mechaswift:ghostwrite`.
- **Not interactive scoping.** The skill takes a topic and runs; it does not ask clarifying questions mid-run.
- **Not a general agent loop.** The orchestrator never searches itself; it only delegates to researcher subagents and synthesizes their output.
- **No MCP server additions in v1.** The researcher uses tools that already exist in the plugin (brightdata, Read/Grep/Glob). Adding databases or other sources is a future extension.

## Approach

A single skill at `skills/research/SKILL.md` acts as the orchestrator. A real plugin subagent at `agents/researcher.md` (invoked as `subagent_type: "mechaswift:researcher"`) does the actual gathering. The orchestrator plans, dispatches one or more researchers in parallel via the `Agent` tool, synthesizes their structured findings into a globally-renumbered report, writes it to `references/research/YYYY-MM-DD-<slug>.md`, and verifies coverage against the original request. The architecture mirrors LangChain's deep research agent pattern but uses native plugin subagents instead of inlined prompts.

## Components

- **`agents/researcher.md`** — Plugin subagent. Frontmatter declares name, description, and tool allowlist: `mcp__brightdata__search_engine`, `mcp__brightdata__search_engine_batch`, `mcp__brightdata__scrape_as_markdown`, `mcp__brightdata__scrape_batch`, `Read`, `Grep`, `Glob`. No `Write`, no `Bash`, no `Agent` (no recursion). System prompt: bounded search-and-reflect loop with hard search budgets, structured findings return format, stop conditions.
- **`skills/research/SKILL.md`** — Orchestrator prompt. Workflow: parse depth flag → plan → save request → generate slug → dispatch researchers → synthesize → write report → verify. Includes report skeletons (comparison / list / overview), citation renumbering rules, slug generation rules, collision handling.
- **`skills/research/evals/evals.json`** — Seven quality eval cases with tool-trace assertions.
- **`references/research/`** — Existing directory. Final reports land here as `YYYY-MM-DD-<slug>.md`.
- **`tmp/research/<slug>/request.md`** — Per-run scratch file holding the original user request, used by the verify step.

## Data / Interfaces

### Researcher description (`agents/researcher.md` frontmatter)

Task-shaped, not source-shaped, so it stays valid as new tools are added:

> Conducts focused research on a single topic and returns structured findings with citations. Sources may include the web, local files, or other available tools. Use when a task requires gathering and synthesizing information that isn't already in context.

### Dispatch prompt template (orchestrator → researcher)

Passed as the `prompt` parameter to the `Agent` tool when invoking `subagent_type: "mechaswift:researcher"`:

```
Research topic: <focused topic for this researcher>

Context: <one or two sentences from the original user request, only what
this researcher needs>

Search budget: <3 | 5 | 8> brightdata searches maximum.

Return your findings as prose with inline [N] citations, followed by a
### Sources section listing each source as `[N] Title: URL` on its own line.
Number citations starting from [1] within your own response — the orchestrator
will renumber globally when synthesizing.

Stop as soon as you can answer comprehensively. Do not search for perfection.
```

### Researcher return shape

```
## Findings

<prose with inline [1], [2], [3] citations>

## Reflection

<one short paragraph: what was found, what is still uncertain, why stopped>

### Sources
[1] Source Title: https://example.com/one
[2] Another Source: https://example.com/two
```

### Final report shape (`references/research/YYYY-MM-DD-<slug>.md`)

```
# <Topic>

**Date:** YYYY-MM-DD

<report body in chosen skeleton — comparison / list / overview — with
globally-renumbered inline [N] citations, prose by default, no
self-referential language>

## Research Notes

<each researcher's Reflection block, preserved verbatim under a subheading
naming what that researcher investigated>

### Sources
[1] Title: URL
[2] Title: URL
...
```

### Depth flag

The skill accepts an optional `--depth` argument anywhere in the user message. Strip it before treating the rest as the topic. Default `standard`.

| Tier       | Parallel researchers | Delegation rounds | Searches per researcher |
|------------|----------------------|-------------------|-------------------------|
| `quick`    | 1                    | 1                 | 3                       |
| `standard` | 3                    | 3                 | 5                       |
| `deep`     | 5                    | 5                 | 8                       |

The `standard` tier matches the LangChain deep research defaults.

### Slug generation

Orchestrator generates a canonical 3–5 word kebab-case slug from the topic, not from the user's raw phrasing. Lowercase, replace non-alphanumerics with hyphens, collapse repeats. Example: "research context engineering approaches used to build AI agents" → `context-engineering-for-agents`.

### Collision handling

If `references/research/YYYY-MM-DD-<slug>.md` already exists, append `-2`, `-3`, ... until a free name is found. Silent. No prompts.

### Citation renumbering

Each researcher cites locally starting at `[1]`. The orchestrator merges all sources and assigns each unique URL exactly one global number, sequential starting at `[1]`, no gaps. Inline citations in the synthesized prose are rewritten to reference the global numbers. Two sources with the same URL collapse to one entry.

### Workflow (orchestrator)

1. **Parse depth flag** from the user message; default `standard`. Strip the flag from the topic string.
2. **Plan** the research. Default to **1 researcher**. Only parallelize for explicit comparisons ("X vs Y") or clearly independent axes (geographic, temporal).
3. **Generate slug** from the canonical topic.
4. **Save request** to `tmp/research/<slug>/request.md` so the verify step can re-read it.
5. **Dispatch** one or more `Agent` calls with `subagent_type: "mechaswift:researcher"`. Multiple dispatches in a single response when parallelizing. Pass the per-researcher search budget in the prompt.
6. **Iterate if needed.** If the first round leaves clear gaps, dispatch a focused follow-up round. Stop after the round limit.
7. **Synthesize.** Choose a structure skeleton (comparison / list / overview). Renumber citations globally. Write prose by default. No self-referential language.
8. **Write report** to `references/research/YYYY-MM-DD-<slug>.md`, applying collision suffixes if needed. Append the `## Research Notes` section preserving each researcher's `## Reflection` block. End with `### Sources`.
9. **Verify.** Re-read `tmp/research/<slug>/request.md` and the final report. Output a one-line coverage check ("addressed: X, Y, Z") to the chat.

## Testing

### Quality evals (`skills/research/evals/evals.json`)

Seven cases. Every case includes a Tool Trace assertion confirming brightdata MCP tools were used and `WebFetch` / `WebSearch` were not.

| # | Case                            | Prompt                                                                | Key assertions |
|---|---------------------------------|-----------------------------------------------------------------------|----------------|
| 1 | Single-researcher decomposition | "research context engineering for AI agents"                          | Exactly 1 `Agent` call with `subagent_type: mechaswift:researcher`; report written to `references/research/YYYY-MM-DD-context-engineering*.md`; tool trace shows brightdata, no WebFetch/WebSearch |
| 2 | Parallel comparison             | "compare LangGraph vs CrewAI vs AutoGen for agent orchestration"      | 3 parallel `Agent` calls dispatched in a single response; final report has comparison structure with sections per framework |
| 3 | Output location & filename      | (reuse #1 output)                                                     | File path matches `references/research/\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md`; date is today; slug is kebab-case, 3–5 words |
| 4 | Citation discipline             | (reuse #2 output)                                                     | `### Sources` present; citations sequential starting at `[1]` with no gaps; no duplicate URLs across numbered entries; every inline `[N]` resolves to a Sources entry |
| 5 | No self-referential prose       | (reuse #1 output)                                                     | Report contains none of: "I found", "I researched", "In my research", "My findings", "We searched" |
| 6 | Verify step ran                 | "research best practices for prompt caching with Claude"              | Orchestrator wrote `tmp/research/<slug>/request.md` and re-read it before declaring done; final response includes a coverage line |
| 7 | Depth flag respected            | "--depth quick research the history of MCP"                           | Exactly 1 `Agent` dispatch; researcher's search budget in dispatch prompt is 3 |

Eval cases hit the real network (real brightdata calls), matching the `summarize` skill's eval pattern. The tool-trace assertion is the whole point — mocking would defeat it.

### Trigger evals

Handled separately by `skill-creator`'s auto-generated trigger optimization loop, per `docs/evals.md`. Run after the skill is in good shape. Not authored by hand.

### Manual checks

- Eyeball one `--depth deep` run end-to-end to confirm 5/5/8 budgets feel right in practice.
- Confirm collision handling produces a `-2` suffix when running the same topic twice in one day.

## Open Questions

1. **Reflection-to-report ratio.** v1 preserves every researcher's `## Reflection` block under `## Research Notes`. If `deep`-tier runs produce too much noise (5 reflections per round, multiple rounds), we may want to summarize them rather than concatenate. Defer until we see real `deep` output.
2. **Future source expansion.** When we add database or internal-docs MCP servers, the researcher's tool allowlist will need to grow. The description is already source-agnostic so it should not need rewriting, but the search budgets (currently brightdata-shaped) may need to be retiered per source type.
