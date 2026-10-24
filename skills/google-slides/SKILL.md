---
name: google-slides
description: "Use when building a new slide deck or changing slides in an existing Google Slides deck: a new deck from a template or from content the user supplies, adding or redesigning slides so they match the rest of the deck, or acting on reviewer comments or a changed number. Covers asks like \"make me a new deck about our Q3 results\", \"build a deck from our brand template\", \"add three slides after slide 8\", \"these last slides are just bullet points, fix them\", \"the numbers changed, update the deck\". Don't use for reading, summarizing or exporting a deck without changing it, a one-word text fix, or PowerPoint and Keynote files."
---

# Google Slides decks

Turn the user's content into slides, in a new deck or an existing one. Take the content as given: don't write the story or rework the outline. For Slides and Drive mechanics (field masks, EMU geometry, guarded writes, rendering), use the `google-workspace` skill when you have it.

**Without `google-workspace`, ask before the first write.** Its rules keep raw Slides writes from landing in the wrong place or overwriting someone's newer change, so writing without them is the user's call. Before creating, copying or editing any file, say the skill isn't available, say what you'd build or change, and get an explicit go-ahead; then use whatever Slides and Drive tools you have. Reading, planning, and reviewing saved copies or renders need no permission: do steps 1 to 3 first and ask with the plan in hand.

Success: the slides read as part of their deck, every fact matches its source, and nothing else in the deck contradicts them. Agents usually get the first and miss the other two; steps 1, 4 and 5 carry the weight.

## 1. Scope the job

Write down, before any write:

- the slides in scope: for an existing deck, slide number and object ID; for new slides, each one's title and body from the user's content
- every fact, number and name on them, with its source. Keep the user's wording, names, casing and numbers exactly. If the deck and the source disagree, the source wins; say so.
- anything the request changes that the deck states elsewhere (a renamed step, a new step, a new result, a dropped feature). Step 5 checks these.

For an existing deck, read the file's owner and sharing from its metadata. If the user has told you who they are and the owner is someone else, or the deck is widely shared, stop and ask before editing, or offer to work on a copy: the user's go-ahead is not the owner's. If the metadata read fails, fix the call; if you still can't read it, ask. An owner you have nothing to compare against is not a reason to stop.

## 2. Learn the design

### New deck

- **Template or reference deck named:** copy it with Drive's copy tool and build in the copy. The copy keeps the template's theme colors, fonts, masters, layouts and logo; a blank deck loses them. Never edit the template itself. Learn the copy's design as for an existing deck, from its layouts and sample slides.
- **None named:** ask once, in one question, for a template or a deck to match, with your slide plan attached. If the user has none or already said go ahead, create a blank presentation and keep its stock theme: one accent color from the theme, at most two layouts (title; title and body), nothing invented. Brand colors, fonts and logo are the brand owner's call; if the deck seems to need them, list that under "Needs your call".

Build each new slide on the deck's own layouts (`createSlide` with the layout's ID and `placeholderIdMappings`, so title and body land in the theme's placeholders), not hand-placed text boxes. Remove or reuse the template's sample slides so none of their placeholder text ships.

### Existing deck

Read two or three finished slides near the scoped ones, with a field mask. Note:

- page size, margins, grid
- title style (font, size, weight, phrase highlighting)
- colors, by theme slot where the deck uses them (`ACCENT1`), so new shapes follow the theme
- reused components: cards, number badges, stat panels, trackers, footers, logos
- object ID naming, so yours match

New slides doing the same job as existing ones (another step, another stat) reuse their components; duplicating a finished slide and changing its text is usually cleanest.

## 3. Design the slides as a set

Slides doing the same job (steps, tips, options) share one layout so they read as a series. Adjacent slides doing different jobs get different layouts. Before building, check the slides on either side of the scoped ones; if your layout echoes a neighbor's, change it.

Size every box to its content: a card a third empty looks unfinished, and text in too small a box spills over, because Slides never shrinks text. Body text needs strong contrast; mid-grey on white reads as disabled.

Link to the exact destination (the specific page, not a homepage), and link between slides when the deck will be clicked through live.

## 4. Build, render, and get a critical review

1. Build each slide in one batch, guarded by the revision ID from your latest read. Name every object ID you choose slide-plus-role (`s04_title`, `s04_stat_value`).
2. After your last write, read the changed slides back. Render them (thumbnail or export, whichever your tools offer) and look yourself. With no render, check geometry from the fresh read: every box inside the page and margins, text fits its box at its font size, nothing overlaps. Say in the report you couldn't see it.
3. Get a second opinion from a reviewer who hasn't seen your work: spawn a subagent with the critic prompt below, passing labeled page images of the changed slides and the slides on either side. Without subagents, apply the prompt to the images yourself in a fresh pass.
4. Fix every finding, re-render, recheck. Don't report done before at least one fix-and-recheck cycle; one fix often causes another problem.

Critic prompt:

> You are reviewing new or redesigned slides before they go in front of an audience. Assume there are problems and find them; "looks fine" is not an answer. The images show the changed slides and, for comparison, their neighbors. For each changed slide, list every issue, however minor:
>
> - text that overflows, is clipped, or sits too close to an edge
> - boxes with large empty areas, or uneven gaps between items
> - body text with weak contrast (light grey on white, dark on dark)
> - elements misaligned with each other or with the deck's margins
> - anything that doesn't match the neighbors: title style, fonts, colors, spacing, footer and logo placement, number badge style
> - a layout close enough to a neighbor's that the two blur together
> - inconsistent capitalization, punctuation or number formats within a set or across neighboring slides
> - leftover placeholder or template sample text, stray emoji, or decoration that adds nothing
>
> For each issue give the slide, what is wrong, where, and a concrete fix. End with the single most important fix.

## 5. Existing deck: sweep for anything the change contradicts

A changed or added fact is usually stated in more than one place. Read the whole deck as text and search for every term from step 1: the old number, old name, feature, step label, and any count the change breaks ("five steps" once there are six). Stale copies hide in repeated components: progress trackers, agendas, section dividers, summary slides, speaker notes. Text exports often omit speaker notes; read them too.

- Restatements of the same fact: update in the same pass.
- Anything else the change makes wrong or odd (a title that no longer fits, steps describing the old result, a "pre-run" tag on live work): don't rewrite silently. List each with slide number and proposed wording.
- Copies outside the deck (exported slide images in a repo, a guide or doc quoting the slide): list them for update.

## 6. Report

Reply in three short parts; for a new deck, put its link first:

1. **Changed:** one line per slide.
2. **Checked:** what the render and review found, and what you fixed.
3. **Needs your call:** each item from step 5's list, with slide number and proposed wording, plus anything in the content you couldn't confirm or had to leave out.
