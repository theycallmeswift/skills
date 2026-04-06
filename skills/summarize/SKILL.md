---
name: summarize
description: "Use when the user wants to summarize a web page, article, blog post, PDF, document, or any other content. Triggers on requests like 'summarize this', 'summarize this page', 'tl;dr', 'what's this about', 'give me the key points', 'cliff notes', or any request to distill content into a quick overview. Also trigger when the user shares a URL, attaches a file (PDF, DOCX, etc.), or pastes content and wants the gist. Trigger on phrases like 'is this worth reading?' or 'what does this say?'. If the user is looking at a web page or has a document open and asks for a summary or reaction, use this skill."
---

# Summarize

Produce a concise, skimmable summary of any content -- web pages, PDFs, documents, or pasted text. The goal is to help the user decide whether to read the full thing, and give them a ready-to-share message.

## Getting the Content

If the user provides a URL, file, or content, use that. If they just say "summarize this" without context, ask what they'd like summarized. Check for:

1. **URL in the message** -- fetch and read it
2. **File path or attachment** -- read the file directly (PDF, DOCX, TXT, etc.)
3. **Active browser tab** -- if browser tools are available, read the current page
4. **Neither** -- ask the user: "What would you like me to summarize? Share a URL, drop a file, or paste the content."

## Steps

1. **Fetch and read** the content. For a single URL, use `scrape_as_markdown` from the brightdata MCP. For multiple URLs in one request, use `scrape_batch`. For local files (PDFs, DOCX, etc.), use Read directly. If the brightdata MCP is unavailable, fail loudly with a message pointing the user at `BRIGHTDATA_API_TOKEN`. Do not fall back to any other fetch tool.
2. **Write the title, TL;DR, and Cliff Notes** (see Output Format below)
3. **Identify the most interesting takeaway** -- the one thing that would make someone want to click the link. Distill it into a sentence or two of raw content (not yet in anyone's voice).
4. **Hand that takeaway to the `ghostwrite` skill** to rewrite as a Slack message. The ghostwrite skill handles voice and tone.
5. **Identify a discussion-worthy angle** -- something specific from the content that invites a real reply. Not a summary, but a point you'd react to as a builder.
6. **Hand that angle to the `ghostwrite` skill** to rewrite as a forum comment.
7. **Present the final output**: title, TL;DR, Cliff Notes, Share, and Comment sections.

## Output Format

Follow this structure exactly, including the heading levels. No horizontal rules between sections.

# [Article Title]

The title of the content as an H1. If a URL is available, include a clickable link to the source below the title. For documents without a URL, use the document title or filename.

## TL;DR

1-2 sentences max. Lead with the single most important takeaway. Be blunt and direct -- write it like a headline expansion, not an abstract. If the reader sees nothing else, they should know what happened and why it matters.

Render the TL;DR text as normal body-sized paragraph text, not as a heading or bold block.

## Cliff Notes

- A bulleted list of the key points, findings, arguments, or events from the content.
- Each bullet: **1-2 sentences max**. No long paragraphs.
- Use **bold** for names, key terms, or critical facts so they pop when skimming.
- Use *italics* for context, nuance, or editorial framing that helps interpretation.
- Aim for **5-8 bullets** (fewer if the content is short; never pad with filler).
- Order bullets by importance, not by their sequence in the source.

## Share

Display the ghostwritten message and URL in a code fence, ready to paste. Keep it to 1-2 short sentences max, then the bare URL. This should feel like a quick hot take you'd fire off in a channel, not a mini-summary. If it's longer than two lines of text before the URL, cut it down.

Use Slack markdown inside the code fence: `*bold*` uses single asterisks, `_italic_` uses single underscores. Do NOT use standard markdown.

The final result should look like this:

```
One punchy reaction sentence here
https://example.com/the-article-url
```

## Comment

A ready-to-paste reply for the post itself, or a Reddit/Hacker News discussion thread. Run it through the `ghostwrite` skill, then display in a code fence.

Write like a veteran developer leaving a quick reply on a forum. Zero filler. Zero PR speak. No "email voice."

- **Hard limit: 20 words or fewer.** Count them. If you're over 20, cut until you're under. One sentence is ideal. Two very short sentences if absolutely necessary.
- Do NOT summarize the article back to the author. Dive straight into your point.
- **Authentic voice**: Energetic but blunt, plain-spoken, and builder-focused.
- **Sound human, not like a bot.** Real developers don't end every comment with a neatly packaged question. Mix it up: share a strong opinion, a quick personal experience, a pushback, or a "yeah, but..." counterpoint. A question is fine sometimes, but it should feel like genuine curiosity, not an engagement prompt. Vary the structure across summaries so they don't all follow the same formula.

```
Comment text here
```

## Style Rules

- Use **bold**, *italics*, and __underline__ strategically to draw the eye, but don't overdo it.
- Shorter is always better. Trim ruthlessly.
- Do not editorialize or inject opinions in the TL;DR or Cliff Notes. Stick to what the content actually says.
- Do not reproduce large verbatim passages from the source. Use your own concise wording.
- No em dashes. Use commas, periods, or restructure the sentence instead.
