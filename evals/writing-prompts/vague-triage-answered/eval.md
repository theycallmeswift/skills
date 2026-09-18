---
history:
- role: user
  content: |
    We're getting flooded with support tickets and I want an LLM to help triage them. Can you
    write me a prompt for that?
- role: assistant
  content: |
    Before I draft, a few questions: where do tickets come from and in what shape, what
    priority levels do you use, and who or what consumes the triage output?
- role: user
  content: |
    Tickets come from Zendesk as JSON: subject, body, customer plan (free/pro/enterprise).
    Priorities are P0 (outage or data loss), P1 (feature broken, no workaround), P2 (bug with
    workaround), P3 (question or feature request). The output feeds a routing script that
    assigns a queue, so it must be machine-readable.
---

## Prompt

Use the `writing-prompts` skill to draft the triage prompt from those answers.

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] Output contains an explicit role/task statement.
- [ ] Output is third-person/imperative voice — no 'I'll help you...' or 'you'll get...'.
- [ ] Output uses XML tags or other clear section delimiters (markdown headings count for doc-shaped outputs).
- [ ] The draft defines a structured, machine-readable output shape (format, schema, or worked example) — not free-form prose.
- [ ] The draft uses the stated P0–P3 definitions.
- [ ] The draft does not lean on generic boilerplate phrases like 'You are a helpful AI assistant'.
- [ ] Output ends with a tightened final version produced by an editorial pass.
