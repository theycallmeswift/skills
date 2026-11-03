# Writing the report

How an MLH report reads: skimmable, credible, and honest without reading like an audit.

## Top of the doc

1. Title that names the subject and the question (`MLH × Snowflake: How Next-Gen & Professional Devs Build with Data Platforms`). Byline: as-of date · author.
2. The notice line for the audience, and the intro for partner and public reports (see [Boilerplate](#boilerplate)).
3. **Verdict:** one or two sentences with the win, the miss, and what it means. Readers only believe a win after they've seen the miss.
4. **The short version:** 5–7 bullets, each with a bold label and one number. For internal reports, group them as what went right, what went wrong, and what changes.
5. Optional stat strip: 4–6 headline numbers when the story is a scoreboard.

## Headings carry the story

- H2s are claims with a number and one emoji. The headings alone should tell the story.
- Pair the win and the loss in one H2 when both are true ("Claude leads on trust, but Gemini wins hackathon projects 📊"). Candour you can see in the headings earns trust for the rest.
- Use H3s under an H2 when it holds more than one point.
- Open each paragraph or bullet with a bold lead-in when the section is a list of findings. Bold the key number once.

## Sentences

- Under 25 words. Paragraphs of 3 sentences or fewer.
- "We" means MLH. In partner reports, "you" means the partner.
- Say "next-gen devs", never "students". Say "professionals" or "working professionals".
- Plain language: say what the number means, not "breadth" or "depth".
- Integers in titles, H2s and the verdict. Use one decimal only where you compare close values. Show small groups as counts ("13 of 15 mentors").
- Every win gets a comparator: target vs actual, this year vs last, or the same question asked of a baseline group.

## Credibility, not audit

- Every number traces to `research/` or an opened URL. Never estimate.
- Use citations and sample sizes where they make an insight more convincing, mostly in captions and Methodology.
- Caveats go in Methodology. Raise a weakness in the body only if it changes the reader's decision or they'd hit it anyway; then state it once, beside the response to it.
- No causal claim the data can't carry. A belief goes in as "we believe…" with its evidence.
- Explain any adjustment that moves a headline number (re-scoring, exclusions) in one plain sentence beside that number.
- Flag provisional periods. Never frame a trend from a low point to a peak.
- An external benchmark gets one directional sentence and a note when its question differs. Don't build a heading on a cross-survey comparison.

## Visuals

- At least one per H2. Tables for comparisons and plans; a chart for any set of five or more values; drawn timelines for sequences.
- Chart title states the finding and its number. Bars start at zero, with values on the marks.
- The subject gets the doc's first categorical color everywhere; the main comparator one fixed second hue; everything else muted.
- Show segment columns (all / next-gen / pro) when the split matters.
- Annotate in the chart where it saves a paragraph ("up from 39% in Jul", "excl. sponsored events").
- Caption: `Source: [dataset], [period], [population filter] [n=…, per segment when split]. Q: "[exact wording]" ([answer mode]). [rule or exclusion]`.
- End the lead-in sentence with a colon and keep it next to its chart.
- Each number appears once, in a chart or a table, not both.
- Screenshot or render every visual after writing it, and fix overlaps.

## Tone by audience

- **Partner:** state competitor leads plainly, in headings and charts too. No "let's", proposed programs, prizes, pilots, MLH upsell or "your opportunity". End with implications and what to track: findings, not offers.
- **Internal:** a scoreboard, then causes (count your own misses in the heading), then a plan: a targets table (this year / last year / proposed) and dated next steps.
- **Investor:** lead with trajectory and the comparator; name risks plainly, each with the response.
- **Public:** no internal names, file names or tooling in reader-facing text.

## End of the doc

**Methodology & sources** (last H2): one H3 per source with the period, population and filters, and exclusions. Add "Counts and samples" when sources gave different counts, and "Unverified items" for figures relayed second-hand. Then links to every external source cited.

Don't add a separate reach or "about MLH" section; the intro carries it.

## Boilerplate

Reuse as written, swapping the bracketed parts, and re-check every figure against its source each time.

**Intro** (italic, no heading, under the byline). Public reports use the first paragraph only:

> Major League Hacking (MLH) is the world's largest independent developer community. Over the last 13 years, we've helped 15% of software engineers get their start, and now we're creating the home for the next billion software creators. The data below comes from our quarterly developer census, submissions from 1,500+ hackathons a year, and the 3.5M developers on DEV (dev.to). Together, it shows which [SUBJECT] next-gen devs and working professionals actually pick up.
>
> We're sharing this data so your team has an independent, ground-level read on how developers use [PARTNER] and its competitors, including where [PARTNER] trails. Each chart notes its source and sample; full methodology is at the end.

**Notice lines:**

- Partner: ***This report is shared confidentially for [PARTNER]'s internal use and is not for publication.***
- MLH internal: `Internal to MLH. Not for sharing outside the team.`
- Investor: `Confidential. Prepared for MLH investors; not for further distribution.`
- Public: none.

**Reach facts** for the intro or a stat strip (as of Nov 2026): 15% of software engineers got their start with MLH; 1 in 3 CS grads joins the MLH network; 1.5k+ hackathons and events a year; 3.5M DEV users and 10M monthly uniques; 56% of alumni put MLH-learned tech into production at work (Oct 2026 census); 45% discover dev tools at hackathons vs 12% through ads.
