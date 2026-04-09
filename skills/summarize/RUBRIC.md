# Summarize Rubric

Evaluated by `make eval`. Goals the output must satisfy across every case.

## Critical

- Output contains a clickable markdown link to the source URL near the title (for web-sourced cases)
- The shareable snippet block includes the source URL (for web-sourced cases)
- Key points reference specific content from the source, not generic commentary
- For local-file cases: title is derived from the document/paper title or filename, not a URL or generic placeholder like "Summary"
- For local-file cases: the shareable snippet block contains no URL
- For local-file cases: key points are grounded in the source content, not invented or generic
- For the `short-input-no-padding` case: the summary names the Q3 demo day date change as the core fact
- For the `short-input-no-padding` case: every bullet is directly supported by the 4-sentence input (no invented project-management commentary)

## Optional

- Bullets are scannable and roughly parallel in shape
