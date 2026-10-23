---
name: google-workspace
description: "Rules for changing a file in the user's Google Drive through the Docs, Sheets, Slides and Drive connectors. Load it before the first connector call when a request asks to create, edit, restyle, copy or rename a Google Doc, Sheet or Slides deck, including a docs.google.com link with a change to make or a follow-up tweak to a Google file from earlier. Skip it when the user only wants to read or ask about a Google file, and for Word, Excel, PowerPoint or PDF files."
---

# Google Slides mechanics

Eval stand-in for the bundled `google-workspace` skill: the rules for editing a Google file through the Slides and Drive connectors.

- **Change the user's file in place.** An edit goes in the same deck, so the link stays the same. Don't recreate a file to avoid an edit.
- **Read with a field mask.** An unmasked `read_presentation` is hundreds of KB. Ask for what you need, such as `slides(objectId,pageElements(objectId,size,transform,shape(shapeType,text)))` plus `revisionId`. Drive `read_file_content` gives the whole deck as short text, without speaker notes.
- **Guard every write.** Send each `update_presentation` batch with `writeControl.requiredRevisionId` set to the `revisionId` of a read taken after your last write. On a mismatch, read again and rebuild.
- **One batch per step.** Requests run in order and atomically: one bad request and none apply.
- **Geometry is in EMU.** 914400 EMU to the inch, 12700 to the point. An element's drawn size is its `size` times its `transform` scale. Slides never shrinks text to fit a box.
- **Look at the result.** `read_slide_page_thumbnail` returns a PNG URL for a slide; fetch it and view it. Read the slide again after each write and check it before reporting.
