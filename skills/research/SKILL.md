---
name: research
description: "Use when the user wants to research a topic and produce a durable, cited report. Triggers on requests like 'research X', 'do research on Y', 'investigate Z', 'compare A vs B', 'what's the state of the art on...', 'dig into...', 'give me a writeup on...', or any request that asks you to gather and synthesize information from multiple sources rather than summarize a single page. Also trigger when the user wants a saved markdown report rather than a chat reply. If the user just wants a single page summarized, use mechaswift:summarize instead. If the user wants to scope or design something, use mechaswift:scope instead."
---

# Research

Turn a research request into a cited markdown report saved to `references/research/YYYY-MM-DD-<slug>.md`. You are the **orchestrator**. You do not search the web yourself. You delegate to one or more `mechaswift:researcher` subagents and synthesize their structured findings.

## When NOT to use this skill

- Single page or PDF → `mechaswift:summarize`
- Designing or scoping a project → `mechaswift:scope`
- Polishing prose → `mechaswift:ghostwrite`

## Inputs

The user message is the topic. The message may also contain `--depth quick|standard|deep` anywhere in the string. Strip the flag from the topic before using it. Default depth is `standard`.

| Tier       | Parallel researchers | Delegation rounds | Searches per researcher |
|------------|----------------------|-------------------|-------------------------|
| `quick`    | 1                    | 1                 | 3                       |
| `standard` | 3                    | 3                 | 5                       |
| `deep`     | 5                    | 5                 | 8                       |

Defaulting to `standard` does not mean defaulting to 3 researchers. See **Plan**.

## Workflow

### 1. Parse depth flag

Scan the user message for `--depth quick`, `--depth standard`, or `--depth deep`. Remove the flag from the message. The remainder is the topic. Pick the matching tier from the table above. Default to `standard` if no flag is present.

### 2. Plan

Default to **1 researcher**. Only parallelize when the topic clearly has independent axes:

- Explicit comparison: "X vs Y", "compare A, B, C" → one researcher per item
- Independent axes: geographic ("US vs EU vs APAC"), temporal ("2010s vs 2020s"), categorical
- Otherwise: 1 researcher

The depth tier caps how many you may dispatch and how many rounds you may run. It is a ceiling, not a target.

### 3. Generate slug

Build a canonical 3–5 word kebab-case slug from the topic, **not** from the user's raw phrasing.

- Lowercase
- Replace non-alphanumerics with `-`
- Collapse repeated `-`
- Trim leading/trailing `-`
- Aim for 3–5 words capturing the core concept

Examples:
- "research context engineering approaches used to build AI agents" → `context-engineering-for-agents`
- "compare LangGraph vs CrewAI vs AutoGen" → `langgraph-vs-crewai-vs-autogen`
- "history of MCP" → `history-of-mcp`

### 4. Save the request

Write the original user message (with `--depth` flag stripped or kept — your choice, just be consistent) to `tmp/research/<slug>/request.md`. Create parent directories as needed. You will re-read this in the verify step.

### 5. Dispatch researchers

For each planned researcher, call the `Agent` tool with `subagent_type: "mechaswift:researcher"`. When dispatching multiple researchers, **send all `Agent` calls in a single response** so they run in parallel.

Use this exact prompt template per researcher, filling in the bracketed slots:

```
Research topic: <focused topic for this researcher>

Context: <one or two sentences from the original user request, only what
this researcher needs>

Search budget: <budget for this tier> brightdata searches maximum.

Return your findings as prose with inline [N] citations, followed by a
### Sources section listing each source as `[N] Title: URL` on its own line.
Number citations starting from [1] within your own response — the orchestrator
will renumber globally when synthesizing.

Stop as soon as you can answer comprehensively. Do not search for perfection.
```

### 6. Iterate if needed

After the first round, look for clear gaps in coverage of the original topic. If gaps exist and you have not hit the round limit for the tier, dispatch a focused follow-up round targeting only the gaps. Otherwise stop.

### 7. Synthesize

Pick the structure that fits the topic:

- **Comparison** — for "X vs Y" or multi-item comparisons. One section per item, then a `## Verdict` or `## Tradeoffs` section.
- **List** — for "tools / patterns / examples of X". A short intro, then bulleted or sectioned items.
- **Overview** — default. Intro + thematic sections.

Write **prose by default**. No self-referential language. Banned phrases include: "I found", "I researched", "In my research", "My findings", "We searched", "Based on my research". Write the report as if a human author already knew the material.

**Renumber citations globally:**

1. Collect every `### Sources` block from every researcher.
2. Deduplicate by URL. Same URL across researchers collapses to one entry.
3. Assign each unique URL a new global number `[1]`, `[2]`, ... sequential, no gaps.
4. Walk the synthesized prose and rewrite every inline `[N]` to point at the new global number.
5. Every inline `[N]` in the final report must resolve to the global `### Sources` list. No orphans.

### 8. Write the report

Target path: `references/research/YYYY-MM-DD-<slug>.md` where `YYYY-MM-DD` is today's date.

**Collision handling:** If the file exists, try `-<slug>-2.md`, then `-3`, etc. Silent. No prompts.

Use this exact skeleton:

```markdown
# <Topic>

**Date:** YYYY-MM-DD

<report body in chosen skeleton with globally-renumbered inline [N] citations>

## Research Notes

### <what researcher 1 investigated>

<researcher 1's Reflection block, verbatim>

### <what researcher 2 investigated>

<researcher 2's Reflection block, verbatim>

### Sources
[1] Title: URL
[2] Title: URL
```

If there was only one researcher, `## Research Notes` still appears with one subsection.

### 9. Verify

Before writing the coverage line, you **MUST** invoke the Read tool on `tmp/research/<slug>/request.md` again — even if you remember its contents, even on the fallback path, even for a one-line request. This re-read is the only mechanism that grades the report against the *original ask* rather than against your own synthesized memory of it. Skipping it defeats the verify step. Then read the final report.

In the chat (not in the report file), output a single coverage line of the form:

```
addressed: <comma-separated list of the request's key asks>
```

Then output the path to the written report so the user can open it.

## Rules

- Never call brightdata, `WebFetch`, or `WebSearch` yourself. Always delegate.
- Never inline the researcher's prompt content into a `general-purpose` Agent call. Always use `subagent_type: "mechaswift:researcher"`.
- Never ask clarifying questions mid-run. Take the topic as given, plan, and execute.
- Never skip the verify step. The coverage line is required.
- Frequent commits do not apply here — this skill is invoked at runtime, not built up over commits.
