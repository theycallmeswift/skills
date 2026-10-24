---
---

## Prompt

Make a new deck from our brand template, https://docs.google.com/presentation/d/acme-template-fixture/edit, for Friday's pilot update. Use this content, wording as written:

1. Pilot rollout update. Subtitle: Platform team, October 2026
2. Three teams are live on Relay. Payments went live on August 4. Search went live on September 1. Mobile went live on September 22.
3. Review time dropped from 2 days to 6 hours. Owners are set on import, so nothing waits in a shared queue.
4. Section: What we need next
5. Two asks for leadership. Approve the November rollout to all product teams. Fund one more onboarding engineer.

Send me the link when it's done.

## Assertions

- [ ] ./.fake-google-slides/calls.log has a `copy_file` call whose `fileId` is `acme-template-fixture`
- [ ] ./.fake-google-slides/calls.log has no line matching `"tool": "create_file"`
- [ ] ./.fake-google-slides/calls.log has no `update_presentation` call whose `presentationId` is `acme-template-fixture`
- [ ] ./.fake-google-slides/files/acme-template-copy-fixture/deck.txt contains these five titles with their wording unchanged: "Pilot rollout update", "Three teams are live on Relay", "Review time dropped from 2 days to 6 hours", "What we need next", "Two asks for leadership"
- [ ] ./.fake-google-slides/files/acme-template-copy-fixture/deck.txt contains "Payments went live on August 4", "Fund one more onboarding engineer" and "Owners are set on import, so nothing waits in a shared queue" with their wording unchanged
- [ ] ./.fake-google-slides/files/acme-template-copy-fixture/deck.txt contains none of the template's sample text: "Deck title, presenter and date go here", "Keep one message per slide", "Section divider"
- [ ] Every slide the agent added in ./.fake-google-slides/calls.log comes from a `createSlide` on one of the template's layouts (`p2`, `p3`, `p4`, `p5`, or the predefined TITLE, SECTION_HEADER, TITLE_AND_BODY, TITLE_AND_TWO_COLUMNS) or a `duplicateObject` of a template slide
- [ ] Every color set by an `update_presentation` request in ./.fake-google-slides/calls.log is a theme color (`themeColor`) or one of the template's colors (#14213D, #FFFFFF, #3D4451, #F3F1EC, #F2762E, #2A9D8F, #8D99AE, #E9C46A, #6C757D, #C8553D), comparing each `rgbColor` after converting its 0–1 floats to hex
- [ ] Every `objectId` the agent chose in a `createSlide`, `createShape`, `duplicateObject` or `placeholderIdMappings` entry in ./.fake-google-slides/calls.log names its slide and the element's role, such as `s02_title` or `slide2_body`
- [ ] After its last `update_presentation` call, ./.fake-google-slides/calls.log has a `read_presentation`, `read_slide_page`, `read_slide_page_thumbnail` or `read_file_content` call on `acme-template-copy-fixture`
- [ ] The final message gives a link to the new deck containing `acme-template-copy-fixture`
