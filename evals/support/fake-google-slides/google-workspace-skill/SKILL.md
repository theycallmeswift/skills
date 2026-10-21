---
name: google-workspace
description: "Read this before the first Google Drive, Docs, Sheets or Slides connector call whenever the task creates or changes a Google file: a request that names Google Docs, Sheets, Slides or Drive and asks to make, edit, format, copy or rename a file, or a docs.google.com link with a request to change it. Do NOT use for read-only questions about a Google file, or for Word, Excel, PowerPoint or PDF files."
---

# Google Slides mechanics

Eval stand-in for the bundled `google-workspace` skill: the rules for editing a Google file through the Slides and Drive connectors.

- **Change the user's file in place.** An edit goes in the same deck, so the link stays the same. Don't recreate a file to avoid an edit.
- **Read with a field mask.** An unmasked `read_presentation` is hundreds of KB. Ask for what you need, such as `slides(objectId,pageElements(objectId,size,transform,shape(shapeType,text)))` plus `revisionId`. Drive `read_file_content` gives the whole deck as short text, without speaker notes.
- **Guard every write.** Send each `update_presentation` batch with `writeControl.requiredRevisionId` set to the `revisionId` of a read taken after your last write. On a mismatch, read again and rebuild.
- **One batch per step.** Requests run in order and atomically: one bad request and none apply.
- **Geometry is in EMU.** 914400 EMU to the inch, 12700 to the point. An element's drawn size is its `size` times its `transform` scale. Slides never shrinks text to fit a box.
- **Look at the result.** `read_slide_page_thumbnail` returns a PNG URL for a slide; fetch it and view it. Read the slide again after each write and check it before reporting.
