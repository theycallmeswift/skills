---
---

## Prompt

Slide 9 of our onboarding deck, "Tips", is a plain bullet list while the rest of the deck is designed. Redesign it so it belongs with the others, then tell me what you changed. https://docs.google.com/presentation/d/acme-onboarding-fixture/edit

## Assertions

- [ ] ./.fake-google-slides/calls.log has a line matching `"tool": "update_presentation"`
- [ ] ./.fake-google-slides/deck.txt contains all five tips from the original slide 9 with their wording unchanged: "Start with one pilot team before inviting everyone", "Clean up old projects before you import them", "Assign an owner to every imported project", "Turn on sync only after the review step", "Keep the onboarding checklist pinned for new hires"
- [ ] Every color set by an `update_presentation` request in ./.fake-google-slides/calls.log is a theme color (`themeColor`) or one of the deck's own colors (#FFFFFF, #E5E7EB, #6B7280, #374151, #111827, #F3F4F6, #0F172A)
- [ ] The shapes created on slide 9 in ./.fake-google-slides/calls.log do not form a single row of four equal cards, the layout slide 10 already uses
- [ ] Every `objectId` the agent chose in a `createShape` request in ./.fake-google-slides/calls.log starts with `s09_` followed by a word naming the element's role
- [ ] After its last `update_presentation` call, ./.fake-google-slides/calls.log has a `read_slide_page`, `read_presentation` or `read_slide_page_thumbnail` call that covers slide 9
