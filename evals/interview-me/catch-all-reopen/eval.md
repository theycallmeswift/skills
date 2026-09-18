---
history:
- role: user
  content: 'Interview me to scope this out before we commit: should our new

    background-job runner use a Postgres-backed queue or Redis? Stress-test that

    one call with me — one question at a time, a visual on every decision — until

    we''ve decided it, and nothing broader. Use the `interview-me` skill.

    '
- role: assistant
  content: 'Mode C — a stated goal: decide the queue backend, nothing broader. Here''s the

    one decision on the table.


    | Option | Backend | Tradeoff |

    |---|---|---|

    | A | Postgres-backed queue | Reuses infra you operate; couples job load to the DB |

    | B | Redis | Fast, purpose-built; another service to run and monitor |


    Postgres or Redis — and what''s driving the call?

    '
- role: user
  content: 'Postgres-backed queue — we already run Postgres, throughput is low, latency

    is relaxed, and we don''t want another moving part.

    '
- role: assistant
  content: 'Locked: Postgres-backed queue. That resolves the one call we set out to make.

    Before we wrap — is there anything important about the job runner we haven''t

    covered?

    '
---

## Prompt

Wait — billing jobs need exactly-once execution; we can't risk double-charging a
customer. Does that change the Postgres-vs-Redis call? Use the `interview-me` skill
to continue.

## Assertions

- [ ] Skill `interview-me` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
- [ ] The catch-all surfaced a requirement that bears directly on the backend choice (exactly-once execution), so the skill REOPENS the decision rather than parking it as out of scope or wrapping — it engages with exactly-once as live input to the Postgres-vs-Redis call, either asking a follow-up to resolve it or laying out how each backend delivers exactly-once and which way that points.
- [ ] No spec file was written under ./docs/specs/.
