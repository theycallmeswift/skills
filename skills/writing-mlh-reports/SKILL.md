---
name: writing-mlh-reports
description: "Use when the user wants a shareable report, write-up or data story built from the MLH ecosystem (Major League Hacking, DEV/dev.to, MLH programs and partners): partner developer reports, program or fellowship outcomes, event recaps, impact or B-Corp reports, investor updates, trend reports, internal retros. Covers asks like \"generate a Q3 developer report for GitHub\", \"write up how the PE Fellowship did this year\", \"make our 2026 impact report\", \"pull together an investor growth update\", \"what are devs doing with coding agents? write it up for DEV\". Use it even when the ask names no format: a report from MLH data is this skill. Don't use for a single number or quick query answered in chat, a slide deck (google-slides), a one-line fix to an existing report, or documents with no MLH data behind them."
---

# Writing MLH reports

Turn MLH ecosystem data into a report one named reader can act on, delivered as a shareable doc (use the `docs` skill when you have it). Success: the reader gets the point from headings alone, every number traces to a source, and nothing in it is wrong for that audience to see. Most failed drafts get the data right and the story wrong. Steps 1, 2 and 5 carry the weight.

You coordinate; subagents do the reading. Keep raw data out of your own context: each subagent writes to the report's working folder and returns a short summary.

## 1. Scope: audience and goal first

Read anything the user attached before anything else. Attachments are usually the real brief, and they often show the subject is not what the one-line ask implies (a "developer report" for a talent-program partner is really a program-outcomes report).

Settle these, asking in one round about whatever you can't infer:

- **Audience:** who reads it (a partner, the MLH team, leadership, investors, the public) and what they may see.
- **Goal:** what the reader should know, feel or decide afterward. Every section must serve it.
- **Subject and spine:** what the report is about, and the comparison that carries it (partner vs competitors, program vs the wider field, this year vs last, target vs actual).
- **Period and baseline.**
- **What's new:** firsts this period. Users often forget to mention them.
- **Where the data lives,** including systems not yet connected.
- **Deadline:** check the calendar for a meeting the report should land before.

Then set the audience rules for this report: tone, whether recommendations are allowed, what's confidential, and the required notice line. Write them into the brief. Defaults:

| Audience | Tone | Recommendations | Never include |
|---|---|---|---|
| Partner | Independent, data-led, never a pitch | No: findings and what to track | Other partners' data, pricing, deal terms, budgets, renewal status, internal staffing |
| MLH internal | Candid, positive where earned | Yes: specific and bold | Individuals' personal data |
| Investor | Confident, evidence-led, no hype | Yes: what's next | Partner deal terms, individuals' data |
| Public | Polished | Light | Anything confidential |

Start `brief.md` in the working folder: audience, goal, spine, period, audience rules, and every decision the user makes from here on. Every subagent reads it.

## 2. Outline gate

Before any drafting, get the user to approve a story outline:

- the one-line arc (the verdict you expect, to be confirmed by data)
- claim-first H2s in reading order, each with the evidence and the visual planned for it
- the sources each section depends on

Order sections by the story, not by data source. Then create the doc with a pending block per section and share the link, so the user can watch it fill.

## 3. Gather

Preflight every connector you'll need with one test query. If one returns a re-auth link, send the user all the links and stop until they're fixed.

Dispatch one subagent per source, in parallel. Each reads `brief.md`, writes `research/<source>.md` with every figure, its exact source (table and query, file, tab and range, URL, or permalink) and the exact question wording for survey items, then returns 300 words or fewer.

[references/sources.md](references/sources.md) maps MLH's main sources and their known traps. Read it before writing the gather briefs. It is a starting map, not a fence: look for other systems that hold what the goal needs (finance, CRM, ads, analytics) and use them.

Re-trace any figure from a deck, doc or Slack post to the raw source before reusing it. Decks drift from their data.

## 4. Reconcile

Build one table: each metric, every value found, the source of each, the chosen figure, and why. When sources disagree, the closer to raw data wins (warehouse > raw sheets and forms > dashboards > decks and docs > Slack and email > meeting transcripts > memory).

Send the user every conflict that changes a headline in one batch, not one at a time mid-draft. Log their decisions in `brief.md`. Keep conflicting deck figures as a QA list for delivery.

## 5. Plan the insights

An analyst subagent reads `brief.md` and `research/`, then writes `plan.md`: 8–12 insights ranked by the goal, and 4–7 visual specs with exact rows. Look for:

- **Measures that disagree** (self-ratings vs assessments, usage vs trust). This is often the lead finding.
- **A true baseline:** the same question asked of a comparable group.
- **Confounds:** test each headline against the obvious one and show the adjusted figure beside it (with vs without partner-sponsored events).
- **Leads and gaps:** where the subject leads and where it trails, as far as the reader's decision needs.
- **Segments:** split next-gen devs vs professionals where the data allows; never label an all-respondent figure as a segment.
- **The user's framing:** keep the point, but make it as precise as the evidence.
- **Firsts.**

Gaps in MLH's own data pipeline are not findings about the subject. Build findings from what is measured and put the gap in Methodology.

## 6. Draft

Draft one section per call, prose then visuals, following [references/writing.md](references/writing.md). Read it before the first section. It also holds the maintained intro and notice lines.

## 7. Review

Once the structure is locked:

1. **Fact-checker** (fresh subagent): traces every number to `research/` or an opened URL, checks segment labels and question wording, and applies clear fixes.
2. **Critic** (fresh subagent, briefed as the target reader): what would they doubt, skip, or forward? What is the strongest finding, and is it leading? Lists judgment calls; edits nothing.
3. **Editor** (one subagent, one pass): applies the critique, voice and skimmability. Numbers stay unchanged.

Only one agent edits the doc at a time. Route the user's comments through the active editor.

## 8. Deliver

Send the doc link, then:

- **Open items:** small samples, provisional periods, unverified figures, anything the user must confirm.
- **QA list:** source figures (decks, dashboards) that didn't reproduce.
- **Email draft** to the external readers, last, once the doc is final: the link, three balanced findings, and the notice line.

Post a one-line status at each gate: scope, outline, reconcile, draft, review, delivery. Build one version; offer variants only after.
