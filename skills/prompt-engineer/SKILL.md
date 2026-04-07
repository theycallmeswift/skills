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
3. **Infer first, ask rarely.** Ask at most one question, and only when the answer would materially change the prompt. Never more than one at a time. Action over asking.
4. **Pick a pattern.** Match the task to a framework (see `references/frameworks.md`). Use it silently, don't name it unless asked.
5. **Draft self-contained.** The target LLM should need zero extra context.
6. **Cut.** Run the Quality Bar. Delete anything that isn't pulling weight.
7. **Present.** Code block + one-line technique note. Nothing else.

## Framework Picker

Pick the lightest pattern that fits. Combine only when blending clearly improves the output. Full templates and examples in `references/frameworks.md`.

| Task | Pattern | Trigger symptom |
|---|---|---|
| Simple, well-defined | Direct / Zero-shot | Task fits in one sentence, no format ambiguity |
| Classification, extraction, formatting | Few-shot | Output format varies run to run |
| Multi-step reasoning, debugging | Chain of Thought | Model skips steps or jumps to wrong conclusion |
| Strategic problem with multiple paths | Tree of Thought | Multiple viable approaches, trade-offs matter |
| Structured content (docs, marketing) | COSTAR | Output needs locked structure and tone |
| Persona-driven content | CRISPE | Voice is the deliverable |
| High-accuracy work needing self-correction | RACE | Model confidently produces wrong answers |
| Persuasive copy | BAB | Goal is action, not information |
| Incident reports, post-mortems | Five S | Output must be objective and complete |
| Stable agent behavior | System prompt | Same rules across many turns |
| Tool-using agent | ReAct | Model has tools and needs to interleave thinking and calling |
| Iterative summarization | Chain of Density | Summary needs to compress without losing key entities |
| Machine-parseable output | Structured Output / JSON | Downstream code parses the result |

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
- Negative-only instructions ("don't do X, don't do Y") with no positive target
- "Be creative" without constraints
- Unfilled placeholders shipping to the model (`{topic}` left literal)
- Mixing system and user voice inside one prompt

## Reviewing a Prompt

1. Diagnose the top 2-3 problems against Quality Bar + Anti-Patterns
2. Patch if the bones are right, rewrite if structurally wrong
3. Deliver in a code block
4. 2-4 bullets explaining what changed and why

## Worked Example

**Bad input prompt:**

````
```
You are a helpful assistant. Please write a really good summary of the article below. Make it concise but thorough and make sure to cover all the important points. Thanks!
```
````

**Diagnosis:** Vague role, contradiction ("concise but thorough"), no format, no length, politeness padding, no testable success criterion.

**Rewrite:**

````
```
Summarize the article below in 3 bullets. Each bullet: one sentence, max 20 words, lead with the most important fact. Skip background the reader can infer from the headline.

Article: {article}
```
````

**Technique:** Direct + format constraint + per-bullet length cap.
**Swap in:** `{article}`

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
