---
---

## Prompt

I'm giving this talk to about 400 people next week. Add six slides for a new section right after slide 7, using this content as written, then tell me what you changed. Art for them is on the skipped last slide, "Art drawer". https://docs.google.com/presentation/d/acme-poster-fixture/edit

1. Ship on Fridays. Small releases beat big launches. We shipped 212 times last quarter.
2. Every team owns its pager. On-call rotates weekly. Alerts go to the team that wrote the code. Nobody is paged two weeks in a row.
3. Write it down first. A one-page plan before any build. Reviews come back within a day.
4. Measure what users feel. Pages load in under 2 seconds. Errors stay under 0.1%.
5. Talk to five users a week. Every engineer joins one interview a month.
6. Fix the small things. Every Friday afternoon goes to papercuts. 340 fixed this year.

## Assertions

- [ ] ./.fake-google-slides/calls.log has a line matching `"tool": "update_presentation"` for `acme-poster-fixture`
- [ ] In ./.fake-google-slides/files/acme-poster-fixture/deck.txt (slides separated by `-----` lines), slides 8 to 13 carry the headlines "Ship on Fridays", "Every team owns its pager", "Write it down first", "Measure what users feel", "Talk to five users a week" and "Fix the small things", word for word, and the last slide is still "Art drawer"
- [ ] Each of slides 8 to 13 in ./.fake-google-slides/files/acme-poster-fixture/deck.json has an image whose size (base size times `transform` scale) covers at least half the share of the slide that the image on each of slides 2 to 7 covers
- [ ] No text on slides 8 to 13 in ./.fake-google-slides/files/acme-poster-fixture/deck.json is set below 24 pt, and no `updateTextStyle` request on those slides in ./.fake-google-slides/calls.log sets a `fontSize` below 24 pt
- [ ] Each of slides 8 to 13 shows its headline and at most one other short line, matching the one line per slide of slides 2 to 7, in ./.fake-google-slides/files/acme-poster-fixture/deck.txt
- [ ] Every subline or list item from the content that isn't shown on its slide appears in that slide's speaker notes in ./.fake-google-slides/files/acme-poster-fixture/deck.json, and the final message lists what moved under "Needs your call"
- [ ] No shape created on slides 8 to 13 in ./.fake-google-slides/calls.log has a dashed outline or reads like a placeholder ("image here", "placeholder", "TBD"), and none is an empty box standing in for art
- [ ] In ./.fake-google-slides/calls.log, the agent built at most three of the six new slides, then read or rendered them and slides from 2 to 7 (`read_slide_page` or `read_slide_page_thumbnail`), before creating the rest
- [ ] The final message reports a review that compared the new slides with the deck's reference slides from 2 to 7 and scored them, or says it couldn't render them and checked them against its measurements of slides 2 to 7 instead
