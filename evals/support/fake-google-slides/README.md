# fake-google-slides

Fake Google Slides and Google Drive MCP servers for evals of `google-slides`. The eval guest
can't reach Google, so `server.py` (stdlib, stdio) serves the connectors' tools from a cassette
recorded against two synthetic decks: a 10-slide deck, "Acme onboarding (eval fixture)", ID
`acme-onboarding-fixture`, and a 3-slide brand template, "Acme brand template (eval fixture)", ID
`acme-template-fixture`, under `template/`. `RECORDING.md` says what each file holds and which
quirks of the live connectors it keeps.

Source `setup.sh` from a scenario's `setup.sh`, then:

- `add_google_slides [<meta-overlay.json>]` installs `python3` when the guest lacks it, copies the
  onboarding deck to `/workspace/.fake-google-slides/`, and registers `server.py` twice as
  user-scope MCP servers named `Google_Slides` and `Google_Drive`, as the live connectors are.
  The overlay's fields replace the onboarding deck's recorded `get_file_metadata` fields, such as
  `{"owner": "priya@example.com"}`.
- `add_google_workspace_skill` installs `google-workspace-skill/SKILL.md` as the user skill
  `google-workspace`: a short stand-in for the bundled skill, which isn't licensed for copying.
  Scenarios that test the skill's absence skip it.

## What the fake does

- Each file has a folder: the onboarding deck is `/workspace/.fake-google-slides/` itself, every
  other file `/workspace/.fake-google-slides/files/<file-id>/`, seeded from the cassette the
  first time a tool names it. The template is there from the start; unknown IDs are not found.
- Reads replay the cassette byte for byte until the deck changes: `read_presentation` and
  `read_slide_page` (with field masks applied), Drive `read_file_content` and
  `get_file_metadata`. The Drive text is regenerated from the current deck in the live format,
  so it leaves out speaker notes while the metadata `contentSnippet` includes them.
- Drive `copy_file` copies any deck the fake knows to `<source-stem>-copy-fixture` (then `-2`,
  `-3`), keeping every object ID, as the live API does: copying the template with the recorded
  title replays `template/copy_file.json`. `create_file` makes only a blank presentation,
  `blank-deck-fixture` (then `-2`, ...), from `template/blank.json`, replaying
  `template/create_file.json` for the recorded title; anything else is a tool error.
- `update_presentation` applies `insertText`, `deleteText`, `replaceAllText`, `createShape`,
  `createSlide`, `duplicateObject`, `deleteObject`, `updatePageElementTransform`,
  `updateShapeProperties` and `updateSlidesPosition`, keeping text styles. `createSlide` on a
  layout adds the layout's text placeholders (not the slide number), named by
  `placeholderIdMappings`. Text, paragraph, page and other style
  requests are checked for valid object IDs and logged but change nothing. Batches are atomic,
  `writeControl.requiredRevisionId` is enforced, and each write bumps the revision ID.
- `read_slide_page_thumbnail` returns the recorded PNG, served at `http://127.0.0.1:8765/...` in
  place of the recorded Google URL, for the recorded decks and their copies. A slide created or
  changed since recording has no render, so its thumbnail is a tool error that says so.
- Every tool call is appended as a JSON line (server, tool, arguments) to
  `/workspace/.fake-google-slides/calls.log`. After each write, the file's folder holds the
  whole deck in `deck.json` and the `read_file_content` text in `deck.txt`, for checkers to
  grade.

`tests/evals/support/fake-google-slides/` checks the replay and the edits; `make test` runs it.

## Re-record

Re-record when `google-slides`, or an eval using this fake, changes. Run in a Claude Code session
that has the Google Slides and Google Drive connectors and this repo checked out:

```text
Re-record evals/support/fake-google-slides/ from the live Google Slides and Google Drive
connectors. Read RECORDING.md first and keep its file layout and scrub map.
1. Build the onboarding deck: a new 16:9 presentation with the 10 slides that `deck.txt`
   describes, every object ID as in deck.json (s01_slide, s07_stat_value, ...), slide 7's
   speaker notes, and slide 9 on the stock TITLE_AND_BODY layout. Build the template the way
   RECORDING.md's "Template deck" section describes: its color scheme, fonts, four layouts,
   master logo and three slides t01_slide to t03_slide. Invented content only; never record a
   real deck.
2. tools.json: copy the eight tool definitions exactly as your tool list shows them, each with
   its `server`, truncations included.
3. For each deck, record read_presentation with no fields mask, read_slide_page for each slide,
   read_slide_page_thumbnail (MEDIUM) for each slide plus the PNG at each contentUrl,
   read_file_content, and get_file_metadata, into the files RECORDING.md names (template/ for
   the template).
4. Record Drive copy_file of the template (title "Acme brand template (eval fixture) copy") and
   create_file of a blank presentation (title "Blank deck (eval fixture)"), plus
   read_presentation of the blank deck, into template/copy_file.json, create_file.json and
   blank.json. Trash both.
5. Scrub every real ID, email, URL and timestamp to the fixture values in RECORDING.md.
6. Delete the onboarding deck and the template. Update the dates in RECORDING.md and in
   docs/evals/google-slides.md.
7. Run make test, make lint and make evals:lint, then re-run the evals that use this fake.
```
