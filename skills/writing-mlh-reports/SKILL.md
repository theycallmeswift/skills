---
name: writing-mlh-reports
description: "Use when the user wants a shareable report, write-up or data story built from the MLH ecosystem (Major League Hacking, DEV/dev.to, MLH programs and partners): partner developer reports, program or fellowship outcomes, event recaps, impact or B-Corp reports, investor updates, trend reports, internal retros. Covers asks like \"generate a Q3 developer report for GitHub\", \"write up how the PE Fellowship did this year\", \"make our 2026 impact report\", \"pull together an investor growth update\", \"what are devs doing with coding agents? write it up for DEV\". Use it even when the ask names no format: a report from MLH data is this skill. Don't use for a single number or quick query answered in chat, a slide deck (google-slides), a one-line fix to an existing report, or documents with no MLH data behind them."
---

# Writing MLH reports

Turn MLH ecosystem data into a report one named reader can act on, delivered as a shareable doc (use the `docs` skill when you have it). Success: the reader gets the point from headings alone, every number traces to a source, and nothing in it is wrong for that audience to see. Most failed drafts get the data right and the story wrong. Steps 1, 3 and 4 carry the weight.

You coordinate; subagents do the reading. Keep raw data out of your own context: each subagent writes to the report's working folder and returns a short summary. If you can't spawn subagents, do the work yourself one source at a time: save raw output to `research/raw/`, finish `research/<source>.md` before opening the next source, and carry forward only short summaries.

## 1. Scope: audience, goal and premise

Read anything the user attached before anything else. Attachments are usually the real brief, and they often show the subject is not what the one-line ask implies (a "developer report" for a talent-program partner is really a program-outcomes report).

Settle these. Infer what the ask, attachments and sources already say, and write each inference into the brief as a stated assumption. Ask only what blocks the work, one question at a time; when nothing blocks, go straight to gathering, and the user corrects assumptions at the gate.

- **Audience:** who reads it (a partner, the MLH team, leadership, investors, the public) and what they may see.
- **Goal:** what the reader should know, feel or decide afterward. Every section must serve it.
- **Subject and spine:** what the report is about, and the comparison that carries it (partner vs competitors, program vs the wider field, this year vs last, target vs actual).
- **Period and baseline.**
- **What's new:** firsts this period. Users often forget to mention them.
- **Where the data lives,** including systems not yet connected.
- **Deadline:** check the calendar and inbox for a meeting or request the report should land before. Its invitees are the named readers.

**Check the premise.** Confirm the report's starting assumption still holds before you build on it: the certification, partnership or program it's about is still active, and you know what this reader has already been told (search email and shared channels for figures sent to them). Tell the user at once if the premise is broken. Figures already sent go into the reconcile table.

Then set the audience rules for this report: tone, whether recommendations are allowed, what's confidential, and the notice line from [writing.md](references/writing.md#boilerplate). Write them into the brief. Defaults:

| Audience | Tone | Recommendations | Never include |
|---|---|---|---|
| Partner | Independent, data-led, never a pitch | No: findings and what to track | Other partners' data or MLH activity (never say a named competitor sponsored or ran anything), pricing, deal terms or contracted targets (incl. "% of goal"), budgets, renewal status, internal staffing |
| MLH internal | Candid, positive where earned | Yes: specific and bold | Individuals' personal data |
| Investor | Confident, evidence-led, no hype | Yes: what's next | Partner deal terms (incl. contract end dates), individuals' data, anyone's pay even as an aggregate line, cap-table detail |
| Public | Polished | Light | Anything confidential; any demographic or location group under 10 people |

Start `brief.md` in the working folder: audience, goal, spine, period, audience rules, a data cutoff date every query filters on (live tables keep changing), and every decision the user makes from here on. Every subagent reads it.

## 2. Gather

Preflight every connector you'll need with one test query. If one returns a re-auth link, send the user all the links and stop until they're fixed.

Dispatch one subagent per source, in parallel. Each reads `brief.md`, writes `research/<source>.md` with every figure, its exact source (table and query, file, tab and range, URL, or permalink) and the exact question wording for survey items, then returns 300 words or fewer.

[references/sources.md](references/sources.md) maps MLH's main sources and their known traps. Read it before writing the gather briefs. It is a starting map, not a fence: look for other systems that hold what the goal needs (finance, CRM, ads, analytics) and use them.

Re-trace every figure you reuse to the raw source: decks, docs, Slack posts, figures already sent to the reader, and the maintained boilerplate in writing.md. Decks drift from their data, and so does boilerplate.

## 3. Reconcile and find the story

Build `reconcile.md`: each metric, every value found, the source of each, the chosen figure, and why. When sources disagree, the closer to raw data wins (warehouse > raw sheets and forms > dashboards > decks and docs > Slack and email > meeting transcripts > memory). A figure the reader already received that doesn't reproduce is a headline conflict. Keep other deck figures that don't reproduce as a QA list for delivery.

Then find the story in the reconciled data. Look for:

- **Measures that disagree** (self-ratings vs assessments, usage vs trust). This is often the lead finding.
- **A true baseline:** the same question asked of a comparable group.
- **Confounds:** test each headline against the obvious one (a sponsored event or prize, a one-off campaign, a platform challenge) and show the adjusted figure beside it.
- **Leads and gaps:** where the subject leads and where it trails, as far as the reader's decision needs.
- **Segments:** split next-gen devs vs professionals where the data allows, with n for each. A gap inside the noise for that n is a tie. Never label an all-respondent figure as a segment.
- **The user's framing:** keep the point, but make it as precise as the evidence.
- **Firsts,** including one just outside the period or population: raise it at the gate rather than drop it or use it silently.

Gaps in MLH's own data pipeline are not findings about the subject. Build findings from what is measured and put the gap in Methodology.

## 4. Gate: outline and conflicts together

One gate before any drafting. First, a fresh subagent briefed as the target reader (or you, rereading as them) reads your draft outline and `reconcile.md`, then names the finding their decision hangs on and what they'd doubt. Without this, the critic finds the real lead after the draft is built. Lead with that finding, even when it's a loss.

Then show the user:

- the one-line arc, now backed by data, opening with that lead
- the title and claim-first H2s in reading order, each with its evidence, planned visual and sources; flag any H2 whose number hangs on an open conflict
- the conflicts

Order sections by strength for this reader, not by data source or the brief's question order. End the gate message with exactly one question: the headline-changing conflict that matters most (what you found, the options, your pick and why), with "or tell me what to change in the outline" as the way to approve or redirect it. Ask the remaining headline conflicts the same way, one per message (structured choice UI where available). List the rest as "taking my recommended picks unless you object". Also raise anything the default population rules in sources.md would drop that the subject cares about.

Log every decision in `brief.md`. Once the user approves, create the doc under the approved title (some doc tools can't rename it later) with a pending block per section, and share the link so the user can watch it fill.

## 5. Plan and draft

An analyst subagent reads `brief.md`, `reconcile.md` and `research/`, then writes `plan.md`: the insights under each approved H2, ranked by the goal, and 4–7 visual specs with exact rows.

Draft one section per call, prose then visuals, following [references/writing.md](references/writing.md). Read it before the first section. It also holds the maintained intro and notice lines.

The doc holds only what its reader may see. Placeholders, unverified claims and sensitive items the user hasn't cleared go in `delivery-notes.md` as open items, never in the doc.

## 6. Review

Once the structure is locked:

1. **Fact-checker** (fresh subagent): traces every number, including each chart's data rows and caption, to `research/` or an opened URL; checks segment labels, question wording and every decision logged in `brief.md`; and applies clear fixes. It checks the intro word for word against writing.md's Boilerplate and leaves its brand claims alone.
2. **Critic** (fresh subagent, briefed as the target reader): what would they doubt, skip, or forward? What is the strongest finding, and is it leading? Lists judgment calls; edits nothing.
3. **Editor** (one subagent, one pass): applies the critique, voice and skimmability. It adds or changes a figure only from `reconcile.md` or `research/`, and lists each one in the delivery notes for re-check.

Only one agent edits the doc at a time. Route the user's comments through the active editor.

## 7. Deliver

Send the doc link, then:

- **Open items** (from `delivery-notes.md`): small samples, provisional periods, unverified figures, held-back sensitive items, figures the editor added, anything the user must confirm.
- **QA list:** source figures (decks, dashboards) that didn't reproduce.
- **Email draft** to the external readers, last, once the doc is final: the link, three balanced findings, and the notice line.

Post a one-line status in chat at each stage: scope, gather, gate, draft, review, delivery. Build one version; offer variants only after.
