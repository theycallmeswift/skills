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
2. **Concrete enough? Draft. Vague? Ask.** Decide which mode you're in:

   **Draft mode (no questions):** the user has given you a concrete target task AND either a sample input, an existing prompt to fix, or output fields/shape. Examples: "extract parties, dates, termination clauses as JSON", "fix this prompt: <pasted>", "classify these reviews as pos/neg/neutral". Reasonable defaults for unspecified items (model target, exact schema field names, edge cases) are fine. Draft it.

   **Ask mode (one question, then stop):** the user has given you a topic with no shape. Examples: "I need a prompt for summarization", "write me something for customer support". Ask exactly ONE clarifying question that would most change the output. ONE question means one — never join two questions with "and", "also", or a comma. If you catch yourself writing "X and Y?", split it and ask only X. Do not draft, do not list 5 questions, do not invent a content type. Wait for the answer.

   The minimum bar for draft mode: a clear target task plus at least one of {sample input, existing prompt, named output fields}. If you have all three, definitely draft. If you have none, definitely ask.

3. **Pick a pattern.** Match the task to a framework (see `references/frameworks.md`). Use it silently, don't name it unless asked.
4. **Draft self-contained.** The target LLM should need zero extra context.
5. **Cut.** Run the Quality Bar. Delete anything that isn't pulling weight. Then run the Failure Mode Checklist — but ONLY for tasks where these failure modes are real:
   - **Structured extraction from documents** (parsing contracts, invoices, resumes, PDFs, multi-page text into JSON/fields): the prompt MUST say (a) what to do when a required field is missing or unknown (return null, omit, raise) AND (b) how to handle long or multi-page input (process the full document, chunking expectation, or explicit length handling). One short clause each is enough — do not bloat.
   - **Classification on short user-provided text** (sentiment, intent, single review/message): these checks do NOT apply. Do not add missing-field or long-input handling. The lean rule wins.
   - When in doubt: would adding this clause change the output for a realistic input? If no, skip it.
6. **Present.** Code block + one-line technique note. Nothing else.

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
- **Failure modes covered:** what happens when a required field is missing, when input is too long, or when the model is uncertain? At least the relevant ones are addressed (e.g. "return null", "process the full document", "say 'unknown'").

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

The user pasted a broken sentiment classifier prompt and a sample input. They want it fixed, not a clarifying question, because the task and inputs are concrete.

**Bad input prompt:**

````
```
You are a helpful AI. Please carefully look at this customer review and tell me if it is positive or negative or maybe neutral. Be accurate but also fast. Thanks!

Review: {review}
```
````

**Diagnosis:** Vague role, contradiction ("accurate but fast"), three classes named in prose with no enum, no output format, politeness padding.

**Rewrite:**

````
```
Classify the sentiment of the review below as exactly one of: positive, negative, neutral.

Output only the label, lowercase, no punctuation, no explanation.

Review: {review}
```
````

**Technique:** Direct + enum constraint + output-only format.
**Swap in:** `{review}`

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
