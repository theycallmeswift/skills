---
---

## Prompt

Use the `writing-prompts` skill to draft the prompt below.

We're getting flooded with support tickets and I want an LLM to help triage them. Can you
write me a prompt for that?

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] Output contains an explicit role/task statement.
- [ ] Output is third-person/imperative voice — no 'I'll help you...' or 'you'll get...'.
- [ ] Output uses XML tags or other clear section delimiters (markdown headings count for doc-shaped outputs).
- [ ] Output specifies the expected output shape (format, schema, or worked example).
- [ ] Either the agent asks at least one scoping question before drafting, OR the draft surfaces its assumptions in writing (input shape, priority taxonomy, what 'triage' means here).
- [ ] If a draft is produced, it defines a structured output shape — not free-form prose.
- [ ] The draft does not lean on generic boilerplate phrases like 'You are a helpful AI assistant'.
- [ ] Output ends with a tightened final version produced by an editorial pass.
