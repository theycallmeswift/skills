---
name: mockup
description: Use whenever the user wants to see a UI before it is specced, split into issues, or built — "mock up the X dialog", "sketch this screen", "wireframe it", "show me a few layouts", "make a clickable demo of the flow", "what could this look like" — for web, mobile, or terminal (TUI) screens. Also when a spec or milestone needs the user's sign-off on a screen first. Don't use to build or change the real UI in code, to chart or visualize data, to write the spec itself (to-spec), or for a questions-only interview (interview-me).
---

# mockup

A mockup buys the user's alignment before a spec or issues lock anything in.
The output is a decision: an approved version the caller can build from.

## Start

Read the project first (README, the screen's code) so every mockup uses real
names, copy, and sizes, never lorem ipsum. If the request and the project say
what the screen is for, go straight to round 1. Otherwise ask one open
question that gets the user describing it ("who's looking at this screen,
and from how far away?"); offer a menu only when they're stuck. One question
per message, always.

## Pick the fidelity

Use the lightest form that answers the question:

| Question | Form |
|---|---|
| Copy, one element, a yes/no | ASCII sketch inline in chat |
| Layout or visual choice | Static page from `assets/page-template.html` |
| A flow across screens | Clickable single-file HTML prototype: the template's `.flow`, no real code, no app imports |

Draw terminal UIs on the template's `.term` grid at the app's real column
widths (e.g. 80×24). Unless the whole screen is the question, mock only the
region that changes, such as a dialog and the rows around it.

## Each round

1. Show one piece: a screen or state, not the whole app.
2. Offer 2–4 options lettered A, B, C, D, so a phone reply can be just "B".
   Each is a mockup beside one or two lines on what differs and what it
   costs. Say which you recommend and why.
3. Save the round as a new version: `<dir>/mockups/vN/<screen>.html` (or
   `.txt` for ASCII), where `<dir>` is the caller's spec folder, else
   `docs/mockups/<slug>/`. Never edit or overwrite an earlier version: the
   user compares against them.
4. Publish it as a page the user can open on a phone, e.g. a hosted-page
   tool if the harness has one; otherwise commit the HTML and give the path.
   Don't start a local server: the user is often on a phone in a cloud
   session, where localhost is unreachable.
5. End with one question: which option, or what's wrong or missing. Fold
   other open points into the options, not a second question.

## Gate

Nothing proceeds until the user approves one version. Proceeding includes
writing a spec, drafting issues, writing product code, and wiring the mockup
into the app. "Looks good" across several options isn't approval; ask which.
Feedback means a new round, `vN+1`.

## On approval

1. Optional: give the approved file to a fresh subagent with "Assume a
   builder will hit problems in this mockup: missing states (empty, error,
   loading), unclear controls, placeholder copy, unreadable at phone width.
   List them." Fix what's real in a new version, then confirm it.
2. Record the approved version where the caller wants it (the spec or the
   issue): its path and a one-line summary, e.g.
   `Approved mockup: docs/mockups/queue-screen/mockups/v2/queue.html (next name large, countdown beside it, rest of the line dimmed).`
3. Hand off by name: tell the user the next step is the caller's skill
   (`to-spec` or `to-milestone`). Don't invoke it yourself.
