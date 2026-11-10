---
name: writing-mlh-reports
description: "Use when the user wants a shareable report, write-up or data story built from the MLH ecosystem (Major League Hacking, DEV/dev.to, MLH programs and partners): partner developer reports, program or fellowship outcomes, event recaps, impact or B-Corp reports, investor updates, trend reports, internal retros. Covers asks like \"generate a Q3 developer report for GitHub\", \"write up how the PE Fellowship did this year\", \"make our 2026 impact report\", \"pull together an investor growth update\", \"what are devs doing with coding agents? write it up for DEV\". Use it even when the ask names no format: a report from MLH data is this skill. Don't use for a single number or quick query answered in chat, a slide deck (google-slides), a one-line fix to an existing report, or documents with no MLH data behind them."
---

# Writing MLH reports

Turn MLH ecosystem data into a shareable doc that one named reader can act on. Most are sales tools: they must be defensible (every claim survives a skeptic), not academically rigorous. Success: the headings alone carry the point, every number traces to a source, and nothing in it is wrong for that reader to see. Failed drafts pick the wrong subject or lead on a figure that doesn't reproduce, so steps 1, 3 and 4 carry the weight.

| Step | Owner | Reads | Writes | Stop the line when |
|---|---|---|---|---|
| 1. Scope | You | The ask, attachments, what the reader was told | `brief.md` | The premise is broken or a question blocks |
| 2. Gather | One subagent per source | `brief.md`, [sources.md](references/sources.md) | `research/<source>.md` | A source the goal needs hasn't answered: no substitutes |
| 3. Reconcile | You | `research/` | `reconcile.md` | A figure that could lead doesn't reproduce |
| 4. Gate | Reader-critic, then the user | Outline, `reconcile.md` | Approved outline in `brief.md` | The user hasn't approved |
| 5. Draft | Analyst, then you | `brief.md`, `reconcile.md`, `research/` | `plan.md`, the doc, `delivery-notes.md` | A figure isn't in `reconcile.md` |
| 6. Review | Fact-checker, critic, editor, in turn | The doc, `research/` | Fixes in the doc | The critic doubts the evidence: back to step 3 |
| 7. Deliver | You, then the user | The doc, `delivery-notes.md` | Link, open items, email draft | Never sent without the user |

Fix feedback where it lives: a wrong figure in `reconcile.md`, a wrong subject or lead in `brief.md` and back through the gate, a judgment about this report in the doc.

You coordinate; subagents keep raw data out of your context. Without subagents, go one source at a time: raw output to `research/raw/`, and finish `research/<source>.md` before opening the next.

## 1. Scope

Read attachments first: they are usually the real brief and often change the subject (a "developer report" for a talent-program partner is really program outcomes). A pasted template is only a format hint: any options you offer include the subject the attachments name. Then settle the audience; the goal (what the reader should know or decide); the spine (the comparison that carries it: vs competitors, the field, last year or target); period and baseline (a program's "this year" is its cohort year); firsts; the reader's terms; which systems hold the data (ask); and any meeting the report must land before (its invitees are the readers). Record each inference in the brief as an assumption. Ask only a blocking question, one at a time; if nothing blocks, gather, and the user corrects assumptions at the gate.

**Check the premise:** the certification, partnership or program is still active, no existing report already covers this (offer to revise it, or a new version if it's been shared), and you know what this reader was already told (search email and shared channels for figures sent). Tell the user at once if the premise is broken; figures already sent go into the reconcile table.

Write the audience's row and its notice line ([writing.md](references/writing.md#boilerplate)) into the brief:

| Audience | Tone | Recommendations | Never include |
|---|---|---|---|
| Partner | Independent, data-led, never a pitch | No: findings and what to track | Other partners' data or MLH activity (never say a named competitor sponsored or ran anything), pricing, deal terms or contracted targets (incl. "% of goal"), budgets, renewal status, internal staffing |
| MLH internal | Candid, positive where earned | Yes: specific and bold | Individuals' personal data, including participants' names, quotes and offers |
| Investor | Confident, evidence-led, no hype | Yes: what's next | Partner deal terms (incl. contract end dates), individuals' data, anyone's pay even as an aggregate line, cap-table detail |
| Public | Polished | Light | Anything confidential; any demographic or location group under 10 people |

`brief.md` holds audience, goal, spine, period, audience rules, a data cutoff date every query filters on, and every decision the user makes. Every subagent reads it.

## 2. Gather

Preflight each connector with one test query and send every re-auth link at once; Slack, decks and memory never stand in for a warehouse that's down. Read sources.md before briefing, and use any other system the goal needs. One subagent per source, in parallel, writes `research/<source>.md` with every figure and its exact source (query, file/tab/range, URL or permalink; exact wording, examples and pass thresholds for survey items and scores) and returns 300 words or fewer. Re-trace every reused figure to raw data, the user's own included: decks, Slack, memory, figures already sent to the reader and writing.md's boilerplate all drift.

## 3. Reconcile and find the story

Build `reconcile.md`: per metric, every value, its source, the chosen figure and why. Closer to raw wins: warehouse > raw sheets and forms > dashboards > decks and docs > Slack and email > transcripts > memory. A figure the reader already received that doesn't reproduce is a headline conflict; other non-reproducing deck figures go on a QA list for delivery. Then look for:

- **Measures that disagree** (self-ratings vs assessments, usage vs trust): often the lead.
- **A true baseline:** the same question asked of a comparable group.
- **Confounds** (a sponsored event or prize, a one-off campaign, a platform challenge): show the adjusted figure beside the headline.
- **Segments:** cut every census figure by next-gen and professionals, n for each; a gap inside the noise for that n is a tie. Never label an all-respondent figure as a segment.
- **Firsts,** including one just outside the period or population: raise it at the gate, don't drop it or use it silently.
- **Not findings:** gaps in MLH's own data pipeline. They go in Methodology.

## 4. Gate

One gate before any drafting. First, a fresh subagent briefed as the target reader (or you, rereading as them) reads the outline and `reconcile.md` and names the finding their decision hangs on and what they'd doubt. Lead with it, even when it's a loss.

Show the user the one-line arc opening with that lead; the title and claim-first H2s, ordered by strength for this reader, each with evidence, planned visual and sources (flag any that hang on an open conflict); and the conflicts. End with exactly one question: the most headline-changing conflict (what you found, the options, your pick and why), with "or tell me what to change in the outline" to approve or redirect. Ask other headline conflicts the same way, one per message; list the rest as "taking my recommended picks unless you object". Log every decision in `brief.md`. After approval, create the doc under the approved title with a pending block per section, and share the link.

## 5. Draft

An analyst subagent writes `plan.md` from `brief.md`, `reconcile.md` and `research/`: ranked insights per H2 and 4–7 visual specs with exact rows. Read [writing.md](references/writing.md), then draft one section per call, prose then visuals. The doc holds only what its reader may see: placeholders, unverified claims and sensitive items the user hasn't cleared go in `delivery-notes.md`.

## 6. Review

Fresh subagents, one editing the doc at a time (route the user's comments through it):

1. **Fact-checker:** traces every number, including chart rows and footnotes, to `research/` or an opened URL; checks segment labels, question wording and each decision in `brief.md`; leaves the intro's brand claims alone; searches for leftover placeholders and `brief.md`'s never-include items. Applies clear fixes.
2. **Critic,** briefed as the target reader: what they'd doubt, skip or forward, and whether the strongest finding leads. Lists judgment calls; edits nothing.
3. **Editor,** one pass: applies the critique, voice and skimmability, then rereads the title, verdict and H2s against the body's caveats. Adds or changes a figure only from `reconcile.md` or `research/`, listing each in the delivery notes for re-check.

## 7. Deliver

Send the doc link, then the open items from `delivery-notes.md` (small samples, provisional periods, unverified or editor-added figures, held-back items, anything to confirm), the QA list, and last an email draft to external readers: the link, three balanced findings and the notice line. Build one version; offer variants, an export and the charts as standalone images after.
