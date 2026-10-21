---
---

## Prompt

./deck.json, ./deck.txt and ./render/ are a saved copy of a Google Slides deck (you can't reach Google from here). A reviewer left this note on slide 7: "Review now takes about 4 minutes, not 10, and the step is renamed Approve. Fix the stat panel." Write the edits you'd make to ./changes.md, then reply with what you'd change and anything that needs my call.

## Assertions

- [ ] ./changes.md exists
- [ ] ./changes.md changes slide 7's stat panel to say about 4 minutes
- [ ] ./changes.md updates the "4 Review" tracker label to "4 Approve" on every one of slides 4–8, not only slide 7
- [ ] The reply or ./changes.md flags slide 7's title "Review in 10 minutes" as now wrong and proposes new wording
- [ ] The reply does not rewrite slide 7's title without listing it for a decision or proposing the wording
- [ ] The reply lists any other slide or speaker note in ./deck.txt that still says 10 minutes or "Review", with its slide number
