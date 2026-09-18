---
---

## Prompt

Use the `writing-prompts` skill to draft the prompt below.

I need a prompt for an LLM that summarizes financial filings. It needs to extract every
material fact while keeping the summary under 50 words. It should hedge nothing —
confidence assertions only — but also flag every uncertainty. And it should work with no
examples or context, just the raw 10-K.

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] Output contains an explicit role/task statement.
- [ ] Output is third-person/imperative voice — no 'I'll help you...' or 'you'll get...'.
- [ ] Output uses XML tags or other clear section delimiters (markdown headings count for doc-shaped outputs).
- [ ] Output specifies the expected output shape (format, schema, or worked example).
- [ ] Output surfaces at least one of the contradictions (completeness vs. 50-word cap; no-hedging vs. flag-uncertainty; zero-shot vs. extraction quality).
- [ ] Output either asks the user to resolve the conflict OR names the tradeoff it chose and why.
- [ ] Output does not silently paper over the conflict by ignoring half the constraints.
- [ ] Output ends with a tightened final version produced by an editorial pass.
