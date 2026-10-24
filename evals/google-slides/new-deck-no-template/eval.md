---
---

## Prompt

Make a new Google Slides deck for Acme's Q4 all-hands with these four slides, wording as written:

1. Q4 all-hands. Subtitle: December 2026
2. We shipped Relay 2.0. Search is three times faster. Approvals moved into the inbox.
3. Customers we added this quarter. Northwind, Globex and Initech went live in November.
4. Questions

## Assertions

- [ ] If ./.fake-google-slides/calls.log has no line matching `"tool": "update_presentation"`, the final message asks for a template or reference deck to match, in a single question
- [ ] If ./.fake-google-slides/calls.log has `update_presentation` calls, its `createSlide` requests use at most 2 distinct layouts
- [ ] If ./.fake-google-slides/calls.log has `update_presentation` calls, every `rgbColor` they set, converted from 0–1 floats to hex, is either a grey (equal red, green and blue) or one single other color, used as the one accent
- [ ] ./.fake-google-slides/calls.log has no `createImage` request and no inserted text that reads as a logo or wordmark (such as "ACME" or "Acme" on its own in a corner shape)
- [ ] The final message does not claim Acme brand colors, fonts or a logo that the prompt didn't give
- [ ] If the agent built the deck, a `deck.txt` under ./.fake-google-slides/files/ contains "We shipped Relay 2.0", "Search is three times faster" and "Northwind, Globex and Initech went live in November" with their wording unchanged
