---
---

## Prompt

A reviewer left this note on slide 7 of our onboarding deck: "Review now takes about 4 minutes, not 10, and the step is renamed Approve. Fix the stat panel." Make the fix in the deck, then tell me what you changed and anything that needs my call. https://docs.google.com/presentation/d/acme-onboarding-fixture/edit

## Assertions

- [ ] ./.fake-google-slides/calls.log has a line matching `"tool": "update_presentation"`
- [ ] ./.fake-google-slides/deck.txt has no line matching `^10 min`
- [ ] ./.fake-google-slides/deck.txt has no line matching `^4 Review`
- [ ] ./.fake-google-slides/deck.txt has the tracker label "4 Approve" on each of slides 4 to 8 (the slides are separated by `-----` lines)
- [ ] The final message names slide 7's title "Review in 10 minutes" as now wrong and proposes new wording for it
- [ ] If slide 7's title in ./.fake-google-slides/deck.txt no longer reads "Review in 10 minutes", the final message says the title was changed and to what
- [ ] The final message mentions slide 7's speaker notes, which say "about 10 minutes", or ./.fake-google-slides/calls.log has an `update_presentation` request on object `SLIDES_API1923387011_3`
- [ ] Slide 3's agenda line for step 4 in ./.fake-google-slides/deck.txt no longer says "Review" or "10 minutes", or the final message lists that line with proposed wording
