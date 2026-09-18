---
---

## Prompt

Use the `writing-prompts` skill to draft the system prompt below.

I'm building a code-review subagent for our team's Claude Code plugin. It needs to focus
on correctness bugs (we have linters for style), accepts a PR diff as input, and outputs
findings as a markdown bullet list with `file:line` references. It should explicitly skip
nitpicks. I want precision over recall — fewer findings, higher confidence. Draft me the
system prompt I'll drop into the subagent's frontmatter.

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] Output contains an explicit role/task statement.
- [ ] Output is third-person/imperative voice — no 'I'll help you...' or 'you'll get...'.
- [ ] Output uses XML tags or other clear section delimiters (markdown headings count for doc-shaped outputs).
- [ ] Output specifies the expected output shape (format, schema, or worked example).
- [ ] Output states the precision-over-recall preference (fewer findings, higher confidence) in the prompt text.
- [ ] Output includes at least one negative constraint (skip nitpicks or no style commentary).
- [ ] Output is shaped so it could be pasted into a subagent description/system-prompt slot without further editing.
- [ ] Output ends with a tightened final version produced by an editorial pass.
