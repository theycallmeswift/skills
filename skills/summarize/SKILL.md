---
name: summarize
description: "Use when the user wants to summarize a web page, article, blog post, PDF, document, or any other content. Triggers on requests like 'summarize this', 'summarize this page', 'tl;dr', 'what's this about', 'give me the key points', 'cliff notes', or any request to distill content into a quick overview. Also trigger when the user shares a URL, attaches a file (PDF, DOCX, etc.), or pastes content and wants the gist. Trigger on phrases like 'is this worth reading?' or 'what does this say?'. If the user is looking at a web page or has a document open and asks for a summary or reaction, use this skill."
---

# Summarize

Produce a concise, skimmable summary of any content -- web pages, PDFs, documents, or pasted text. The goal is to help the user decide whether to read the full thing, and give them a ready-to-share message.

## The final response rule (read this first)

Your final assistant message to the user is **only the filled-in template below**. Nothing before it, nothing after it.

- The very first character of your final message is `#` (the H1 title).
- No preamble. Not "Here's the summary:", not "Summary:", not "Lint clean.", not "---", not a recap of what you did. Zero.
- No postscript. No "Let me know if you want me to adjust..." at the bottom.
- Ghostwrite output is **internal scratch**, not your final message. When you invoke ghostwrite, its return value is text you paste INTO the `## Share` and `## Comment` code fences of the template — never the whole response.
- If you are about to send a message that does not start with `# `, stop and rewrite it. This is the most common way this skill fails.

## Getting the Content

If the user provides a URL, file, or content, use that. If they just say "summarize this" without context, ask what they'd like summarized. Check for:

1. **URL in the message** -- fetch and read it
2. **File path or attachment** -- read the file directly (PDF, DOCX, TXT, etc.)
3. **Active browser tab** -- if browser tools are available, read the current page
4. **Neither** -- ask the user: "What would you like me to summarize? Share a URL, drop a file, or paste the content."

## The final response template

Every summary the user sees is a **single assistant message** that fills in this exact template. The section headings are literal markdown and must appear verbatim. Do not substitute bold labels (`**SLACK**`, `**COMMENT:**`, `**Slack share message:**`, etc.) for any heading. Do not skip any of the five sections.

```
# <H1 title per Input Types below>

## TL;DR

<1-2 sentences of plain paragraph text>

## Cliff Notes

- <bullet 1>
- <bullet 2>
- <as many bullets as the source supports, up to 8 max>

## Share

` ` `
<ghostwritten hot-take sentence>
<bare source URL on its own line, OR omit this line for file/pasted input>
` ` `

## Comment

` ` `
<ghostwritten forum comment, 20 words or fewer>
` ` `
```

(The ` ` ` shown above represent real triple-backtick code fences in the actual response.)

## Steps

1. **Fetch and read** the content. For a single URL, use `scrape_as_markdown` from the brightdata MCP. For multiple URLs in one request, use `scrape_batch`. For local files (PDFs, DOCX, etc.), use Read directly. If the brightdata MCP is unavailable, fail loudly with a message pointing the user at `BRIGHTDATA_API_TOKEN`. Do not fall back to any other fetch tool.
2. **Draft Title, TL;DR, and Cliff Notes internally** from the source content. These are YOUR words, not ghostwrite's.
3. **Identify the Share takeaway** (one punchy sentence that would make someone click) and the **Comment angle** (something specific to react to as a builder).
4. **Invoke the `ghostwrite` skill exactly once** with both the Share takeaway and the Comment angle. Ask it to return two rewrites: a Slack-style share message and a short forum comment. Ghostwrite's return value is **raw text you paste into the Share and Comment code fences of the template in step 6**. It is never your final response to the user. If ghostwrite gives you text and you are tempted to just return it, STOP — you still owe the user the full template (H1 + TL;DR + Cliff Notes + Share + Comment).
5. **Verify hard limits.** Count, do not estimate.
   - **Cliff Notes**: up to 8 bullets. Fewer is fine — if the source only supports 3, emit 3. Never pad to hit a number.
   - **Share**: 1-2 sentences. If more, cut.
   - **Comment**: 20 words or fewer inside the code fence. If more, trim yourself (do not re-invoke ghostwrite).
6. **Write the full template above as a single markdown message.** All five sections. Literal `## TL;DR`, `## Cliff Notes`, `## Share`, `## Comment` headings. No bold-label substitutes.
7. **Self-check before presenting.** Before delivering, verify: starts with H1 title, has summary paragraph before bullets, bullet count 1-8 (never pad), has Share and Comment blocks, no em dashes, no narration prefixes (Let me, Now I, I'll draft, etc.). Fix any issues before presenting.
8. **Deliver the template directly.** Your next assistant message is the filled-in template and nothing else. First character is the `#` of the H1. Last character is the closing backtick of the Comment code fence. No "Lint clean.", no "Here's the summary:", no "---", no trailing "Let me know...".

## Input types

**URL input** (user pasted a link, or asked you to summarize a web page):
- H1 uses the article title as the link text with the source URL, e.g. `# [Article Title](https://example.com/post)`.
- Share fence ends with the bare source URL on its own line below the hot-take sentence.

**File input** (user attached or named a PDF, DOCX, or other local file):
- H1 uses the document title (from the file's own title/metadata) or the filename if no title exists. No markdown link.
- Share fence contains only the hot-take sentence. **Do NOT include a URL line** -- there is no URL to share.

**Pasted text input** (user pasted raw content directly in the message, no file, no URL):
- H1 uses a short descriptive title you infer from the pasted content. No markdown link.
- Share fence contains only the hot-take sentence. **Do NOT include a URL line**.

In all three cases, the `## Share` and `## Comment` section headings are still emitted exactly as `## Share` and `## Comment`.

## Section guidance

**H1 title** — single line starting with `# `. Format depends on input type (see Input types above).

**TL;DR** — 1-2 sentences max as plain paragraph text (NOT a heading, NOT a bold block). Lead with the single most important takeaway. Write it like a headline expansion, not an abstract. If the reader sees nothing else, they should know what happened and why it matters.

**Cliff Notes** — a bulleted list of the key points, findings, arguments, or events:
- Each bullet: 1-2 sentences max. No long paragraphs.
- Use **bold** for names, key terms, or critical facts so they pop when skimming.
- Use *italics* for context, nuance, or editorial framing that helps interpretation.
- Up to 8 bullets, ordered by importance (not source order). Fewer is fine.
- Never pad with filler. If the source only supports 3 bullets, emit 3.

**Share** — a code fence containing the ghostwritten Slack-style hot take. Use Slack markdown inside the fence: `*bold*` single asterisks, `_italic_` single underscores. For URL inputs, the last line inside the fence is the bare source URL on its own line. For file/pasted inputs, omit the URL line entirely.

**Comment** — a code fence containing the ghostwritten forum comment. Hard limit: 20 words or fewer. Zero filler, zero PR speak, no "email voice." Write like a veteran developer leaving a quick reply on a forum. Don't summarize the article back to the author — dive straight into your point. Sound human, not like a bot. Vary the structure across summaries so they don't all follow the same formula: strong opinion, quick personal experience, pushback, or "yeah, but..." counterpoint. A question is fine if it feels like genuine curiosity.

## Style Rules

- Use **bold** and *italics* strategically to draw the eye, but don't overdo it. Bold and italic conventions are defined per-section above; do not introduce new emphasis styles.
- Shorter is always better. Trim ruthlessly.
- Do not editorialize or inject opinions in the TL;DR or Cliff Notes. Stick to what the content actually says.
- Do not reproduce large verbatim passages from the source. Use your own concise wording.
- No em dashes. Use commas, periods, or restructure the sentence instead.
