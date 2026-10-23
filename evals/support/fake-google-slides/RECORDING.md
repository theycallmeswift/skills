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
