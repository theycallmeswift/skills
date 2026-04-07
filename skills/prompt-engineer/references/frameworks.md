# Prompting Frameworks Reference

Deeper detail on the patterns referenced in `SKILL.md`. Load this file when you need a template skeleton, want to remember a framework's exact components, or need to pick between two similar patterns.

Frameworks are not magic. They are checklists that force you to be deliberate about role, context, format, and constraints. Pick the lightest one that fits the task. Combine only when blending genuinely improves the output.

## Quick Comparison

| Framework | Best for | Strength | Drawback |
|---|---|---|---|
| **Direct / Zero-shot** | Simple, well-defined tasks | Fast, low-effort | Unreliable for nuanced tasks |
| **Few-shot** | Format consistency, classification, extraction | Examples beat descriptions | Token cost, examples must match |
| **Chain of Thought** | Multi-step reasoning, debugging, math | Transparent logic, higher accuracy | Verbose, slower |
| **Tree of Thought** | Strategic problems with multiple viable paths | Explores alternatives, avoids local maxima | Slow, expensive |
| **COSTAR** | Structured content (docs, marketing, summaries) | Comprehensive, forces specificity | Verbose for simple tasks |
| **CRISPE** | Persona-driven content with a strong voice | Detailed, context-rich | Overkill for factual queries |
| **RACE** | High-accuracy work that needs self-correction | Built-in validation loop | Stifles creative tasks |
| **BAB** | Persuasive writing, sales, UX copy | Simple, psychologically resonant | Wrong tone for objective work |
| **Five S** | Incident reports, post-mortems, status updates | Structured, objective, blame-free | Rigid, not creative |
| **Agile / Modular** | Reusable prompt systems across a team | Composable, collaborative | Setup overhead |
| **ReAct** | Agents that interleave reasoning and tool use | Tight loop with observability | Only useful with tools |
| **Chain of Density** | Iterative summarization | Compresses without losing info | Niche, summarization only |
| **System Prompt** | Stable agent behavior across many turns | Persists rules, frees user tokens | Not a standalone technique |

---

## Direct / Zero-shot

The simplest pattern. Ask the model to do the thing, no examples, no scaffolding. Use when the task is well-defined and the model has clearly seen the pattern in training.

```
Translate the following English text to French. Return only the translation, no commentary.

Text: {input}
```

**When to skip:** anything where format consistency matters or the task is genuinely novel.

## Few-shot

Show 2-5 input/output pairs that demonstrate the pattern. Stronger than describing the rules. Use for classification, extraction, formatting, or any task where consistency matters across many runs.

```
Convert event names and years into standardized event codes.

Event: Local Hack Day, 2023
Code: LHD-23

Event: Hackcon, 2024
Code: HCN-24

Event: AI Hackathon, 2025
Code:
```

**Tips:**
- Examples should cover edge cases, not just the happy path.
- Keep example format identical to the target format. Inconsistency confuses the model.
- 3-5 is usually the sweet spot. More is not always better.
- Bad examples are worse than no examples. The model will pattern-match the wrong thing.

## Chain of Thought (CoT)

Force the model to reason step by step before answering. Use for math, debugging, multi-step analysis, or any task where the reasoning process matters.

**Zero-shot CoT:** Add "Think step by step before answering."

**Structured CoT:**

```
I have 50 units of stock for Product A. I sold 15 units on Monday, received a shipment of 25 units on Tuesday, and sold 7 more units on Wednesday. How many units do I have left?

Show your reasoning step by step, then give the final number on its own line.
```

CoT routinely improves accuracy on analytical tasks, often by 30-50% on benchmarks, at the cost of more output tokens.

## Tree of Thought (ToT)

Instead of generating one reasoning path, prompt the model to explore multiple paths, evaluate each, and synthesize the best one. Use for strategic problems, optimization, or anywhere there are multiple viable approaches and you want the trade-offs surfaced.

```
I need to optimize a Python script that processes 10GB+ CSV files and crashes from running out of memory on a 16GB machine.

1. Propose three distinct strategies to reduce memory usage.
2. For each strategy, list the pros, cons, and implementation difficulty.
3. Pick the best one for a developer with moderate Python skills.
4. Provide a code snippet showing the recommended approach with pandas.
```

ToT is slow and resource-intensive. Reserve it for problems where the alternatives genuinely matter.

## COSTAR

Six-part structure for content where clarity and structure are critical. Verbose, but it leaves no room for ambiguity.

- **C**ontext: background information
- **O**bjective: the specific goal
- **S**tyle: writing style (formal, conversational, technical)
- **T**one: emotional tone (optimistic, serious, urgent)
- **A**udience: who the response is for
- **R**esponse format: output structure (markdown, JSON, bullets, length)

```
Context: MLH is launching a new AI-focused hackathon for university students. It's a weekend-long event where students build AI projects and learn from mentors.
Objective: Draft a short, exciting announcement post for X to drive sign-ups.
Style: Direct and energetic.
Tone: Encouraging.
Audience: University students interested in tech and AI.
Response format: A single post under 280 characters with relevant hashtags and a placeholder for the sign-up link.
```

Best for marketing copy, formal docs, structured summaries. Overkill for quick brainstorms.

## CRISPE

Role-based framework for tasks where persona and voice are central.

- **C**apacity and role: the persona to adopt
- **I**nsight: background context
- **S**tatement: the actual task statement
- **P**ersonality: the personality and voice
- **E**xperiment: ask for multiple variations

```
Capacity and role: You are a senior engineer at MLH known for being a patient mentor.
Insight: A junior dev submitted their first PR. The code works but lacks comments and uses single-letter variable names.
Statement: Write feedback for this PR.
Personality: Friendly, patient, and educational. Build their skills, don't criticize.
Experiment: Provide three different ways to phrase the feedback in a single GitHub comment.
```

Use for content with a strong voice. Skip for purely data-driven tasks.

## RACE

Reason, Act, Check, Explain. A self-correcting loop that forces the model to validate its own work. Use when accuracy matters more than speed and you want the reasoning visible.

- **R**eason through the problem and possible approaches
- **A**ct on the recommendation
- **C**heck the output for accuracy and counter-arguments
- **E**xplain why the answer is correct

```
A student asked whether to use Python with Flask or JavaScript with Node/Express for their first hackathon web app.

Reason through the decision considering ease of learning, library availability for beginners, and deployment complexity.
Act by recommending one stack.
Check your recommendation by surfacing potential downsides or counterarguments.
Explain why the recommended stack is the best fit for a beginner at a hackathon.
```

Great for fact-checking, technical decisions, and tutorials. Skip for creative or open-ended brainstorming.

> Note: there's a competing definition of RACE in the wild (Role / Audience / Context / Expectation). In this skill, RACE always means Reason / Act / Check / Explain.

## BAB (Before-After-Bridge)

Classic copywriting formula for persuasive content. Surface the problem, paint the solution, bridge the two with the offer.

- **B**efore: the current state or problem
- **A**fter: the ideal state once the problem is solved
- **B**ridge: how to get from one to the other

```
Write marketing copy for the MLH AI Hackathon using BAB.

Before: You have ideas for AI projects but you don't know where to start. You're watching from the sidelines.
After: You've built and shipped your first AI app in a single weekend, surrounded by a community of learners and mentors.
Bridge: The MLH AI Hackathon gives you the workshops, mentorship, and supportive environment to turn your ideas into reality. Sign up now.
```

Built for sales, UX writing, chatbot scripts, and anything meant to drive action. Wrong tone for objective reporting.

## Five S

Structured format for incident reports, post-mortems, and status updates. Forces objectivity and completeness.

- **S**et: scene and context
- **S**ituation: what happened
- **S**takeholders: who was involved or affected
- **S**olution: what was done
- **S**ummary: concise wrap-up

```
Generate an incident report using Five S.

Set: We're running a 24-hour hackathon at a university campus.
Situation: At 2:00 AM, the primary WiFi network for the main hacking space went down.
Stakeholders: 200 students, 15 mentors, MLH staff, university IT.
Solution: IT switched traffic to the backup guest network within 15 minutes and rebooted the core router. Primary network was restored at 2:45 AM.
Summary: Briefly summarize the 45-minute downtime and resolution.
```

Ideal for blameless post-mortems and leadership status reports. Too rigid for creative work.

## Agile / Modular

Build prompts from smaller reusable components. Less a framework, more a workflow. Use when a team is maintaining a library of prompts and wants composability.

```
I'm drafting an email to a potential sponsor. Combine these modules.

[Context Module]: MLH runs hackathons for 150,000+ students globally each year. We're hosting our flagship AI Hackathon in the fall.
[Objective Module]: Persuade the sponsor (a major cloud provider) to partner with us. Emphasize the reach into early-career developers.
[Tone Module]: Professional, confident, partnership-oriented.
[Format Module]: A 4-paragraph email with a clear call-to-action to schedule a 30-minute call.
```

Worth the setup cost only when the same modules will be reused. Otherwise it's overhead.

## ReAct (Reasoning + Acting)

For agents that interleave thinking with tool calls. Each step alternates reasoning and action. Only useful when the model has tools available.

```
You have access to these tools:
- search(query): returns top web results
- calculate(expression): evaluates math
- fetch(url): returns page contents

For each step, output:
Thought: [your reasoning about what to do next]
Action: [the tool call, or "Answer" if you're done]
Observation: [result of the action]

Continue until you have enough to answer. Then output:
Answer: [final answer]

Question: {input}
```

## Chain of Density

For summarization tasks where you want iterative compression. The model writes a first pass, then rewrites it denser, then denser again.

```
Summarize the article below.

Generate 3 increasingly dense summaries. Each must:
- Stay the same length (~80 words)
- Add 1-3 new key entities or facts from the article
- Reuse phrasing from prior summaries where possible
- Become information-dense without becoming unreadable

Output the third (densest) summary as the final result.

Article: {input}
```

## System Prompt Pattern

Not a framework on its own, but a delivery vehicle. Use the system slot for stable instructions (role, rules, format) and keep user messages clean for variable input. Saves tokens on repeated turns and gives the model a stable baseline.

```
You are a senior backend engineer specializing in API design.

Rules:
- Always consider scalability and performance implications
- Default to RESTful patterns unless asked otherwise
- Flag security concerns immediately
- Provide code examples in Python
- Use early-return pattern in code

Response format:
1. Analysis
2. Recommendation
3. Code example
4. Trade-offs
```

Pair with few-shot or CoT inside the system prompt for stronger anchoring.

## Structured Output (JSON / Schema)

When you need machine-parseable output. Combine with few-shot for best results.

```
Extract entities from the text below. Return JSON matching this exact schema:

{
  "people": [{"name": string, "role": string | null}],
  "organizations": [string],
  "locations": [string],
  "dates": [string in ISO format]
}

Rules:
- If a field has no values, return an empty array
- Do not invent entities not present in the text
- Do not include any text outside the JSON object

Text: {input}
```

---

## Combining Frameworks

Most production prompts blend 2-3 patterns. Common combinations that pull their weight:

- **System prompt + Few-shot:** stable role with concrete examples
- **COSTAR + Few-shot:** structured content with a locked output format
- **CRISPE + CoT:** persona-driven analysis with visible reasoning
- **RACE + ReAct:** self-correcting agent loop with tool use
- **Chain of Density inside a System Prompt:** reusable summarizer

Don't blend for the sake of blending. Each added pattern costs tokens and complexity. Add one only if removing it would clearly hurt the output.
