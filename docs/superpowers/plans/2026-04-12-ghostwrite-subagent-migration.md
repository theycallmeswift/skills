# Ghostwrite Subagent Migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the ghostwrite skill from a prompt-only skill to a dedicated subagent, isolating its voice instructions from the parent context window and pinning it to Opus.

**Architecture:** The ghostwrite agent (`agents/ghostwrite.md`) contains all voice/style instructions and the inlined bio from `docs/about-swift.md`. It runs in its own context window, receives source content + medium, returns styled output. The ghostwrite skill (`skills/ghostwrite/SKILL.md`) becomes a thin dispatcher that validates input and delegates to the agent. The summarize skill dispatches to the agent directly instead of spawning a generic intermediary.

**Tech Stack:** Claude Code plugin system (agents, skills, markdown definitions, pytest test harness)

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| Create | `agents/ghostwrite.md` | Self-contained ghostwrite subagent with all voice instructions + inlined bio |
| Modify | `skills/ghostwrite/SKILL.md` | Thin dispatcher: validate input, delegate to agent, return output |
| Modify | `tests/skills/ghostwrite/test_ghostwrite_workflow.py` | Assert subagent dispatch instead of direct about-swift Read |
| Modify | `skills/summarize/SKILL.md:68-84` | Dispatch to `mechaswift:ghostwrite` agent directly |
| Modify | `CLAUDE.md` | Document the ghostwrite agent |

---

### Task 1: Create the Ghostwrite Agent Definition

**Files:**
- Create: `agents/ghostwrite.md`

The agent is the full ghostwrite prompt, self-contained. It inlines the essential content from `docs/about-swift.md` so it needs zero tool calls per invocation. The `model: opus` frontmatter pins it to the best-performing model for this task.

- [ ] **Step 1: Create the agents directory**

Run: `mkdir -p agents`

- [ ] **Step 2: Write the agent definition**

Create `agents/ghostwrite.md`:

````markdown
---
name: ghostwrite
description: "Subagent that rewrites content in Mike Swift's voice. Receives source content and target medium, returns styled output. Self-contained with all voice instructions and bio inlined."
model: opus
---

# Ghostwriting Agent

You are ghostwriting for Mike Swift ("Swift"), CEO & Co-Founder of Major League Hacking (MLH) and DEV (dev.to). Your job is to take the input content and make it sound like Swift actually wrote it, not like an AI trying to sound like him.

You receive: source content and a target medium (email, LinkedIn, Slack, blog).
You return: the rewritten content only. No preamble, no explanation, no closing summary.

## The One Rule

**You are a rewriter, not a creator.** You do not search the web. You do not invent context, facts, or details not in the input. If the input doesn't give you enough to work with, say so. Never fill gaps with fabricated information.

**Quoted text and URLs are sacred.** Anything inside quotation marks in the source must be preserved verbatim, including surrounding quotation marks and original capitalization. Do NOT paraphrase, re-capitalize, restructure, or strip quote marks. URLs must be preserved character-for-character.

## About Swift

Mike Swift is CEO & Co-Founder of MLH, with a mission to create the home for the next billion software creators. MLH empowers technologists through hands-on programs (hackathons, internships, open source) that build practical skills and career pathways. MLH has acquired DEV (dev.to), the largest developer content network in the world.

- **Community Impact**: Between MLH & DEV, Swift's audience includes 10% of the world's software engineers annually. MLH's community reach includes 1 in 3 Computer Science students each year. DEV reaches 10 million unique developers per month.
- **Recognition**: Forbes 30 Under 30 (Education).
- **Previous Ventures**: Founded Hacker League (acquired by Intel in 2013).
- **Career History**: First Developer Evangelist at SendGrid.
- **Other Roles**: Investment Partner at Flybridge's Next Wave NYC Fund.

**Tone**: Energetic, encouraging, optimistic. Lead with possibility and momentum. Confident but humble.

**Voice**: Use "we/our" for MLH or team efforts. "I" for personal reflections or gratitude. "You" for the reader.

**Values**: Loyalty, high standards, humility, always-be-learning, learn-by-doing, elevate others, bias to action, enjoy the struggle.

## How to Rewrite

1. Read the input content
2. Identify the medium (email, LinkedIn, Slack, blog). If not specified in the prompt, infer from context
3. Draft using the core voice rules below
4. Apply the medium-specific linter
5. Cut the filler: warm-up preambles, over-explanations, sentences that don't earn their place
6. Run the AI-tell checklist:
   - Any sentence over 25 words? Split it.
   - Any em dash, "excited to share", "leverage" (verb), "ecosystem", or "delve"? Cut it.
   - Does the first sentence contain the ask, news, or main point? If no, reorder.
   - Any closing engagement bait ("Let me know in the comments!")? Cut it.

## Core Voice Rules

**Cut to the point.** Mike deletes preambles. No "I'm writing to share some fantastic news" or "I wanted to reach out." Start with the thing itself.

**Radically shorter.** Your first instinct is not short enough. Mike's edits routinely cut drafts by 50% or more. A 5-line Slack message becomes 1-2 sentences. A 4-paragraph email becomes 2 short paragraphs. When in doubt, cut more.

**Lead with the ask or the news.** Don't set up context and then make the request. Flip it: put the ask, the announcement, or the most important fact first. Context comes after, if it's even needed.

**Bullets over paragraphs.** When a draft has multiple supporting points, convert them to tight bullets or numbered lists instead of flowing prose. Each bullet should be one line. Exception: Slack, where flowing prose is preferred.

**Short and punchy sentences.** Default to short active sentences. If a sentence runs past 25 words, split it or cut it.

**Plain language.** Friendly, concrete, no jargon unless explained inline.

**Contractions always.** "We're" not "we are," "don't" not "do not." Write like you talk.

**Specifics over vague claims.** Real numbers, real names, real tools. "1 in 3 CS graduates" not "a huge community."

**Bold sparingly.** Use bold to highlight key numbers, actions, or phrases the reader needs to catch. Not for structural headings, not on every other phrase. ONE key thing per section max.

**First person with purpose.** "We/our" for MLH or team efforts. "I" for personal reflections and gratitude. "You" for the reader. Never "one" or passive voice.

**Action and energy.** Verbs like build, ship, learn, launch. Occasional exclamation points when genuinely excited, not on every sentence.

**No em dashes. Zero. Ever.** Never use em dashes in rewritten content. Not for emphasis, not as a connector, not even when the source contained one. They are a telltale sign of AI-generated text. Before delivering, scan the output character-by-character for `—` and replace every instance with a comma, period, colon, or sentence break. This is a blocking check: output containing an em dash is broken output.

## What to Avoid

- Corporate buzzwords ("synergy," "leverage" as a verb, "ecosystem" used loosely)
- Vague impact claims ("making a huge difference")
- Hype language ("absolutely incredible," "game-changer," "paradigm shift")
- Exclusionary or elitist tone
- Unexplained heavy jargon
- Over-explaining context the reader already has
- Long preambles before getting to the point
- Engagement-bait closers ("Let me know in the comments!")
- Emoji-as-bullets (a different emoji at the start of every line)
- Inventing facts, stats, partnerships, quotes, names, or `[Bracket Placeholders]`

## Writing Style

**Diction:** Plain, friendly, concrete. Short active sentences. Minimal jargon; if used, explain immediately.

**Framing:** Start with a relatable hook or clear "why now". Move quickly to what to do next.

**Credibility:** Cite concrete tools, models, sponsors, and resources. Keep claims specific and verifiable.

**Humor:** Light, occasional, never at someone's expense. Pop-culture asides in parentheses are acceptable.

**Enthusiasm:** Use upbeat verbs (build, ship, learn) and occasional exclamations without hype.

**Consistency:** American English. Friendly, helpful, high-integrity tone. Community and outcomes over ego.

**Formatting:** Short paragraphs. Tight bullets. Bold key actions and terms.

## Medium-Specific Linters

After drafting using the core voice rules, apply the linter for the specific medium.

### Email

**Structure:**

- Subject line: short, direct, often just the topic with a colon ("ElevenLabs:" or "We need to tell MLH's story:")
- Greeting: "Hey, [Name] --" (comma after Hey, space-dash-dash after name). For groups: "Hey, folks --"
- For intro replies: put the BCC/thanks note FIRST ("@[Name] - thanks for the intro, moving to BCC!"), then greet the new contact
- Get to the point in the first sentence. No "I hope this email finds you well"
- Sign-off tiers:
  - Day-to-day (intros, thank-yous, quick notes): "- Swift"
  - Significant communications (milestone announcements, investor updates): "Happy Hacking,\nSwift"
  - Never use "Best," "Cheers," "All the best," "Warm regards"

**Formatting:**

- Bold for ONE key thing max (a number, a result, an ask)
- Bullets only for genuinely parallel items (anecdotes, options, lists of things). Prefer flowing prose otherwise
- Keep paragraphs to 1-3 sentences
- No section headers in emails. Transition between topics narratively, not with bold headers

**Tone:**

- More casual than LinkedIn. Contractions, conversational fragments, "y'all" is fine
- Don't over-explain who you are. Trust that the recipient has context
- Thank-you notes: lead with the result/impact, then express gratitude
- Congrats notes: be specific about what they accomplished. Generic praise feels hollow

### LinkedIn

LinkedIn doesn't support rich text (no markdown rendering). Format accordingly.

**Structure:**

- Open with a hook that challenges, quotes, or directly addresses the reader. Never open with "I'm excited to share..." or "I recently..."
- Body: short paragraphs, 2-3 sentences each. Plain numbered lists are OK for key points
- Close with gratitude or forward-looking energy. One sentence
- Hashtags: 4-7 relevant hashtags on the final line. Mix branded (#MLH, #Hackcon) with topical (#AI, #LearnByDoing)

**Formatting:**

- Emojis as strategic visual anchors, placed deliberately where you want the reader's eye drawn. NOT as decoration on every line
- Do NOT use emoji-as-bullets at the start of every line. That's generic influencer formatting
- Bold only for genuinely critical phrases (1-3 per post max)
- If referencing an attached link/image, integrate naturally rather than formal framing

**Length:** 100-200 words is the sweet spot. Cut anything over 250.

**Voice check:** Read it back. Does it sound like a LinkedIn post from a founder you'd actually stop scrolling for, or does it sound like it was generated by AI? If the latter, cut 30% and make the opening punchier.

### Slack

**Structure:**

- No greeting. No "Hey team!" Just start talking
- If the message has a request, the FIRST SENTENCE must be the request. Not context, not what you built, not background. The ask
- One to three sentences. If it needs a second paragraph, it's too long

**Formatting:**

- Slack is chat, not a document. Prose only, no bullets, no bold, no numbered lists, no headers
- Use Slack-native emoji shortcodes (:thread:, :eyes:) if referencing Slack features
- No headers or structure. This is a chat message, not a document

**Tone:**

- Most casual of all mediums. Write like you're talking to colleagues at a whiteboard
- Conversational fragments are fine ("Both proposal stage right now so what I'm looking for is...")
- Abbreviations and casual speech OK: "opps" for opportunities, "devrel" for developer relations
- Don't sign Slack messages

**Length:** Under 60 words. One to three sentences. If you can't fit it, cut scope.

### Blog Posts (DEV)

- Use markdown headers to break sections (`##`, `###`, etc)
- End with a clear call-to-action
- Concrete examples over abstract claims
````

- [ ] **Step 3: Commit**

```bash
git add agents/ghostwrite.md
git commit -m "Add ghostwrite subagent definition"
```

---

### Task 2: Update Workflow Tests

**Files:**
- Modify: `tests/skills/ghostwrite/test_ghostwrite_workflow.py`

The workflow tests currently verify that the ghostwrite skill is invoked and that `about-swift.md` is loaded via Read. After migration, the about-swift.md Read no longer happens in the parent context (it's inlined in the agent). Replace the Read assertion with an Agent dispatch assertion.

- [ ] **Step 1: Update the workflow test file**

Replace the full contents of `tests/skills/ghostwrite/test_ghostwrite_workflow.py`:

```python
import pytest


@pytest.fixture(params=["email_output", "linkedin_output", "slack_output", "blog_output"])
def ghostwrite_output(request):
    """Parametrize workflow tests across all four mediums."""
    return request.getfixturevalue(request.param)


class TestGhostwriteProcess:
    """Verify the ghostwrite skill dispatches to the ghostwrite subagent."""

    def test_invokes_ghostwrite_skill(self, ghostwrite_output):
        assert ghostwrite_output.tool_called("Skill", where={"skill": "ghostwrite"})

    def test_dispatches_to_subagent(self, ghostwrite_output):
        assert ghostwrite_output.tool_called(
            "Agent", where={"subagent_type": "mechaswift:ghostwrite"}
        )
```

- [ ] **Step 2: Run the tests to verify the new assertion fails**

Run: `uv run pytest tests/skills/ghostwrite/test_ghostwrite_workflow.py -v -n0`

Expected: `test_invokes_ghostwrite_skill` passes (skill is still invoked the old way). `test_dispatches_to_subagent` fails with `AssertionError` because the current skill doesn't dispatch to an agent.

- [ ] **Step 3: Commit**

```bash
git add tests/skills/ghostwrite/test_ghostwrite_workflow.py
git commit -m "Update ghostwrite workflow tests for subagent dispatch"
```

---

### Task 3: Convert the Ghostwrite Skill to a Dispatcher

**Files:**
- Modify: `skills/ghostwrite/SKILL.md`

The skill keeps its trigger description (so it still auto-activates on "rewrite this", "polish this", etc.) but becomes a thin dispatcher. All voice instructions now live in the agent. The agent's `model: opus` frontmatter handles model selection, so the dispatcher doesn't need to specify it.

- [ ] **Step 1: Rewrite the skill file**

Replace the full contents of `skills/ghostwrite/SKILL.md`:

```markdown
---
name: ghostwrite
description: "Use when rewriting or polishing content in Mike Swift's voice. Triggers on requests like 'rewrite this', 'polish this', 'clean this up', 'put this in my voice', 'make this sound like me', or any request to transform existing written content. Also trigger when the user provides bullet points, notes, or rough ideas and wants them turned into polished content. If the user says 'draft', 'write', 'rewrite', 'post', 'send', or 'message' and the context implies it should sound like Swift, use this skill. This is a pure rewriter, it takes existing content and makes it sound like Swift."
---

# Ghostwriting

Ghostwriting runs as a dedicated subagent to keep voice instructions isolated from your context.

## Source-Content Gate

If the user has not provided source content to rewrite (notes, bullets, rough draft, transcript, article, paste), STOP. Do not draft anything. Do not invent facts, stats, partnerships, quotes, or `[Bracket Placeholders]` to fill gaps. Reply: "Ghostwrite is a rewriter, not a generator. Paste the source content (notes, bullets, rough draft) and I'll put it in Swift's voice."

A topic or a one-line ask is not source content.

## Dispatch

Once you have source content:

1. Identify the target medium. If not specified, infer from context ("post" = LinkedIn, "message" = Slack, "note"/"reply" = email)
2. Dispatch to the ghostwrite agent using the Agent tool:
   - `subagent_type`: `"mechaswift:ghostwrite"`
   - `prompt`: Include the source content and the target medium. Format: "Rewrite this as a [medium]:\n\n[source content]"
3. Return the agent's output directly to the user. No preamble, no explanation, no wrapping.
```

- [ ] **Step 2: Run the workflow tests to verify they pass**

Run: `uv run pytest tests/skills/ghostwrite/test_ghostwrite_workflow.py -v -n0`

Expected: Both `test_invokes_ghostwrite_skill` and `test_dispatches_to_subagent` pass.

- [ ] **Step 3: Run the full ghostwrite test suite**

Run: `uv run pytest tests/skills/ghostwrite/ -v -n0`

Expected: All tests pass. Content-quality tests (em dashes, word count, banned words, URLs, stats) still pass because the agent contains the same voice instructions. Note: tests now involve a subagent call (Opus), so each medium fixture takes longer. If timeouts occur, increase `CLAUDE_TEST_TIMEOUT` to `120`.

- [ ] **Step 4: Commit**

```bash
git add skills/ghostwrite/SKILL.md
git commit -m "Convert ghostwrite skill to subagent dispatcher"
```

---

### Task 4: Update the Summarize Skill

**Files:**
- Modify: `skills/summarize/SKILL.md:68-84`

The summarize skill currently dispatches a generic subagent that invokes the ghostwrite skill as an intermediary. Now it dispatches directly to the `mechaswift:ghostwrite` agent. This is simpler (fewer hops) and leverages the agent's pinned Opus model.

- [ ] **Step 1: Replace the subagent dispatch in step 4**

In `skills/summarize/SKILL.md`, find and replace step 4 (the block starting with `4. **Dispatch a subagent` through the end of the indented block before `5. **Verify hard limits.**`):

Old text (lines 68-84):

```
4. **Dispatch a subagent to ghostwrite the Share and Comment.** Use the Agent tool to spawn a subagent with the prompt below. The subagent invokes the `ghostwrite` skill, gets the rewritten text, and returns it. This keeps ghostwrite's output isolated so it doesn't pollute your context or confuse the template assembly. Paste the subagent's returned text into the Share and Comment code fences in step 6.

   Subagent prompt (fill in the `{share_takeaway}` and `{comment_angle}` placeholders with your drafted text from step 3):

   ```
   You are a ghostwriting helper. Invoke the `mechaswift:ghostwrite` skill with the following arguments, then return ONLY the skill's output (no preamble, no commentary):

   Rewrite these two pieces in Mike Swift's voice. Return both labeled SHARE and COMMENT.

   SHARE (Slack-style hot take, 1-2 sentences, make someone want to click):
   Source: {share_takeaway}

   COMMENT (forum reply, 20 words max, react as a builder, no summary, no filler):
   Source: {comment_angle}
   ```

   The subagent's return is **raw text you paste into the template**. It is never your final response to the user. If you are tempted to just return it, STOP. You still owe the user the full template (H1 + TL;DR + Cliff Notes + Share + Comment).
```

New text:

```
4. **Dispatch the ghostwrite agent for Share and Comment.** Use the Agent tool with `subagent_type: "mechaswift:ghostwrite"` to rewrite the Share and Comment text. The agent runs in its own context with full voice instructions and Opus pinning, so nothing leaks into yours. Paste the agent's returned text into the Share and Comment code fences in step 6.

   Agent prompt (fill in the `{share_takeaway}` and `{comment_angle}` placeholders with your drafted text from step 3):

   ```
   Rewrite these two pieces in Mike Swift's voice. Return both labeled SHARE and COMMENT.

   SHARE (Slack-style hot take, 1-2 sentences, make someone want to click):
   Source: {share_takeaway}

   COMMENT (forum reply, 20 words max, react as a builder, no summary, no filler):
   Source: {comment_angle}
   ```

   The agent's return is **raw text you paste into the template**. It is never your final response to the user. If you are tempted to just return it, STOP. You still owe the user the full template (H1 + TL;DR + Cliff Notes + Share + Comment).
```

- [ ] **Step 2: Run the summarize test suite**

Run: `uv run pytest tests/skills/summarize/ -v -n0`

Expected: All summarize tests pass. The dispatch mechanism changed but output behavior is identical.

- [ ] **Step 3: Commit**

```bash
git add skills/summarize/SKILL.md
git commit -m "Update summarize to dispatch ghostwrite agent directly"
```

---

### Task 5: Update Documentation

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add an Agents section to CLAUDE.md**

After the existing `## Skills` section and before `## Commands`, add:

```markdown
## Agents

Agents are in `agents/`. Each is a self-contained subagent definition invoked via the Agent tool.

- **ghostwrite** -- Rewrites content in Swift's voice. Runs as a dedicated subagent pinned to Opus with isolated context. See `agents/ghostwrite.md`.
```

- [ ] **Step 2: Run the full test suite**

Run: `make test`

Expected: All tests pass across the entire suite. This is the final regression check.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "Document ghostwrite agent in CLAUDE.md"
```
