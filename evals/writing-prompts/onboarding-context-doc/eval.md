---
---

## Prompt

Use the `writing-prompts` skill to draft the context doc below.

I'm writing `docs/onboarding.md` for our team. Claude reads it as context when someone
asks 'how do we do X here?' or 'what does Y mean?'. Cover: company decision-making norms
(we move fast, RFCs only for irreversible things), the tech stack
(TypeScript/Postgres/Vercel), and the no-meetings-Friday rule. Also point to our deeper
docs — the full deploy runbook and the per-service on-call guides — without inlining them.
Keep it under 200 lines.

## Assertions

- [ ] Skill `writing-prompts` invoked
  - if: {BENCHSPEC_ARM} != {BENCHSPEC_BASELINE}
- [ ] Output contains an explicit role/task statement.
- [ ] Output is third-person/imperative voice — no 'I'll help you...' or 'you'll get...'.
- [ ] Output uses XML tags or other clear section delimiters (markdown headings count for doc-shaped outputs).
- [ ] Output is under 200 lines.
- [ ] Output is behavioral ('Confirm before irreversible actions; otherwise just do it') rather than adjectival ('Be careful with important changes').
- [ ] Output names at least one failure mode or tiered-autonomy boundary, not just rules-when-everything-goes-right.
- [ ] Output uses load-on-demand framing for detail it doesn't inline: either a `## References` section pointing at deeper docs, inline links framed as load-on-demand, OR an explicit empty-but-named placeholder (a `## References` heading whose body says no deeper docs exist yet). Encyclopedic detail inlined with no structural placeholder fails.
- [ ] Output uses section headings that scan in under a minute — no one section dominates the file.
