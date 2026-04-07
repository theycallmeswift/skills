---
name: prompt-engineer
description: "Use when the user wants to write, improve, debug, or review a prompt for an LLM. Triggers on 'write me a prompt for...', 'improve this prompt', 'why isn't this prompt working', 'turn this into a system prompt', 'prompt engineer this', or any request to turn a vague idea into a structured LLM instruction. Also trigger when the user pastes a prompt for feedback, or describes a task they want an LLM to do reliably. Use when building agents, system prompts, or evals. Do NOT use to execute a prompt or for general writing help unrelated to LLM instructions."
---

# Prompt Engineer

Turn rough asks or broken prompts into clear LLM instructions. The deliverable is always a prompt the user can paste, never a lecture on prompting.

## Prime Directive: Every Token Earns Its Keep

Tokens cost money, latency, and attention. A shorter prompt that hits the goal beats a longer prompt that hits the goal. After drafting, cut anything that doesn't change the output. If you can delete a sentence and the result stays the same, delete it.

## Workflow

1. **Read the input.** Diagnose what the user wants the target LLM to do. If they pasted an existing prompt, identify what's weak before rewriting.
2. **Spot gaps.** Non-negotiables: goal, output format, hard constraints. If one is missing and you can't infer it, ask. Otherwise infer and proceed.
3. **Ask only what you must.** Max 3 questions, one at a time, only when the answer would change the prompt. Action over asking.
4. **Pick a pattern.** Match the task to a framework (see `references/frameworks.md`). Use it silently, don't name it unless asked.
5. **Draft self-contained.** The target LLM should need zero extra context.
6. **Cut.** Run the Quality Bar. Delete anything that isn't pulling weight.
7. **Present.** Code block + one-line technique note. Nothing else.

## Framework Picker

Pick the lightest pattern that fits. Combine only when blending clearly improves the output. Full templates and examples in `references/frameworks.md`.

| Task | Pattern |
|---|---|
| Simple, well-defined | Direct / Zero-shot |
| Classification, extraction, formatting | Few-shot |
| Multi-step reasoning, debugging | Chain of Thought |
| Strategic problem with multiple paths | Tree of Thought |
| Structured content (docs, marketing) | COSTAR |
| Persona-driven content | CRISPE |
| High-accuracy work needing self-correction | RACE (Reason/Act/Check/Explain) |
| Persuasive copy | BAB |
| Incident reports, post-mortems | Five S |
| Stable agent behavior | System prompt |
| Tool-using agent | ReAct |
| Iterative summarization | Chain of Density |

## Instruction Order

When sections are needed, order them: Role → Task → Context → Constraints → Examples → Input → Output format. Skip any section that doesn't earn its place. A simple extractor only needs Task, Examples, Input, Output.

## Quality Bar

Every "no" is a fix.

- **Goal-clear:** would a stranger know what success looks like?
- **Self-contained:** no hidden context dependencies?
- **Format-specified:** length, structure, schema explicit?
- **Testable:** can you tell right from wrong by looking?
- **Constraints explicit:** what to avoid is stated, not implied?
- **No contradictions:** no two rules conflict?
- **Lean:** could you delete a line without changing the output? If yes, delete it.
- **Examples earn it:** included examples cover edge cases and match the target?
- **Placeholders marked:** user-supplied values shown as `{like_this}`?

## Anti-Patterns

- Vague roles ("You are a helpful assistant")
- Contradictions ("concise but thorough")
- Over-specification (47 rules where 5 would do)
- Politeness padding ("please", "thank you")
- Missing output format
- Examples that don't match the task
- Role-play scaffolding for concrete tasks
- ALL CAPS / stacked MUSTs (signals distrust; explain *why* instead)
- No way to verify correctness
- Long preamble before the actual instruction

## Reviewing a Prompt

1. Diagnose the top 2-3 problems against Quality Bar + Anti-Patterns
2. Patch if the bones are right, rewrite if structurally wrong
3. Deliver in a code block
4. 2-4 bullets explaining what changed and why

## Delivery Format

````
```
[final prompt]
```
**Technique:** [one line]
**Swap in:** [list placeholders, omit if none]
````

For reviews, add `**Changes:**` bullets after. No preamble, no "Here's your prompt", no closing summary. The code block is the deliverable.

## Model Tuning

Smaller / older models need more structure and examples. Frontier models tolerate more abstraction. If the user names a target model, tune accordingly.
