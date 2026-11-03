# Writing the report

How an MLH report reads: skimmable, credible, and honest without reading like an audit. These rules override a doc tool's default style where they differ (emoji in headings, the short version, a Methodology section).

## Top of the doc

1. Title that names the subject and the question or headline finding (`MLH × Snowflake: How Next-Gen & Professional Devs Build with Data Platforms`). It passes the same tests as an H2: no claim, metaphor or hype the body can't carry. Byline: as-of date · author.
2. The notice line for the audience, and the intro for partner and public reports (see [Boilerplate](#boilerplate)).
3. An `Executive summary` H2 (with an emoji) over the verdict, short version and any stat strip, so the summary shows in the doc's outline.
4. **Verdict:** two or three short sentences: the finding the reader's decision hangs on (even when it's a loss), the miss, and what it means. The miss is about the subject, never about how MLH measures it. Readers only believe a win after they've seen the miss.
5. **The short version:** 5–7 bullets, each with a bold label and one number. For internal reports, group them as what went right, what went wrong, and what changes.
6. Optional stat strip: 4–6 headline numbers when the story is a scoreboard.

## Headings carry the story

- H2s are claims with a number and one emoji that matches the finding's sign (no 🏆 or 🤝 on a loss, a tie or a vendor). H2 #1 carries the verdict's lead. The headings alone should tell the story.
- Pair the win and the loss in one H2 when both are true ("Claude leads on trust, but Gemini wins hackathon projects 📊"). Candour you can see in the headings earns trust for the rest.
- Use H3s under an H2 when it holds more than one point.
- Open each paragraph or bullet with a bold lead-in when the section is a list of findings. Bold the key number once.

## Sentences

- Under 25 words. Paragraphs of 3 sentences or fewer.
- "We" means MLH. In partner reports, "you" means the partner.
- Say "next-gen devs", never "students". Say "professionals" or "working professionals".
- Name the population measured ("census respondents", "MLH developers", "League hackathon projects"), never "developers", "hackers" or "the community" for a sample. Give the next-gen share of "all" once.
- Plain language: say what the number means, not "breadth" or "depth".
- Integers in titles, H2s and the verdict. Use one decimal only where you compare close values; when rounding would hide a near-tie, call it a tie in words. Round once, from the raw figure. Show small groups as counts ("13 of 15 mentors"), with no multiples on them ("4 → 32 posts", not "nearly tripled").
- Every win gets a comparator: target vs actual, this year vs last, or the same question asked of a baseline group.

## Credibility, not audit

- Every number traces to `research/` or an opened URL. Never estimate.
- Use citations and sample sizes where they make an insight more convincing, mostly in captions and Methodology.
- Caveats go in Methodology. Raise a weakness in the body only if it changes the reader's decision, they'd hit it anyway, or a skeptic would raise it against a headline (a competitor missing from the options, a reworded question, a confound the reader paid for); then state it once, in the sentence beside that number.
- No causal claim the data can't carry, in the title, verdict, headings and tables as much as the body. "Because", "drove", "the gap is X" and "what it changed" are causal. A belief goes in as "we believe…" with its evidence.
- Explain any adjustment that moves a headline number (re-scoring, exclusions), or that revises a figure the reader already received, in one plain sentence beside that number.
- Flag provisional periods, on the chart mark as well as in the text. Describe each series' actual direction: never frame a trend from a low point to a peak, call a fall "flat", or say "now matches" when the subject lost a lead.
- Compare like with like: the same wording, answer options, population and definition at both ends of a trend or ranking. Anything else (an external benchmark, a reworded option, another population or revenue basis) gets one directional sentence and a note, never a heading, and is never summed or stacked with the headline.

## Visuals

- At least one per H2 (a table counts), unless the section is one or two facts. A chart when the shape matters (a trend, a ranking of five or more); a table when the reader looks up exact values or plans; a drawn timeline for sequences.
- Chart title states the finding and its number. Bars start at zero, with values on the marks.
- The subject gets the doc's first categorical color everywhere; the main comparator one fixed second hue; everything else muted. With no single subject (a trend across vendors), give each series one fixed color across every chart.
- Show segment columns (all / next-gen / pro) when the split matters.
- Annotate in the chart where it saves a paragraph ("up from 39% in Jul", "excl. sponsored events").
- Caption: `Source: [dataset], [period], [population filter] [n=…, per segment when split]. Q: "[exact wording]" ([answer mode]). [rule or exclusion]`.
- End the lead-in sentence with a colon and keep it next to its chart.
- Each dataset appears once, as a chart or a table, not both. The verdict, short version and headings repeat key numbers on purpose.
- Screenshot or render every visual after writing it: fix overlaps, and check that the title's claim is visible in the marks and agrees with its H2. If you can't render, check layout from the chart's data and code, and say so in the delivery notes.

## Tone by audience

- **Partner:** state competitor leads plainly, in headings and charts too. No "let's", proposed programs, prizes, pilots, MLH upsell or "your opportunity". Activity the partner paid MLH for (sponsored events, its content on DEV) is never its win: name the confound in the same sentence, and never imply it should buy more. End with implications and what to track: findings, not offers.
- **Internal:** a scoreboard, then causes (count your own misses in the heading), then a plan: a targets table (this year / last year / proposed) and dated next steps.
- **Investor:** lead with trajectory and the comparator. Cover revenue on one stated definition, margin, profit or burn, cash and runway, and concentration; a missing one is a top open item. Name risks plainly, each with the response.
- **Public:** no internal names, file names or tooling in reader-facing text.

## End of the doc

**Methodology & sources** (last H2): one H3 per source with the period, population and filters, and exclusions. Add "Counts and samples" when sources gave different counts, and, except in public reports, "Unverified items" for figures relayed second-hand (a public report leaves them out). Then links to every external source cited.

Don't add a separate reach or "about MLH" section; the intro carries it.

## Boilerplate

Reuse as written, swapping the bracketed parts. The first two sentences stay fixed; the "data below comes from" sentence names the sources this report actually uses, keeping the brand figure for any of census, hackathons or DEV it does use. The intro's reach figures are brand claims: directional, owned by MLH, and fine in the intro as written. Keep them out of findings, charts and stat strips, and don't "correct" them against the warehouse. Every other figure gets re-traced like any number.

**Intro** (italic, no heading, under the byline). Public reports use the first paragraph only:

> Major League Hacking (MLH) is the world's largest independent developer community. Over the last 13 years, we've helped 15% of software engineers get their start, and now we're creating the home for the next billion software creators. The data below comes from our quarterly developer census, submissions from 1,500+ hackathons a year, and the 3.5M developers on DEV (dev.to). Together, it shows which [SUBJECT] next-gen devs and working professionals actually pick up.
>
> We're sharing this data so your team has an independent, ground-level read on how developers use [PARTNER] and its competitors, including where [PARTNER] trails. Each chart notes its source and sample; full methodology is at the end.

**Notice lines:**

- Partner: ***This report is shared confidentially for [PARTNER]'s internal use and is not for publication.***
- MLH internal: `Internal to MLH. Not for sharing outside the team.`
- Investor: `Confidential. Prepared for MLH investors; not for further distribution.`
- Public: none.

**Brand claims** (intro only, directional):

- "15% of software engineers": about 5M developers in MLH's database against about 35M software engineers worldwide.
- "1,500+ hackathons a year": the annualized projection across all event formats.
- "3.5M developers on DEV": registered members, per the DEV team.

**Reach facts** for findings or a stat strip (as of Nov 2026), each with its source:

- 56% of census respondents have introduced or started using a technology they learned at a hackathon at work. Season Census, Oct 2026, attention-check passers, n=3,366. Q: "After learning a technology at a hackathon, have you ever introduced or started using it at work?" Never say "alumni", "MLH-learned" or "into production".
- 1,898 events in 2026 across all formats, about 470 of them Hacktoberfest (Core). About 306 a year are hackathon-format.
- Unverified until traced: 1 in 3 US CS graduates joins the MLH network (Hackcon 2025 keynote); 45% discover dev tools at hackathons vs 12% through ads (census, wave unknown); 10M monthly DEV uniques (Mar 2026 figure is 6.8M average, sampled).
