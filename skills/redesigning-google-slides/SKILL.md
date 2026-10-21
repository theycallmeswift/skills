---
name: redesigning-google-slides
description: "Use when redesigning, restyling or polishing slides in an existing Google Slides deck, or making a section or set of slides match the rest of the deck: \"make these slides look like the others\", \"these last slides are just bullet points, fix them\", \"redesign the demo section\", \"clean up this deck\"; also when acting on reviewer comments or a changed number in a deck. Don't use for a brand-new deck with nothing to match, a one-word text fix, PowerPoint or Keynote files, or reading a deck without changing it."
---

# Redesigning slides in an existing Google Slides deck

This skill is the redesign workflow. For Slides and Drive mechanics (field masks, EMU geometry, guarded writes, rendering), use the `google-workspace` skill when you have it.

**Without `google-workspace`, ask before the first live edit.** Its rules are what keep raw Slides writes from landing in the wrong place or overwriting someone's newer change, so editing without them is the user's call. Before any write to the live deck, tell the user the skill isn't available, say what you'd change, and ask for an explicit go-ahead; then use whatever Slides tools you have. Reading the deck, planning, and reviewing saved copies or renders need no permission, so do steps 1 to 3 first and ask with the plan in hand.

A redesign succeeds when the new slides read as part of the deck, every fact on them is still true, and nothing else in the deck contradicts them. Agents usually get the first right and miss the other two, so steps 4 and 5 carry the weight.

## 1. Scope the job

Before touching the deck, write down:

- the slides in scope (slide number and object ID), and what each must still say
- every fact, number and name on them, with its source. Keep names, casing and numbers exactly as sourced; if deck and source disagree, the source wins; say so.
- anything the request changes that the deck states elsewhere (a renamed step, a new result, a dropped feature). Step 5 checks these.

Check the file's owner and sharing. If the deck is someone else's or widely shared, ask before editing it, or offer to work on a copy.

## 2. Learn the deck's design from its finished slides

Read two or three finished slides near the scoped ones, with a field mask so the read stays small. Note:

- page size, margins, grid
- title style (font, size, weight, phrase highlighting)
- colors, by theme slot where the deck uses them (`ACCENT1`), so new shapes follow the theme
- reused components: cards, number badges, stat panels, trackers, footers, logos
- object ID naming, so yours match

## 3. Design the slides as a set

Slides doing the same job (steps, tips, options) share one layout so they read as a series. Adjacent slides doing different jobs get different layouts so the audience can tell them apart. Before building, check the slides on either side of the scoped ones; if your layout echoes a neighbor's, change it.

Size every box to its content: a card a third empty looks unfinished, and text in too small a box spills over, because Slides never shrinks text. Body text needs strong contrast on its background; mid-grey on white reads as disabled.

Link to the exact destination (the specific page, not a homepage), and link between slides when the deck will be clicked through live.

## 4. Build, render, and get a critical review

1. Build each slide in one batch, guarded by the revision ID from your latest read, with object IDs named slide-plus-role.
2. Render the changed slides (a thumbnail or an export, whichever your tools offer) and look at them yourself. If no render is available, check the geometry from a fresh read instead: every box inside the page and margins, text that fits its box at its font size, and nothing overlapping. Say in the report that you couldn't see it.
3. Get a second opinion from a reviewer who hasn't seen your work: spawn a subagent with the critic prompt below, passing page images of the changed slides and of the slides on either side, labeled. Without subagents, apply the prompt to the images yourself in a fresh pass.
4. Fix every finding, re-render, recheck. Don't report done until at least one fix-and-recheck cycle has run, because one fix often causes another problem.

Critic prompt:

> You are reviewing redesigned slides before they go in front of an audience. Assume there are problems and find them; "looks fine" is not an answer. The images show the changed slides and, for comparison, their neighbors. For each changed slide, list every issue, however minor:
>
> - text that overflows, is clipped, or sits too close to an edge
> - boxes with large empty areas, or uneven gaps between items
> - body text with weak contrast (light grey on white, dark on dark)
> - elements misaligned with each other or with the deck's margins
> - anything that doesn't match the neighbors: title style, fonts, colors, spacing, footer and logo placement, number badge style
> - a layout close enough to a neighbor's that the two blur together
> - inconsistent capitalization, punctuation or number formats within a set or across neighboring slides
> - leftover placeholder text, stray emoji, or decoration that adds nothing
>
> For each issue give the slide, what is wrong, where, and a concrete fix. End with the single most important fix.

## 5. Sweep the deck for anything the change contradicts

A changed fact is usually stated in more than one place. Read the whole deck as text and search for every term from step 1: the old number, old name, feature, step label. Stale copies hide in repeated components: progress trackers, agendas, section dividers, summary slides, speaker notes. A deck's text export often leaves out speaker notes, so read the notes too.

- Restatements of the same fact: update them in the same pass, so the deck never says two things.
- Anything else the change makes wrong or odd (a title that no longer fits, steps describing the old result, a "pre-run" tag on live work): don't rewrite it silently. List each with slide number and proposed wording.
- Copies outside the deck (exported slide images in a repo, a guide or doc quoting the slide): list them so they get updated too.

## 6. Report

Reply in three short parts:

1. **Changed:** one line per slide.
2. **Checked:** what the render and review found, and what you fixed.
3. **Needs your call:** each item from step 5's list, with slide number and proposed wording, plus anything in the source you couldn't confirm.
