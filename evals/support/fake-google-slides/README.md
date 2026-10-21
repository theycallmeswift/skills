# fake-google-slides

Fake Google Slides and Google Drive MCP servers for evals of `redesigning-google-slides`. The
eval guest can't reach Google, so `server.py` (stdlib, stdio) serves the connectors' tools from a
cassette recorded against a synthetic 10-slide deck, "Acme onboarding (eval fixture)", ID
`acme-onboarding-fixture`. `RECORDING.md` says what each file holds and which quirks of the live
connectors it keeps.

Source `setup.sh` from a scenario's `setup.sh`, then:

- `add_google_slides [<meta-overlay.json>]` installs `python3` when the guest lacks it, copies the
  deck to `/workspace/.fake-google-slides/`, and registers `server.py` twice as user-scope MCP
  servers named `Google_Slides` and `Google_Drive`, as the live connectors are. The overlay's
  fields replace recorded `get_file_metadata` fields, such as `{"owner": "priya@example.com"}`.
- `add_google_workspace_skill` installs `google-workspace/SKILL.md` as a user skill. It is a short
  stand-in for the bundled `google-workspace` skill, which isn't licensed for copying; scenarios
  that test the skill's absence skip it.

## What the fake does

- Reads replay the cassette byte for byte until the deck changes: `read_presentation` and
  `read_slide_page` (with field masks applied), Drive `read_file_content` and
  `get_file_metadata`. The Drive text is regenerated from the current deck in the live format,
  so it leaves out speaker notes while the metadata `contentSnippet` includes them.
- `update_presentation` applies `insertText`, `deleteText`, `replaceAllText`, `createShape`,
  `createSlide`, `duplicateObject` and `deleteObject`, keeping text styles. Style and position
  requests are checked for valid object IDs and logged but change nothing. Batches are atomic,
  `writeControl.requiredRevisionId` is enforced, and each write bumps the revision ID.
- `read_slide_page_thumbnail` returns the recorded PNG, served at `http://127.0.0.1:8765/...` in
  place of the recorded Google URL. A slide changed since recording has no render, so its
  thumbnail is a tool error that says so.
- Every tool call is appended as a JSON line (server, tool, arguments) to
  `/workspace/.fake-google-slides/calls.log`. After each write, `deck.json` there holds the whole
  deck and `deck.txt` the `read_file_content` text, for checkers to grade.

`tests/evals/support/fake-google-slides/` checks the replay and the edits; `make test` runs it.

## Re-record

Re-record when `redesigning-google-slides`, or an eval using this fake, changes. Run in a Claude
Code session that has the Google Slides and Google Drive connectors and this repo checked out:

```text
Re-record evals/support/fake-google-slides/ from the live Google Slides and Google Drive
connectors. Read RECORDING.md first and keep its file layout and scrub map.
1. Build the deck: a new 16:9 presentation with the 10 slides that `deck.txt` describes, every
   object ID as in deck.json (s01_slide, s07_stat_value, ...), slide 7's speaker notes, and
   slide 9 on the stock TITLE_AND_BODY layout. Invented content only; never record a real deck.
2. tools.json: copy the six tool definitions exactly as your tool list shows them, each with
   its `server`, truncations included.
3. Record read_presentation with no fields mask, read_slide_page for each slide,
   read_slide_page_thumbnail (MEDIUM) for each slide plus the PNG at each contentUrl,
   read_file_content, and get_file_metadata, into the files RECORDING.md names.
4. Scrub every real ID, email, URL and timestamp to the fixture values in RECORDING.md.
5. Delete the deck. Update the date in RECORDING.md and in docs/evals/redesigning-google-slides.md.
6. Run make test, make lint and make evals:lint, then re-run the evals that use this fake.
```
