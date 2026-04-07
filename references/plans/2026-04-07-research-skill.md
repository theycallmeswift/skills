# Research Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `mechaswift:research` skill plus a `mechaswift:researcher` plugin subagent that turn a research request into a cited markdown report at `references/research/YYYY-MM-DD-<slug>.md`.

**Architecture:** A plugin subagent at `agents/researcher.md` does bounded search-and-reflect using brightdata MCP + Read/Grep/Glob and returns structured Findings + Reflection + Sources. A skill at `skills/research/SKILL.md` orchestrates: parses `--depth`, plans, dispatches one or more researchers in parallel via the `Agent` tool, synthesizes globally-renumbered citations into a report, writes the file, and runs a coverage verify step. The orchestrator never searches the web itself.

**Tech Stack:** Claude Code plugin (`mechaswift`), brightdata MCP (`scrape_as_markdown`, `scrape_batch`, `search_engine`, `search_engine_batch`), native `Agent` tool with `subagent_type: "mechaswift:researcher"`, plugin skills/agents conventions per `docs/plugin-structure.md`.

**Spec:** `references/specs/2026-04-07-research-skill.md` — read this first; the plan implements it directly.

---

## File Structure

Files this plan creates or modifies:

- **Create** `agents/researcher.md` — plugin subagent. Frontmatter (`name`, `description`, `tools`) + system prompt enforcing the search-and-reflect loop, search budget passed in by orchestrator, structured return shape. No `Write`, no `Bash`, no `Agent` (no recursion).
- **Create** `skills/research/SKILL.md` — orchestrator skill. Activation triggers, depth-flag parsing, planning rules, slug generation, dispatch template, synthesis + citation renumbering, report skeletons, write + verify steps.
- **Create** `skills/research/evals/evals.json` — seven quality eval cases with tool-trace assertions, mirroring `skills/summarize/evals/evals.json` shape.
- **Modify** `CLAUDE.md` — add `research` to the Skills list under `## Skills`.
- **Modify** `AGENTS.md` — same Skills list update (mirror of CLAUDE.md surface).
- **No code** for `references/research/` or `tmp/research/<slug>/` — these directories are created at runtime by the skill itself.

The skill file is the only large surface here; everything else is small.

---

## Task 1: Create the researcher subagent

**Files:**
- Create: `agents/researcher.md`

- [ ] **Step 1: Create the agents directory if missing**

Run: `ls agents 2>/dev/null || mkdir agents`
Expected: directory exists after the command.

- [ ] **Step 2: Write `agents/researcher.md`**

Create the file with this exact content:

```markdown
---
name: researcher
description: Conducts focused research on a single topic and returns structured findings with citations. Sources may include the web, local files, or other available tools. Use when a task requires gathering and synthesizing information that isn't already in context.
tools:
  - mcp__brightdata__search_engine
  - mcp__brightdata__search_engine_batch
  - mcp__brightdata__scrape_as_markdown
  - mcp__brightdata__scrape_batch
  - Read
  - Grep
  - Glob
---

# Researcher

You are a focused research subagent. You receive a single topic, a small amount of context, and a hard search budget. You gather information, reflect, and return structured findings. You do not write files. You do not call other agents. You do not loop forever.

## Inputs

The orchestrator passes you a prompt of this shape:

```
Research topic: <focused topic for this researcher>

Context: <one or two sentences from the original user request>

Search budget: <N> brightdata searches maximum.

Return your findings as prose with inline [N] citations, followed by a
### Sources section listing each source as `[N] Title: URL` on its own line.
Number citations starting from [1] within your own response — the orchestrator
will renumber globally when synthesizing.

Stop as soon as you can answer comprehensively. Do not search for perfection.
```

## Loop

1. **Plan.** Decide which 1–3 initial searches will move you furthest. Do not exceed the search budget across the whole run.
2. **Search.** Use `mcp__brightdata__search_engine` or `mcp__brightdata__search_engine_batch`. Never use `WebFetch` or `WebSearch` — they are not available and they are forbidden.
3. **Read promising results.** Use `mcp__brightdata__scrape_as_markdown` for one URL, `mcp__brightdata__scrape_batch` for several. For local files use `Read`/`Grep`/`Glob`.
4. **Reflect after each pass.** Ask: do I have enough to answer the topic comprehensively? If yes, stop. If not, identify the single biggest gap and do one more targeted search.
5. **Stop conditions.** Stop when ANY of these is true:
   - You can answer the topic comprehensively.
   - You have used your full search budget.
   - Two consecutive searches added nothing new.

## Return shape

Return exactly this structure. Nothing before, nothing after.

```
## Findings

<prose with inline [1], [2], [3] citations — no bullet dump, write it as if
it will be read by a human; cite every non-obvious claim>

## Reflection

<one short paragraph: what you found, what is still uncertain, why you stopped>

### Sources
[1] Source Title: https://example.com/one
[2] Another Source: https://example.com/two
```

## Rules

- Number citations locally starting at `[1]`. The orchestrator renumbers globally.
- Every inline `[N]` must resolve to an entry in your `### Sources` section.
- Never invent a source or a URL. If you didn't read it, don't cite it.
- Never use `WebFetch` or `WebSearch`. Only the brightdata MCP tools listed in your frontmatter.
- Do not write files. Do not call other agents.
```

- [ ] **Step 3: Verify the file parses as a plugin agent**

Run: `head -20 agents/researcher.md`
Expected: frontmatter block with `name: researcher`, `description:`, and a `tools:` list including the six tools above.

- [ ] **Step 4: Commit**

```bash
git add agents/researcher.md
git commit -m "feat: add researcher subagent for research skill"
```

---

## Task 2: Create the research skill orchestrator

**Files:**
- Create: `skills/research/SKILL.md`

- [ ] **Step 1: Create the skill directory**

Run: `mkdir -p skills/research/evals`
Expected: both directories exist.

- [ ] **Step 2: Write `skills/research/SKILL.md`**

Create the file with this exact content:

````markdown
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

Re-read `tmp/research/<slug>/request.md` and the final report. In the chat (not in the report file), output a single coverage line of the form:

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
````

- [ ] **Step 3: Sanity-check the file**

Run: `head -5 skills/research/SKILL.md && wc -l skills/research/SKILL.md`
Expected: frontmatter with `name: research` and a non-trivial line count (>100).

- [ ] **Step 4: Commit**

```bash
git add skills/research/SKILL.md
git commit -m "feat: add research orchestrator skill"
```

---

## Task 3: Create the eval cases

**Files:**
- Create: `skills/research/evals/evals.json`

- [ ] **Step 1: Write `skills/research/evals/evals.json`**

Create the file with this exact content:

```json
{
  "skill_name": "research",
  "evals": [
    {
      "id": 1,
      "prompt": "research context engineering for AI agents",
      "expected_output": "A cited markdown report written to references/research/ produced by exactly one researcher subagent",
      "files": [],
      "assertions": [
        { "text": "Exactly one Agent tool call was made with subagent_type 'mechaswift:researcher'", "type": "structural" },
        { "text": "A file matching references/research/\\d{4}-\\d{2}-\\d{2}-context-engineering[a-z0-9-]*\\.md was written", "type": "structural" },
        { "text": "Tool trace shows brightdata MCP tools were used (search_engine, search_engine_batch, scrape_as_markdown, or scrape_batch)", "type": "structural" },
        { "text": "Tool trace does NOT mention WebFetch or WebSearch", "type": "structural" },
        { "text": "The orchestrator itself made zero direct brightdata calls — all brightdata calls happened inside the researcher subagent", "type": "structural" }
      ]
    },
    {
      "id": 2,
      "prompt": "compare LangGraph vs CrewAI vs AutoGen for agent orchestration",
      "expected_output": "A comparison report produced by three parallel researchers, one per framework",
      "files": [],
      "assertions": [
        { "text": "Exactly three Agent tool calls were made with subagent_type 'mechaswift:researcher'", "type": "structural" },
        { "text": "All three Agent calls were dispatched in a single assistant response (parallel dispatch)", "type": "structural" },
        { "text": "The final report has a comparison structure with a dedicated section for LangGraph, CrewAI, and AutoGen", "type": "structural" },
        { "text": "Tool trace shows brightdata MCP tools were used", "type": "structural" },
        { "text": "Tool trace does NOT mention WebFetch or WebSearch", "type": "structural" }
      ]
    },
    {
      "id": 3,
      "prompt": "research the current state of OSS vector databases",
      "expected_output": "Output file path matches the canonical naming convention",
      "files": [],
      "assertions": [
        { "text": "Output file path matches the regex references/research/\\d{4}-\\d{2}-\\d{2}-[a-z0-9-]+\\.md", "type": "structural" },
        { "text": "The date in the filename is today's date", "type": "structural" },
        { "text": "The slug portion of the filename is kebab-case and contains 3 to 5 hyphen-separated words", "type": "structural" }
      ]
    },
    {
      "id": 4,
      "prompt": "compare Postgres vs MySQL vs SQLite for embedded analytics",
      "expected_output": "Citations are globally renumbered with no gaps and no duplicates",
      "files": [],
      "assertions": [
        { "text": "The final report contains a '### Sources' section", "type": "structural" },
        { "text": "Source citations are numbered sequentially starting at [1] with no gaps", "type": "structural" },
        { "text": "No two numbered Sources entries share the same URL", "type": "structural" },
        { "text": "Every inline [N] citation in the report body resolves to an entry in the Sources section", "type": "structural" }
      ]
    },
    {
      "id": 5,
      "prompt": "research the tradeoffs of monorepos vs polyrepos",
      "expected_output": "Report contains no self-referential phrasing",
      "files": [],
      "assertions": [
        { "text": "Report does not contain the phrase 'I found'", "type": "structural" },
        { "text": "Report does not contain the phrase 'I researched'", "type": "structural" },
        { "text": "Report does not contain the phrase 'In my research'", "type": "structural" },
        { "text": "Report does not contain the phrase 'My findings'", "type": "structural" },
        { "text": "Report does not contain the phrase 'We searched'", "type": "structural" },
        { "text": "Report does not contain the phrase 'Based on my research'", "type": "structural" }
      ]
    },
    {
      "id": 6,
      "prompt": "research best practices for prompt caching with Claude",
      "expected_output": "Verify step ran: request was saved and re-read, coverage line printed",
      "files": [],
      "assertions": [
        { "text": "A file matching tmp/research/<slug>/request.md was written before the report file", "type": "structural" },
        { "text": "tmp/research/<slug>/request.md was read after being written and before the final assistant response", "type": "structural" },
        { "text": "The final assistant response includes a line beginning with 'addressed:'", "type": "structural" }
      ]
    },
    {
      "id": 7,
      "prompt": "--depth quick research the history of MCP",
      "expected_output": "Quick depth dispatches one researcher with a search budget of 3",
      "files": [],
      "assertions": [
        { "text": "Exactly one Agent tool call was made with subagent_type 'mechaswift:researcher'", "type": "structural" },
        { "text": "The dispatch prompt passed to the researcher contains the substring 'Search budget: 3'", "type": "structural" },
        { "text": "The '--depth quick' flag does not appear in the final report or in the topic passed to the researcher", "type": "structural" }
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate JSON**

Run: `python3 -c "import json; json.load(open('skills/research/evals/evals.json'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add skills/research/evals/evals.json
git commit -m "test: add quality evals for research skill"
```

---

## Task 4: Register the skill in CLAUDE.md and AGENTS.md

**Files:**
- Modify: `CLAUDE.md` (the `## Skills` section)
- Modify: `AGENTS.md` (the `## Skills` section if present)

- [ ] **Step 1: Read both files to find the Skills section**

Run: `grep -n "^## Skills" CLAUDE.md AGENTS.md`
Expected: a line number for each (or only CLAUDE.md if AGENTS.md has no Skills section — in that case skip the AGENTS.md edit).

- [ ] **Step 2: Add the research bullet to `CLAUDE.md`**

Use Edit to insert this bullet under the `## Skills` list, in alphabetical order (between `ghostwrite` and `scope`):

```
- **research** -- Turn a topic into a cited markdown report at `references/research/`. See `skills/research/SKILL.md`.
```

- [ ] **Step 3: Add the same bullet to `AGENTS.md`** (only if it has a `## Skills` section)

Use the same bullet text in the same alphabetical position.

- [ ] **Step 4: Verify**

Run: `grep -n "research" CLAUDE.md AGENTS.md`
Expected: at least one match in each file pointing at the new bullet.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md AGENTS.md
git commit -m "docs: register research skill in project docs"
```

---

## Task 5: Smoke test end-to-end

**Files:** none (runtime check)

- [ ] **Step 1: Reload plugins**

Tell the user to run `/reload-plugins` in their Claude Code session, or do it yourself if the harness exposes it. Confirm `mechaswift:research` and `mechaswift:researcher` show up in the registries.

- [ ] **Step 2: Run a quick-tier smoke test**

In a fresh session, send: `--depth quick research the history of MCP`

Expected:
- One Agent dispatch with `subagent_type: "mechaswift:researcher"` and a prompt containing `Search budget: 3`.
- A file written at `references/research/YYYY-MM-DD-history-of-mcp.md` (or a similar 3–5 word slug).
- A `tmp/research/<slug>/request.md` exists.
- Final assistant response contains a line starting with `addressed:`.

- [ ] **Step 3: Run a parallel comparison smoke test**

In a fresh session, send: `compare LangGraph vs CrewAI vs AutoGen for agent orchestration`

Expected:
- Three Agent dispatches, all in one assistant response.
- A comparison-shaped report at `references/research/YYYY-MM-DD-langgraph-vs-crewai-vs-autogen.md`.
- Sources are globally renumbered with no duplicate URLs.

- [ ] **Step 4: Run the eval suite**

Run: `/eval research`
Expected: all 7 cases pass. If any fail, fix the underlying skill or agent file (not the eval) and re-run.

- [ ] **Step 5: Final commit if any fixes were needed**

If you edited files in Step 4, commit them with a descriptive message. Otherwise this step is a no-op.

---

## Notes for the implementer

- **Plugin namespacing.** This is a Claude Code plugin. The agent is invoked as `subagent_type: "mechaswift:researcher"`, never as `general-purpose`. Read `docs/plugin-structure.md` if anything about the layout is unclear.
- **No `Co-Authored-By` trailers.** Per `CLAUDE.md`, never attribute commits to an AI model or harness.
- **Real network in evals.** Eval cases hit the real brightdata MCP. The whole point of the tool-trace assertion is to confirm the right tools were used; mocking would defeat it. This matches `skills/summarize/evals/evals.json`.
- **Spec is the source of truth.** If anything in this plan contradicts `references/specs/2026-04-07-research-skill.md`, the spec wins. Re-read the relevant section before implementing.
