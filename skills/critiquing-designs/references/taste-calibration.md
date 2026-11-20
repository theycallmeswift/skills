# Taste calibration

Read this before an aesthetic pass when the user hasn't named reference sites. It turns "make it look better" into reference images the models can grade against, from pictures the user reacts to instead of adjectives they must invent.

## 1. Pick candidates

Choose 8–10 sites or products the work could plausibly learn from: same category or audience, a spread of directions (dense and spacious, quiet and bold, different type choices). Include any the user mentioned in passing. Fewer than 8 gives no real choice; more than 10 blurs on one sheet.

## 2. Screenshot them in dark mode

Capture each in dark mode at the same viewport width, on a comparable screen (a dashboard against a dashboard, not a marketing page). Use any browser or screenshot tool you have; if none, ask the user for the screenshots. Name files by candidate, e.g. `linear.png`.

## 3. Build the contact sheet

```
python3 scripts/contact_sheet.py OUT/calibration/sheet.png OUT/calibration/*.png --labels "1 Linear,2 Vercel,3 Raycast,..." --cols 3
```

Without `--labels`, it labels each thumbnail with its number and file stem. Show the sheet to the user.

## 4. Ask two questions, one at a time

1. **Multi-select:** "Which of these feel right for <product>? Pick any, by number." Offer the numbered candidates as choices, plus "none of these".
2. **Direction:** "Refine toward these, or redirect?" If redirect, ask what to move toward in their words, then repeat steps 1–4 once with new candidates.

Record what the user says they like about each pick; the aesthetic rubric's References section quotes it.

## 5. Show font and variant choices rendered

When the direction raises a choice of font, weight, colour variant or density, render the options side by side with the same real content (a heading, a body paragraph, a table row from the actual design), put them on one contact sheet with `contact_sheet.py`, and ask which. Never ask in the abstract ("geometric or humanist sans?"): people can't predict their taste from a label, but they recognise it on sight.

## 6. Hand off

The picked screenshots become the REF images in the aesthetic package (frames `REF1`, `REF2`, ...). Each rendered choice the user made becomes a settled decision in the rubric.
