---
history:
- role: user
  content: |
    Quick recap of where we landed on the widget service: a 256-entry in-process LRU in
    front of `read_widget`, invalidated whenever `write_widget` touches that widget, and
    no distributed cache for now. The goal is cutting DB load on hot widgets.
- role: assistant
  content: |
    Got it — in-process LRU on the read path, invalidation on write, distributed caching
    out of scope for this round.
---

## Prompt

take this design we landed on and write the spec doc

## Assertions

- [ ] Skill `to-spec` invoked
  - if: {BENCHSPEC_ARM} != "baseline"
