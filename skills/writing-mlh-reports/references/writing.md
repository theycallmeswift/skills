# Writing the report

These rules override a doc tool's default style where they differ.

## Top of the doc

1. **Title** stating the headline finding; no claim the body can't carry. Partner and trend reports lead on the reader's market, as a trade outlet would run it (`Devs Trust Claude and Pay Anthropic, but Build with Gemini`): MLH is the source, never the subject. Byline: as-of date · author.
2. **Notice line**, then the **intro** for any report a non-MLH reader sees (see [Boilerplate](#boilerplate)).
3. **`Executive summary` H2** (with an emoji). Under it, with no labels of their own:
   - **Verdict paragraph,** two or three short sentences: the finding the reader's decision hangs on (even a loss), the miss, and what it means. The miss is about the subject, never MLH's measurement.
   - **5–7 bullets,** each with a bold label and one number. Internal reports group them as went right / went wrong / changes.

## Headings and sentences

- H2s are claims with a number and one emoji matching the finding's sign (no 🏆 or 🤝 on a loss, a tie or a vendor). H2 #1 carries the verdict's lead; the headings alone tell the story.
- Under each H2, short H3s (3–6 words) and a bold lead-in per paragraph, so the headings and bold text alone carry the section.
- Pair win and loss in one H2 when both are true ("Claude leads on trust, but Gemini wins hackathon projects 📊").
- Sentences under 25 words, paragraphs of 3 sentences or fewer. "We" is MLH; in partner reports "you" is the partner. Say "next-gen devs", never "students", and use the reader's category nouns ("coding harness"), never a source tab's label. Use the reader's category nouns, never a source tab's label.
- Name the population measured ("census respondents", "League hackathon projects"), never "developers" or "the community"; give the next-gen share of "all" once.
- Integers in title, H2s and verdict; one decimal only to compare close values, and call a near-tie a tie. Small groups as counts ("13 of 15 mentors"), no multiples ("4 → 32 posts", not "nearly tripled"). Don't call out a small n: mark a figure from fewer than 100 people "directional" once, beside it, with its n in the footnote. Keep groups under 30 out of the title, verdict and H2s.
- Every win gets a comparator and every count its "out of".

## Defensible, not an audit

- Caveats go in Methodology. One goes in the body, once, beside its number, only if a skeptic would raise it against a headline (a missing competitor, a reworded question, a confound the reader paid for).
- No causal claim the data can't carry, in headings and tables too. "Because", "drove" and "what it changed" are causal; a belief is "we believe…" with its evidence.
- An adjustment that moves a headline, or revises a figure the reader already received, gets one plain sentence beside it.
- Drop a compromised item (primed by its own examples, or reworded between waves) rather than caveat it.
- Describe each series' actual direction: no low-to-peak framing, no "flat" for a fall, no "now matches" for a lost lead. Mark provisional periods on the chart.
- Compare like with like (wording, population, definition). Anything else gets one directional sentence, never a heading, and is never summed with the headline.

## Visuals

- One per H2 (a table counts) unless the section is one or two facts. Each dataset appears once.
- Chart title states the finding and its number. Bars start at zero, values on the marks. Colors stay fixed across charts: subject first, main comparator second, the rest muted.
- Sources are numbered footnotes, never lines under a chart: a marker (¹) on the sentence or chart title, and the note under **Sources** at the end: `[dataset], [period], [population] [n=…]. Q: "[exact wording]" ([single or multi-select]).`
- Render every visual and check its marks show the title's claim. Can't render? Say so in the delivery notes.

## Tone by audience

- **Partner:** state competitor leads plainly, in headings and charts too. No "let's", proposals, upsell or "your opportunity". Activity the partner paid MLH for (sponsored events, its DEV content) is never its win: name the confound in the same sentence. In a recap of a program the partner paid MLH to run, that program is the subject.
- **Internal:** scoreboard, causes (own misses in the heading), then targets and dated next steps.
- **Investor:** trajectory and comparator first. Cover revenue on one stated definition, margin, profit or burn, cash and runway, and concentration; a missing one is a top open item. Name each risk with its response.
- **Public:** no internal names, file names or tooling.

## End of the doc

**Methodology & sources** (last H2): the numbered **Sources**, then a short note per source on population and filters, carrying the caveats kept out of the body, and links to every external source. No other side sections: the intro carries MLH, and general insights fold into the H2 they support.

## Boilerplate

Reuse as written, swapping bracketed parts; the "data below comes from" sentence names only the sources this report uses. Its reach figures are brand claims: directional, fine in the intro, never "corrected" against the warehouse, never in findings or charts. Re-trace every other figure.

**Intro** (italic, no heading, under the notice line). Investor and public reports use the first paragraph only:

> Major League Hacking (MLH) is the world's largest independent developer community. Over the last 13 years, we've helped 15% of software engineers get their start, and now we're creating the home for the next billion software creators. The data below comes from our quarterly developer census, submissions from 1,500+ hackathons a year, and the 3.5M developers on DEV (dev.to). Together, it shows which [SUBJECT] next-gen devs and working professionals actually pick up.
>
> We're sharing this data so your team has an independent, ground-level read on how developers use [PARTNER] and its competitors, including where [PARTNER] trails. Each chart notes its source and sample; full methodology is at the end.

**Notice lines** (bold italic, under the byline). Public: none.

- Partner: ***This report is shared confidentially for [PARTNER]'s internal use and is not for publication.***
- MLH internal: ***Internal to MLH. Not for sharing outside the team.***
- Investor: ***Confidential. Prepared for MLH investors; not for further distribution.***

**Brand claim bases:** "15% of software engineers" = ~5M developers in MLH's database vs ~35M worldwide; "1,500+ hackathons a year" = annualized projection across all formats; "3.5M developers on DEV" = registered members, per the DEV team.

**Reach facts** for findings (as of Nov 2026):

- 56% of census respondents have introduced or started using a technology they learned at a hackathon at work (Season Census, Oct 2026, attention-check passers, n=3,366; Q: "After learning a technology at a hackathon, have you ever introduced or started using it at work?"). Never "alumni", "MLH-learned" or "into production".
- 1,898 events in 2026 across all formats, about 470 of them listed Hacktoberfest Fests (381 held); about 306 a year are hackathon-format.
- Unverified until traced: 1 in 3 US CS graduates joins MLH (Hackcon 2025 keynote); 45% discover dev tools at hackathons vs 12% via ads (wave unknown); 10M monthly DEV uniques (Mar 2026 shows 6.8M, sampled).
