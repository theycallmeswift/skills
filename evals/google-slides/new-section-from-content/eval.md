---
---

## Prompt

Our onboarding is getting a sixth step, Automate. Add three slides for it right after slide 8 of the onboarding deck, using this content as written, then tell me what you changed. https://docs.google.com/presentation/d/acme-onboarding-fixture/edit

1. Automate the routine work. Rules move requests to the right owner without anyone triaging. Stat: 3 hrs saved per person each week.
2. Three automations to start with. Auto-assign by project. Remind owners a day before due dates. Close tasks when the linked request ships.
3. Before you turn on automations. Finish the review step first. Start with one rule per team. Check the rule log after a week.

## Assertions

- [ ] ./.fake-google-slides/calls.log has a line matching `"tool": "update_presentation"`
- [ ] In ./.fake-google-slides/deck.txt (slides separated by `-----` lines), slides 9, 10 and 11 carry the titles "Automate the routine work", "Three automations to start with" and "Before you turn on automations", and slide 12 is "Tips"
- [ ] ./.fake-google-slides/deck.txt contains "Rules move requests to the right owner without anyone triaging", "Close tasks when the linked request ships" and "Check the rule log after a week" with their wording unchanged
- [ ] Every color set by an `update_presentation` request in ./.fake-google-slides/calls.log is a theme color (`themeColor`) or one of the deck's own colors (#FFFFFF, #000000, #E5E7EB, #CBD5E1, #6B7280, #374151, #111827, #F3F4F6, #0F172A), comparing each `rgbColor` after converting its 0–1 floats to hex
- [ ] The "Automate the routine work" slide uses the step design of slides 4 to 8 (tracker, number badge and stat panel), by duplicating one of them or with matching shapes, as shown in ./.fake-google-slides/calls.log
- [ ] Neither "Three automations to start with" nor "Before you turn on automations" is laid out like its neighbor "Tips" (a title over a plain bullet list), and the two are not laid out identically to each other, as shown by the requests in ./.fake-google-slides/calls.log
- [ ] Every `objectId` the agent chose in a `createSlide`, `createShape` or `duplicateObject` request in ./.fake-google-slides/calls.log names its slide and the element's role
- [ ] Slide 1's subtitle "Get a new team live in five steps" and slide 3's title "Five steps from sign-up to shared" are updated to six steps in ./.fake-google-slides/deck.txt, or the final message lists each with proposed wording
- [ ] The step tracker on slides 4 to 8 ("1 Setup" … "5 Share") gains "6 Automate" in ./.fake-google-slides/deck.txt, or the final message lists the tracker with a proposed change
- [ ] After its last `update_presentation` call, ./.fake-google-slides/calls.log has a `read_slide_page`, `read_presentation` or `read_slide_page_thumbnail` call that covers a new slide
