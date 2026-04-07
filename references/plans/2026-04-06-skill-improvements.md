# Skill Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply prioritized improvements to all four mechaswift skills (ghostwrite, scope, summarize, prompt-engineer) based on a recursive prompt-engineering review. Fix real contradictions, eliminate duplication, replace unverifiable instructions with testable ones, and add missing output templates.

**Architecture:** Four independent skill files, each edited in isolation with its own commit. After each skill is edited, run that skill's eval (`/eval <skill>`) as the verification gate. Order: summarize first (has a real bug), then ghostwrite (real contradiction), then scope (missing template), then prompt-engineer (self-improvement).

**Tech Stack:** Markdown skill files under `skills/<name>/SKILL.md`, evals under `skills/<name>/evals/evals.json`, run via the project `/eval` slash command.

---

## File Structure

Files modified by this plan:

- `skills/summarize/SKILL.md` — fix ghostwrite-loop contradiction, dedupe length caps, drop `__underline__`, merge fetch sections.
- `skills/ghostwrite/SKILL.md` — resolve Slack length contradiction, delete `Writing Style` section, replace unverifiable "read it back as Swift" with concrete checklist, add explicit output format.
- `skills/scope/SKILL.md` — collapse Steps vs sub-section duplication, add spec template skeleton, tighten Hard Gate, verify auto-commit norm.
- `skills/prompt-engineer/SKILL.md` — add trigger-symptom column to picker, add one before/after example, add Structured Output row, resolve ask-vs-infer tension, add missing anti-patterns.
- `skills/prompt-engineer/references/frameworks.md` — delete duplicate Quick Comparison table, drop preamble paragraph.

No new files created. No tests added (skills are prompts; evals already exist).

---

## Task 1: Fix `summarize` skill

**Files:**
- Modify: `skills/summarize/SKILL.md`

- [ ] **Step 1: Resolve the Comment ghostwrite-loop contradiction**

The skill currently says three different things about the Comment ghostwrite loop. Step 6 says "Hand that angle to the `ghostwrite` skill." Step 7 says "trim the comment yourself (do not send it back to ghostwrite)." Output Format > Comment says "Run it through the `ghostwrite` skill." A reader has to reconcile three statements.

Edit Step 6 to read:

```
6. **Hand that angle to the `ghostwrite` skill** to rewrite as a forum comment. Ghostwrite is invoked exactly once. If the result is over 20 words, trim it yourself in step 7 — do not re-invoke ghostwrite.
```

Edit the Output Format > Comment section. Replace:

```
A ready-to-paste reply for the post itself, or a Reddit/Hacker News discussion thread. Run it through the `ghostwrite` skill, then display in a code fence.
```

with:

```
A ready-to-paste reply for the post itself, or a Reddit/Hacker News discussion thread. Display in a code fence. (Voice is handled by ghostwrite in step 6, with self-trim in step 7 if over the cap.)
```

- [ ] **Step 2: Drop `__underline__` from Style Rules**

Underline is never used anywhere else in the skill and risks the model emitting `__underline__` literal markdown. Replace this line in `## Style Rules`:

```
- Use **bold**, *italics*, and __underline__ strategically to draw the eye, but don't overdo it.
```

with:

```
- Use **bold** and *italics* strategically to draw the eye, but don't overdo it. Bold and italic conventions are defined per-section above; do not introduce new emphasis styles.
```

- [ ] **Step 3: Verify the changes by re-reading the file**

Read `skills/summarize/SKILL.md` end to end. Confirm:
- Comment loop is described consistently in Step 6, Step 7, and Output Format > Comment.
- No `__underline__` references remain.
- Length caps (Cliff Notes <=8, Share <=2 sentences, Comment <=20 words) still appear in their existing locations. (Deeper dedupe is intentionally out of scope to keep the diff small.)

- [ ] **Step 4: Run the summarize eval**

Run: `/eval summarize`
Expected: All evals pass. If any fail, read the failure, diagnose whether the change caused it, and fix before committing.

- [ ] **Step 5: Commit**

```bash
git add skills/summarize/SKILL.md
git commit -m "fix(summarize): resolve ghostwrite-loop contradiction and drop underline"
```

---

## Task 2: Fix `ghostwrite` skill

**Files:**
- Modify: `skills/ghostwrite/SKILL.md`

- [ ] **Step 1: Resolve the Slack length contradiction**

Three different length rules currently exist for Slack:
- Line 30 (Core Voice Rules): "A 5-line Slack message becomes 1-2 sentences."
- Line 141 (Slack > Structure): "One to two paragraphs max."
- Line 156 (Slack > Length): "Under 100 words ideally. If you can say it in one paragraph, do."

Pick one canonical rule. Edit the Slack > Structure bullet to:

```
- One to three sentences. If it needs a second paragraph, it should probably be an email.
```

Edit the Slack > Length section to:

```
**Length:** Under 60 words. One to three sentences. If you can't fit it, it's an email.
```

Leave the line in Core Voice Rules ("A 5-line Slack message becomes 1-2 sentences") as-is — it now agrees with the Slack section.

- [ ] **Step 2: Reconcile the Slack bullets contradiction**

Line 34 (Core Voice Rules) says: "Exception: Slack, where flowing prose is preferred." Line 145 (Slack > Formatting) says: "NO bullet points. NO bold. NO numbered lists." These don't contradict, but the Slack line is shouty and the prompt-engineer skill flags ALL CAPS as a distrust signal.

Replace the Slack > Formatting section's first bullet:

```
- NO bullet points. NO bold. NO numbered lists. Flowing prose only
```

with:

```
- Slack is chat, not a document. Prose only — no bullets, no bold, no numbered lists, no headers.
```

- [ ] **Step 3: Replace the unverifiable "read it back as Swift" check**

Step 7 of `## How to Rewrite` says "Read it back as Swift. Does it sound like something he'd actually send?" This is unverifiable from a transcript. Replace step 7 with a concrete checklist:

```
7. Run the AI-tell checklist before delivering:
   - Any sentence over 25 words? Split it.
   - Any em dash, "excited to share", "leverage" (verb), "ecosystem", or "delve"? Cut it.
   - Does the first sentence contain the ask, news, or main point? If no, reorder.
   - Any closing engagement bait ("Let me know in the comments!")? Cut it.
```

- [ ] **Step 4: Add an explicit output format**

The skill never tells the model how to present the rewrite. Add a new section directly above `## Medium-Specific Linters`:

```
## Output Format

Return the rewritten content only. No preamble ("Here's the rewrite:"), no explanation of changes unless the user asked, no closing summary. The deliverable is the text the user can paste.
```

- [ ] **Step 5: Verify the changes by re-reading the file**

Read `skills/ghostwrite/SKILL.md` end to end. Confirm:
- Slack length appears consistently in Core Voice Rules, Slack > Structure, and Slack > Length.
- No ALL CAPS shouty rules remain.
- Step 7 is the new AI-tell checklist.
- A new `## Output Format` section exists above `## Medium-Specific Linters`.

- [ ] **Step 6: Run the ghostwrite eval**

Run: `/eval ghostwrite`
Expected: All evals pass. If any fail, diagnose and fix before committing.

- [ ] **Step 7: Commit**

```bash
git add skills/ghostwrite/SKILL.md
git commit -m "fix(ghostwrite): resolve Slack length contradiction and add output format"
```

---

## Task 3: Improve `scope` skill

**Files:**
- Modify: `skills/scope/SKILL.md`

- [ ] **Step 1: Tighten the Hard Gate to one paragraph**

The Hard Gate is currently stated twice. Replace the entire `## Hard Gate` section with:

```
## Hard Gate

Do not write any files (code, configs, specs, scaffolding, evals) until the user has explicitly approved a design. Reading existing files is fine. The spec in Step 6 is the first write, and only after Step 5 approval. "Present before persist" — show the plan, get a yes, then write.
```

- [ ] **Step 2: Add a spec template skeleton**

Step 6 says "save to `docs/specs/YYYY-MM-DD-<topic>.md`" but gives zero structure. Add a new section directly after `## Steps` (and before `## Clarifying Questions`):

```
## Spec Template

Use this skeleton for every spec. Scale each section to the project — short for simple work, longer for nuanced. Delete sections that genuinely don't apply, but default to keeping them.

​```markdown
# <Topic>

**Date:** YYYY-MM-DD
**Status:** Draft | Approved | Implemented

## Goal
One or two sentences. What are we building and why does it matter now?

## Non-Goals
What is explicitly out of scope. Prevents scope creep during implementation.

## Approach
The recommended approach in 2-5 sentences. Reference alternatives only if the trade-off matters.

## Components
Bullet list of the pieces being built or changed. One line each. Include file paths where known.

## Data / Interfaces
Any data shapes, function signatures, or external interfaces the implementer needs. Skip if trivial.

## Testing
How we'll know it works. What gets an eval, what gets a manual check, what is left unverified and why.

## Open Questions
Anything still unresolved. Empty is fine — but if you have unresolved items at write time, list them so the implementer can flag them.
​```
```

(Note: replace the `​` zero-width characters with backticks when copying. The escape is only here so the inner code fence doesn't break this plan's outer fence.)

- [ ] **Step 3: Verify the auto-commit step against project norms**

Step 6 currently says "save to `docs/specs/YYYY-MM-DD-<topic>.md` and commit." Swift's CLAUDE.md convention is generally "only commit when asked." Edit Step 6 in the `## Steps` list to:

```
6. **Write spec** -- save to `docs/specs/YYYY-MM-DD-<topic>.md` using the Spec Template below. This is the first point where files are created. Do not commit unless the user asks.
```

Also edit the matching line in `## Writing the Spec`:

```
Save the validated design to `docs/specs/YYYY-MM-DD-<topic>.md`. Do not commit unless the user asks.
```

- [ ] **Step 4: Verify the changes by re-reading the file**

Read `skills/scope/SKILL.md` end to end. Confirm:
- `## Hard Gate` is now one paragraph.
- `## Spec Template` exists between `## Steps` and `## Clarifying Questions`.
- Both Step 6 references no longer auto-commit.
- The deeper Steps-vs-sub-sections deduplication is intentionally out of scope for this pass — that's a larger restructure best done in a separate session.

- [ ] **Step 5: Run the scope eval**

Run: `/eval scope`
Expected: All evals pass. If any fail, diagnose and fix before committing.

- [ ] **Step 6: Commit**

```bash
git add skills/scope/SKILL.md
git commit -m "feat(scope): add spec template and tighten hard gate"
```

---

## Task 4: Improve `prompt-engineer` skill

**Files:**
- Modify: `skills/prompt-engineer/SKILL.md`
- Modify: `skills/prompt-engineer/references/frameworks.md`

- [ ] **Step 1: Add a trigger-symptom column to the Framework Picker**

Real user input rarely arrives pre-labeled by task category. Add a third column that maps observable symptoms to patterns. Replace the entire `## Framework Picker` table with:

```
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
```

(Note the new "Machine-parseable output" row at the bottom — this pattern exists in `frameworks.md` but was never in the picker.)

- [ ] **Step 2: Resolve the ask-vs-infer tension**

Step 3 of `## Workflow` says "Max 3 questions, one at a time." This invites asking. Replace step 3 with:

```
3. **Infer first, ask rarely.** Ask at most one question, and only when the answer would materially change the prompt. Never more than one at a time. Action over asking.
```

- [ ] **Step 3: Add missing anti-patterns**

Append the following bullets to the end of the `## Anti-Patterns` list:

```
- Negative-only instructions ("don't do X, don't do Y") with no positive target
- "Be creative" without constraints
- Unfilled placeholders shipping to the model (`{topic}` left literal)
- Mixing system and user voice inside one prompt
```

- [ ] **Step 4: Add a worked before/after example**

The skill has no concrete example. Add a new section directly above `## Delivery Format`:

```
## Worked Example

**Bad input prompt:**

​```
You are a helpful assistant. Please write a really good summary of the article below. Make it concise but thorough and make sure to cover all the important points. Thanks!
​```

**Diagnosis:** Vague role, contradiction ("concise but thorough"), no format, no length, politeness padding, no testable success criterion.

**Rewrite:**

​```
Summarize the article below in 3 bullets. Each bullet: one sentence, max 20 words, lead with the most important fact. Skip background the reader can infer from the headline.

Article: {article}
​```

**Technique:** Direct + format constraint + per-bullet length cap.
**Swap in:** `{article}`
```

(Note: replace the `​` zero-width characters with backticks when copying.)

- [ ] **Step 5: Drop the duplicate Quick Comparison table in frameworks.md**

`frameworks.md` has a `## Quick Comparison` table that overlaps the SKILL.md Framework Picker. Maintaining both invites drift. Delete the entire `## Quick Comparison` section (the heading and the table, lines roughly 7-23) from `skills/prompt-engineer/references/frameworks.md`.

- [ ] **Step 6: Trim the frameworks.md preamble**

Replace the paragraph that begins "Frameworks are not magic..." with the single sentence:

```
Pick the lightest pattern that fits. Combine only when blending clearly improves the output.
```

- [ ] **Step 7: Verify the changes by re-reading both files**

Read `skills/prompt-engineer/SKILL.md` and `skills/prompt-engineer/references/frameworks.md` end to end. Confirm:
- Framework Picker has three columns and includes the Structured Output row.
- Workflow step 3 is the new infer-first rule.
- Anti-Patterns list includes the four new bullets.
- A `## Worked Example` section exists above `## Delivery Format`.
- `frameworks.md` has no `## Quick Comparison` section.
- `frameworks.md` preamble is one sentence.

- [ ] **Step 8: Run the prompt-engineer eval**

Run: `/eval prompt-engineer`
Expected: All evals pass. If any fail, diagnose and fix before committing.

- [ ] **Step 9: Commit**

```bash
git add skills/prompt-engineer/SKILL.md skills/prompt-engineer/references/frameworks.md
git commit -m "feat(prompt-engineer): add trigger symptoms, worked example, and anti-patterns"
```

---

## Final Verification

- [ ] **Step 1: Run the full eval suite**

Run: `/eval`
Expected: All evals pass across all four skills.

- [ ] **Step 2: Confirm git state**

Run: `git log --oneline -5`
Expected: Four new commits in order — summarize fix, ghostwrite fix, scope template, prompt-engineer feature.

---

## Out of Scope (Deferred)

These came up in the review but are intentionally not in this plan. Each is a larger restructure that deserves its own scoping pass:

- **ghostwrite:** delete the duplicate `## Writing Style` section and merge into Core Voice Rules. Decide whether to load `style-samples.csv` as few-shot or delete it.
- **scope:** collapse `## Clarifying Questions`, `## Proposing Approaches`, `## Presenting the Design`, `## Working in Existing Codebases`, `## Writing the Spec` into the `## Steps` list. ~40% line reduction.
- **summarize:** dedupe length-cap statements that appear in multiple sections. Merge `## Getting the Content` into Step 1.
- **prompt-engineer:** expand or delete the one-line `## Model Tuning` section. Add Quality Bar items for failure-mode coverage and stop conditions.
