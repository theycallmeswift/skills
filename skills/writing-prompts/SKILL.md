---
name: writing-prompts
description: Use whenever drafting, revising, or refining a prompt for an LLM — system prompts for the API, prompts for subagents and Task dispatches, single-shot user prompts, slash command bodies, the description and body text of a SKILL.md, AGENTS.md or CLAUDE.md repo context files, and `docs/*.md` files that an agent will read as context. Triggers on phrases like "write a prompt", "draft a system prompt", "draft the SKILL.md", "help me prompt the model", "this CLAUDE.md is too long", or any ask whose output is text another LLM will read. Don't use for building a skill end-to-end, evaluating a skill, debugging why a skill does or doesn't trigger, or restructuring an existing skill (splitting to references/, trimming a long SKILL.md) — those are writing-agent-skills, which calls this skill for wording. Also not for critiquing a prompt without rewriting it (code-review-style work), writing prose for human readers (blog posts, marketing copy, Slack or email messages, announcements), or generating training data.
---

# Writing prompts

A prompt is any text written to be read by an LLM — system prompts for the API, subagent or Task dispatches, slash command bodies, SKILL.md instructions, AGENTS.md / CLAUDE.md, `docs/*.md` files agents load as context. The same four ingredients (role, scope, output shape, examples) carry every variant; what differs is the length budget and the structural rules layered on top.

## Triage

Pick the reference that matches the prompt's shape and read it before drafting. If none match, the core workflow below is the lowest common denominator and handles the case directly.

- **Skill body, slash command, subagent definition** → read [`references/skills.md`](references/skills.md). Adds frontmatter, triggering description, and namespace conventions.
- **Session-level agent guidance** — files loaded once at session start and weighed against *every* subsequent turn regardless of task: `AGENTS.md`, `CLAUDE.md`, an onboarding doc whose audience is an agent, a team-norms file read as standing agent context. The defining property is *persistence across the whole session, applies regardless of task*. Filename is not the trigger; *function* is. Domain reference docs that load only when working in that domain (e.g., `docs/writing-tests.md`, `docs/architecture.md`) are NOT this — they belong in the bucket below.
  - **First action: copy [`assets/agent-md-template.md`](assets/agent-md-template.md) to the target path.** Then fill the `{{variables}}` and delete the `<!-- comments -->`. Delete entire sections only when the comment marks them optional (e.g., `## Tool Access`). Do not hand-write the structure from prose.
  - Read [`references/agent-md.md`](references/agent-md.md) for the rationale behind each section and the length budget; the template is the source of truth for structure.
- **Everything else** (one-shot API prompt, ad-hoc subagent dispatch, on-demand domain reference docs like `docs/writing-tests.md` or `docs/architecture.md`, prompt for an end-user app) → no reference needed. Use the workflow below directly.

## The four ingredients

Every working prompt has four ingredients. Author them as named sections — LLMs pattern-match on structure more reliably than on prose.

1. **Role.** One sentence on who the model is acting as and its top constraint. *"You are a code reviewer focused on correctness bugs."* Not *"You are a helpful AI assistant."*
2. **Scope.** What's in, what's out, what the input is. Negative constraints often do more work than positive ones — *"Do not comment on style; a linter handles that"* prevents nitpicks more reliably than *"focus on correctness."*
3. **Output shape.** Schema, template, or worked example. Templates beat prose-described schemas. Show, don't describe.
4. **Examples.** One excellent worked example beats three mediocre ones. Pick one that anchors a hard boundary case the role/scope sentence leaves ambiguous.

Wrap each in an XML tag (`<role>`, `<scope>`, `<output>`, `<example>`). For doc-shaped outputs (AGENTS.md, `docs/*.md`), use markdown headings instead — the relevant reference covers the structure.

## Workflow

1. **Capture intent.** Restate the ask in one sentence. If the ask is vague (purpose unclear, or the input, output shape, or its consumer undefined), ask and end the turn; draft once answered or told to assume. If the ask carries contradictions, list **every** one — completeness-vs-length, no-hedging-vs-flag-uncertainty, zero-shot-vs-quality, conflicting output shapes, mutually exclusive constraints — and either ask the user to resolve them or explicitly name the tradeoff chosen for each. Flagging one contradiction while silently designing around the others fails the prompt.
2. **Pick the reference** per the triage section. Read it before continuing.
3. **Draft the four ingredients** in order. Fill the structure first; don't write prose around it.
4. **Add a worked example** when the output shape benefits from one. Subagent prompts almost always benefit; AGENTS.md / CLAUDE.md usually don't.
5. **Run the editorial pass** below.
6. **Once drafted, emit the tightened prompt as the closing artifact, with `## Notes` above it as evidence of the pass.** The response has exactly two sections in this order: `## Notes` first (3–6 short bullets covering what you cut, restructured, or kept — even a single "no cuts, original was already tight" bullet counts; this section is required as evidence that the editorial pass ran), then `## Tightened prompt` as the last section, in a single fenced block. Nothing after the closing fence — not a post-note, not a "one thing to watch", not an advisory paragraph, not a drop-in instruction ("paste this into…", "use as your…", "drop this verbatim…"), not a sign-off, not a recap of what the prompt does. The author should be able to copy the closing fenced block straight into their target. If you have more to say, it belongs in `## Notes` above.

## Editorial pass

After drafting, run an editorial pass that strips filler and tightens language without changing semantics. Default to the subagent for independence; fall back to inline when nesting is restricted.

- **Subagent (default).** Spawn a fresh subagent briefed with [`agents/prompt-editor.md`](agents/prompt-editor.md). Pass the draft as `{DRAFT_PROMPT}` and the original ask as `{ORIGINAL_REQUEST}`. Use the returned **Tightened prompt** verbatim.
- **Inline (fallback).** If subagent nesting is restricted, the output is under ~30 lines, or you're running inside an eval executor: read [`agents/prompt-editor.md`](agents/prompt-editor.md), apply its rules to your own draft.

Skip the editorial pass entirely when the output is under ~5 lines — the overhead exceeds the gain.

## Output template

Use this scaffold for non-trivial prompts. Drop sections that don't apply; expand sections that need more.

```
<role>
{one sentence: who the model is acting as, top constraint}
</role>

<scope>
in: {what counts}
out: {what doesn't}
input format: {what the model receives}
</scope>

<output>
{schema, template, or one-line example structure}
</output>

<example>
{one fully-worked input → output pair}
</example>

<rules>
- {load-bearing constraint 1}
- {load-bearing constraint 2}
</rules>
```

## Common mistakes

- **Generic role openings.** "You are a helpful AI assistant" produces generic output. Anchor the role in the actual job.
- **Output described in prose, not shown.** "Return a list of findings with file:line references" leaves format ambiguous. A two-line worked example resolves it.
- **Constraints stated only positively.** "Focus on correctness" leaves the model to interpret. "Do not comment on style" rules out a category.
- **Examples used as filler.** Three examples that all anchor the same boundary teach less than one that anchors a hard case.
- **Skipping the editorial pass on long prompts.** Long prompts grow filler. The editor reliably cuts 15–30% without losing meaning.
- **Reusing this skill to *review* a prompt without rewriting it.** This skill drafts and revises. Critique-only work is a code-review task.
