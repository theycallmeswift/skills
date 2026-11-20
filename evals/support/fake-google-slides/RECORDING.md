# fake-google-slides recording

- Recorded 2026-10-21 from the live Google Slides and Google Drive MCP servers against a synthetic 10-slide, 16:9 deck ("Acme onboarding (eval fixture)"; invented content). Slide IDs are `s01_slide`…`s10_slide`; element IDs are slide plus role (`s07_stat_value`). Slide 7 has speaker notes ("about 10 minutes"). Slide 9 uses the stock TITLE_AND_BODY placeholders.
- `tools.json`: the definitions of Slides `read_presentation`, `read_slide_page`, `read_slide_page_thumbnail`, `update_presentation` and Drive `read_file_content`, `get_file_metadata`, copied as the client listed them (bare `name`, plus `server`). The client truncated `update_presentation`'s description mid-list, ending in `… [truncated]`, and it is kept that way.
- `deck.json`: `read_presentation` with no `fields` mask (287 KB; includes layouts, masters, notesMaster).
- `pages/p-NN.json`: `read_slide_page` with no mask. Built from `deck.json`'s `slides[NN-1]` plus `commentsViewMode` and `revisionId`. The live `read_slide_page` output for `s01_slide` and `s09_slide` at the same revision matched this byte for byte.
- `deck.txt`: Drive `read_file_content` (no comments). `meta.json`: Drive `get_file_metadata` (default verbosity).
- `thumbs/p-NN.json`: `read_slide_page_thumbnail` with `thumbnailSize: MEDIUM`. `thumbs/p-NN.png`: 800x450 bytes fetched from each `contentUrl` (it is public and needs no auth).
- Scrub map: presentation and file ID `acme-onboarding-fixture`, parent `fixture-parent-folder`, `ouid` `000000000000000000000`, owner `owner@example.com`, revision `fixture-revision-0001`, created `2026-01-05T09:00:00.000Z`, modified and viewed `2026-01-05T10:30:00.000Z`, thumbnail URL `https://lh7-us.googleusercontent.com/docsdf/acme-onboarding-fixture-p-NN=s800`. Generated notes IDs (`SLIDES_API…`) and list IDs (`kix.…`) are left as recorded.

## Response quirks to reproduce

- Every result is a single text block holding compact JSON (no image blocks), with keys sorted alphabetically.
- `read_presentation` and `read_slide_page` wrap the resource in `{"content": {...}}`. `update_presentation` returns bare `{"replies": [...]}`: `{}` per request, `{"createSlide"|"createShape"|"duplicateObject": {"objectId": ...}}` for creates. Thumbnails return bare `{"contentUrl","heightPx","widthPx"}`. Drive returns bare `{"fileContent","title","viewUrl"}` and a bare File object.
- `read_file_content` leaves out speaker notes, but `get_file_metadata`'s `contentSnippet` includes them, after the slide's body text.
- Created elements come back with base size 3000000x3000000 EMU and the real size in `transform.scaleX/scaleY`, rounded to 4 decimal places.
- Errors are tool errors whose text starts `Invalid argument: <eye3 title='/PresentationsService.BatchUpdatePresentation, INVALID_ARGUMENT'/> APPLICATION_ERROR;...ExternalBadRequestException: Invalid requests[1].createSlide: The object ID (s01) length should not be less than 5.;...`. Batches are atomic.
- An unmasked read is large: about 287 KB for the deck and 5 to 22 KB per page.

## Template deck (`template/`)

- Recorded 2026-10-24 from the live connectors against a synthetic 3-slide, 16:9 template, "Acme brand template (eval fixture)" (invented content). Built with Drive `create_file`, then Slides `update_presentation`: `updatePageProperties` set a custom `colorScheme` on master `simple-light-2` (DARK1 navy `#14213D`, ACCENT1 orange `#F2762E`, DARK2 slate, LIGHT2 warm neutral, teal and grey accents); master placeholders set to Montserrat bold (title) and Lato (body); layouts kept are `p2` TITLE (navy background), `p3` SECTION_HEADER (orange background), `p4` TITLE_AND_BODY and `p5` TITLE_AND_TWO_COLUMNS, with `p6`…`p12` removed by `deleteObject`; a `RECTANGLE` logo `acme_logo` reading "ACME" sits on the master. Slides `t01_slide` (TITLE), `t02_slide` (TITLE_AND_BODY), `t03_slide` (SECTION_HEADER); element IDs are slide plus role (`t02_body`).
- Same layout as the onboarding deck: `deck.json` (`read_presentation`, no mask, 85 KB), `pages/p-NN.json` (built from `deck.json` the same way; the live `read_slide_page` for `t03_slide` matched byte for byte), `deck.txt` (`read_file_content`), `meta.json` (`get_file_metadata`), `thumbs/p-NN.json` + `p-NN.png` (MEDIUM, 800x450).
- `copy_file.json`: Drive `copy_file` of the template, title "Acme brand template (eval fixture) copy". `create_file.json`: Drive `create_file` with `contentMimeType: application/vnd.google-apps.presentation`, title "Blank deck (eval fixture)". `blank.json`: `read_presentation` of that blank deck, no mask (117 KB). Both were then trashed with `trash_file` (reply `{}`); the template was kept.
- `tools.json` gained Drive `copy_file` and `create_file`, copied untrimmed as the client listed them.
- Scrub map: template ID `acme-template-fixture`, copy `acme-template-copy-fixture`, blank `blank-deck-fixture`, parent `fixture-parent-folder`, `ouid` `000000000000000000000`, owner `owner@example.com`, revisions `template-revision-0001` and `blank-revision-0001`, template created `2026-01-05T09:00:00.000Z` and modified/viewed `2026-01-05T10:30:00.000Z`, copy times all `2026-01-05T11:00:00.000Z`, blank times all `2026-01-05T11:05:00.000Z`, thumbnail URL `https://lh7-us.googleusercontent.com/docsdf/acme-template-fixture-p-NN=s800`. Notes IDs (`SLIDES_API…`) left as recorded.

### Template quirks

- `copy_file` and `create_file` return a bare File object, the same shape as `get_file_metadata` without `contentSnippet`, with `fileSize` `"1"` right after the call. These, and the template's `meta.json`, now carry `"starred":false`, which the 2026-10-21 `meta.json` lacks.
- The copy keeps every object ID: master `simple-light-2`, layouts `p2`…`p5`, the logo, slide and element IDs, and the notes IDs. Only the presentation ID, revision ID and title change.
- A `create_file` presentation is the stock deck: master `simple-light-2`, eleven layouts `p2`…`p12`, and one TITLE slide `p` with empty placeholders `i0`, `i1`.
- `updatePageProperties` with `fields: colorScheme` was sent the twelve settable colors (fewer not tried); reads return sixteen, adding the `TEXT1`, `BACKGROUND1`, `TEXT2` and `BACKGROUND2` aliases.
- `get_file_metadata`'s `contentSnippet` includes master text (the "ACME" logo) after each slide's text; `read_file_content` leaves it out.

## Poster deck (`poster/`)

- Recorded 2026-10-26 from the live connectors against a synthetic 8-slide, 16:9 poster talk, "Acme poster talk (eval fixture)" (invented content), for `new-slides-illustrated-deck`. Built with Drive `create_file`, then one Slides `update_presentation` batch on the stock theme: `s01_slide` (TITLE layout: "How Acme builds software", "Engineering all-hands"); `s02_slide`…`s07_slide` (BLANK), each a hand-drawn image `sNN_art` of 8 x 4.2 in at (1, 0.3) in, 60% of the slide, over one centered line `sNN_line` in Patrick Hand 40pt; and `art_drawer` (BLANK, `isSkipped: true`), titled "Art drawer" (`art_title`, 28pt) and holding six unused 2.8 x 1.47 in images, `art_ship`, `art_pager`, `art_write`, `art_measure`, `art_talk` and `art_fix`. Every image has alt text naming what it shows.
- The images are `poster/art/*.png`: black stick-figure line drawings, 1600x840, drawn with PIL for this fixture. `createImage` fetched them from raw.githubusercontent.com at commit `9d5bec5`, and each image's `sourceUrl` keeps that URL.
- Same layout as the onboarding deck: `deck.json` (`read_presentation`, no mask, 155 KB), `pages/p-NN.json` (built from `deck.json` the same way; the live `read_slide_page` for `s01_slide` and `art_drawer` matched on every field compared, notes IDs, transforms and text styles included), `deck.txt` (`read_file_content`), `meta.json` (`get_file_metadata`), `thumbs/p-NN.json` + `p-NN.png` (MEDIUM, 800x450).
- Scrub map: presentation and file ID `acme-poster-fixture`, parent `fixture-parent-folder`, `ouid` `000000000000000000000`, owner `owner@example.com`, revision `poster-revision-0001`, created `2026-01-05T09:00:00.000Z`, modified and viewed `2026-01-05T10:30:00.000Z`, thumbnail URL `https://lh7-us.googleusercontent.com/docsdf/acme-poster-fixture-p-NN=s800`, image `contentUrl` `https://docs.google.com/slides-images-rt/acme-poster-fixture-<objectId>=s2048` (live, a signed URL with a `key` parameter that changes on every read). Notes IDs (`SLIDES_API…`) left as recorded.

### Poster quirks

- `createImage` stores the picture's own size as the base, 25 EMU per pixel (1600x840 becomes 40000 x 21000 EMU), and carries the requested size in a uniform scale: 182.88 for the 8 in slides, 64.008 for the drawer. Its reply is `{"createImage": {"objectId": ...}}`.
- `read_file_content` leaves images out entirely; a shape with no text still shows as an empty line. `get_file_metadata`'s `contentSnippet` leaves out alt text.
- Every slide made by `createSlide`, BLANK ones included, comes with a notes page `<slide>:notes` holding a slide image and an empty speaker notes box, both with generated `SLIDES_API…` IDs.
- Right after the write, `get_file_metadata` returned a stale `contentSnippet` ("# 1 of 1"), `fileSize` and `modifiedTime`; a read about a minute later, recorded here, had caught up.
