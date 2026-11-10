---
name: writing-mlh-reports
description: "Use when the user wants a shareable report, write-up or data story built from the MLH ecosystem (Major League Hacking, DEV/dev.to, MLH programs and partners): partner developer reports, program or fellowship outcomes, event recaps, impact or B-Corp reports, investor updates, trend reports, internal retros. Covers asks like \"generate a Q3 developer report for GitHub\", \"write up how the PE Fellowship did this year\", \"make our 2026 impact report\", \"pull together an investor growth update\", \"what are devs doing with coding agents? write it up for DEV\". Use it even when the ask names no format: a report from MLH data is this skill. Don't use for a single number or quick query answered in chat, a slide deck (google-slides), a proposal or pitch to a buyer, a one-line fix to an existing report, or documents with no MLH data behind them."
---

# Writing MLH reports

Turn MLH ecosystem data into a shareable doc one named reader can act on. It's a sales tool: defensible, not academic. Every claim survives a skeptical analyst, nothing is wrong, and nothing leaks; rigor that changes no claim gets cut. Steps 1, 3 and 4 carry the weight: drafts fail on the wrong subject or a lead figure that doesn't reproduce.

| Step | Owner | Reads | Writes | Stop the line when |
|---|---|---|---|---|
| 1. Scope | You | The ask, attachments, what the reader was told | `brief.md` | The premise is broken or a question blocks |
| 2. Gather | One subagent per source | `brief.md`, [sources.md](references/sources.md) | `research/<source>.md` | A source the goal needs hasn't answered: no substitutes |
| 3. Reconcile | You | `research/` | `reconcile.md` | A figure that could lead doesn't reproduce |
| 4. Gate | Reader-critic, then the user | Outline, `reconcile.md` | Approved outline in `brief.md` | The user hasn't approved |
| 5. Draft | Analyst, then you | `brief.md`, `reconcile.md`, `research/` | `plan.md`, the doc, `delivery-notes.md` | A figure isn't in `reconcile.md` |
| 6. Review | Fact-checker, critic, editor, in turn | The doc, `research/` | Fixes in the doc | The critic doubts the evidence: back to step 3 |
| 7. Deliver | You, then the user | The doc, `delivery-notes.md` | Link, open items, email draft | Never sent without the user |

Fix feedback where it lives: a wrong figure in `reconcile.md`, a wrong subject or lead in `brief.md` and back through the gate, a judgment call in the doc. You coordinate; subagents keep raw data out of your context. Without subagents, finish one source's `research/<source>.md` before opening the next.

## 1. Scope

Read attachments first: they are usually the real brief and often change the subject (a "developer report" for a talent-program partner is really program outcomes). A pasted template is only a format hint: any options you offer include the subject the attachments name. Then settle the audience; the goal (what the reader should know or decide); the spine (the comparison that carries it: competitors, the field, last year or target); the period (a program's "this year" is its cohort year); and which systems hold the data (ask). Record inferences as assumptions the user corrects at the gate; ask only a blocking question, one at a time.

**Check the premise:** the certification, partnership or program is still active, no existing report already covers this (offer to revise it, or a new version if it's been shared), and you know what this reader was already told (search email and channels). Tell the user at once if the premise is broken; figures already sent go into the reconcile table.

Write the audience's row and its notice line ([writing.md](references/writing.md#boilerplate)) into the brief:

| Audience | Tone | Recommendations | Never include |
|---|---|---|---|
| Partner | Independent, data-led, never a pitch | No: findings and what to track | Other partners' data or MLH activity (never say a named competitor sponsored or ran anything), pricing, deal terms or contracted targets (incl. "% of goal"), budgets, renewal status, internal staffing |
| MLH internal | Candid, positive where earned | Yes: specific and bold | Individuals' personal data, including participants' names, quotes and offers |
| Investor | Confident, evidence-led, no hype | Yes: what's next | Partner deal terms (incl. contract end dates), individuals' data, anyone's pay even as an aggregate line, cap-table detail |
| Public | Polished | Light | Anything confidential; any demographic or location group under 10 people |

`brief.md` holds audience, goal, spine, period, audience rules, one data cutoff date for every query, and every decision the user makes.

## 2. Gather

Test each connector with one query and send all re-auth links at once; Slack, decks and memory never stand in for a warehouse that's down. One subagent per source writes `research/<source>.md` with every figure, its exact source and, for survey items and scores, the exact wording and pass threshold, and returns ≤300 words. Re-trace every reused figure to raw data, the user's own included: decks, Slack, memory and figures already sent all drift.

## 3. Reconcile and find the story

Build `reconcile.md`: per metric, every value, its source and the chosen figure. Closer to raw wins: warehouse > sheets and forms > dashboards > decks > Slack and email > memory. A figure the reader already received that doesn't reproduce is a headline conflict. Then look for:

- **Measures that disagree** (self-ratings vs assessments, usage vs trust): often the lead.
- **A comparator** for every win: target, last year, or the same question asked of a comparable group.
- **Confounds** (a sponsored event or prize, a one-off campaign): show the adjusted figure beside the headline.
- **Segments:** cut census figures by next-gen and professionals; a gap of a few points is a tie. Never label an all-respondent figure as a segment.
- **Firsts,** including one just outside the period: raise it at the gate.
- **Gaps in MLH's own data** are not findings.

## 4. Gate

One gate before any drafting. First, a fresh subagent briefed as the target reader (or you, rereading as them) reads the outline and `reconcile.md` and names the finding their decision hangs on and what they'd doubt. Lead with it, even when it's a loss.

Show the user the one-line arc opening with that lead; the title and claim-first H2s, strongest first, each with evidence and planned visual (flag any that hang on an open conflict); and the conflicts. End with exactly one question: the most headline-changing conflict (what you found, the options, your pick and why), with "or tell me what to change in the outline". Ask other headline conflicts the same way, one per message; list the rest as "taking my recommended picks unless you object". After approval, create the doc under the approved title with a pending block per section, and share the link.

## 5. Draft

An analyst subagent writes `plan.md`: ranked insights per H2 and 4–7 visual specs with exact rows. Read [writing.md](references/writing.md), then draft one section at a time. The doc holds only what its reader may see: placeholders, unverified claims and anything sensitive the user hasn't cleared go in `delivery-notes.md`.

## 6. Review

Fresh subagents, one editing the doc at a time:

1. **Fact-checker:** traces every number, chart rows and footnotes included, to `research/`, and checks that dates, windows and counts can co-exist; checks segment labels, question wording and the decisions in `brief.md`; leaves the intro's brand claims alone; hunts leftover placeholders and never-include items. Applies clear fixes.
2. **Critic,** briefed as the target reader: what they'd doubt, skip or forward, and whether the strongest finding leads. Edits nothing.
3. **Editor,** one pass: applies the critique and tightens voice; the title and H2s claim no more than the body supports. New figures only from `reconcile.md`, flagged in the delivery notes.

## 7. Deliver

Send the doc link, then the open items from `delivery-notes.md` (directional or provisional figures, held-back items, anything to confirm), and last an email draft to external readers: the link, three balanced findings and the notice line. Build one version; offer variants or an export after.
